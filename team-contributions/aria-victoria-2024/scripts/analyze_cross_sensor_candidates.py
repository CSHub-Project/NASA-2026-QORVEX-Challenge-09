
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import numpy as np
import pandas as pd


# =========================================================
# 1. CONFIGURATION
# =========================================================

DATA_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")
OUTPUT_DIR = Path(r"C:\Users\Asus\data")

PRODUCTS = {
    "MODIS_SP": "MODIS",
    "VIIRS_SNPP_SP": "SNPP",
    "VIIRS_NOAA20_SP": "NOAA20",
}

GRID_SIZE_KM = 5.0
MAX_DISTANCE_KM = 5.0
MAX_TIME_HOURS = 24.0

REFERENCE_LATITUDE = -36.5


# =========================================================
# 2. COORDINATE PROJECTION
# =========================================================

def project_coordinates(lat, lon):

    x = (
        lon
        * 111.320
        * np.cos(np.radians(REFERENCE_LATITUDE))
    )

    y = lat * 110.574

    return x, y


# =========================================================
# 3. LOAD RAW FIRMS DATA
# =========================================================

def load_product(product_name, sensor_name):

    files = sorted(
        DATA_DIR.glob(f"{product_name}_*.csv")
    )

    if not files:
        raise FileNotFoundError(
            f"No files found for {product_name}"
        )

    frames = []

    required_columns = [
        "latitude",
        "longitude",
        "acq_date",
        "acq_time",
        "satellite",
        "scan",
        "track",
        "frp",
    ]

    for file in files:

        df = pd.read_csv(file)

        missing = (
            set(required_columns) - set(df.columns)
        )

        if missing:
            raise ValueError(
                f"{file.name} is missing: {sorted(missing)}"
            )

        # -------------------------------------------------
        # Stable source-record identifier
        # -------------------------------------------------

        # Original CSV row numbers start at 2 because
        # row 1 contains the header.

        df["source_record_id"] = [
            f"{file.name}::row={row_number}"
            for row_number in range(2, len(df) + 2)
        ]

        df["source_file"] = file.name

        frames.append(df)

    data = pd.concat(
        frames,
        ignore_index=True
    )

    # -----------------------------------------------------
    # Parse UTC timestamps
    # -----------------------------------------------------

    time_text = (
        data["acq_time"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(4)
    )

    timestamp_text = (
        data["acq_date"].astype(str)
        + " "
        + time_text.str[:2]
        + ":"
        + time_text.str[2:4]
    )

    data["timestamp_utc"] = pd.to_datetime(
        timestamp_text,
        format="%Y-%m-%d %H:%M",
        errors="coerce",
        utc=True,
    )

    # -----------------------------------------------------
    # Convert numerical fields
    # -----------------------------------------------------

    numeric_columns = [
        "latitude",
        "longitude",
        "scan",
        "track",
        "frp",
    ]

    for column in numeric_columns:

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    data = data.dropna(
        subset=[
            "latitude",
            "longitude",
            "timestamp_utc",
        ]
    ).copy()

    data = data[
        data["latitude"].between(-90, 90)
        &
        data["longitude"].between(-180, 180)
    ].copy()

    data["sensor_group"] = sensor_name

    data = data.reset_index(drop=True)

    # -----------------------------------------------------
    # Project coordinates
    # -----------------------------------------------------

    x, y = project_coordinates(
        data["latitude"].to_numpy(),
        data["longitude"].to_numpy(),
    )

    data["x_km"] = x
    data["y_km"] = y

    # -----------------------------------------------------
    # Assign spatial grid cells
    # -----------------------------------------------------

    data["grid_x"] = np.floor(
        data["x_km"] / GRID_SIZE_KM
    ).astype(int)

    data["grid_y"] = np.floor(
        data["y_km"] / GRID_SIZE_KM
    ).astype(int)

    return data


# =========================================================
# 4. BUILD SPATIAL GRID
# =========================================================

def build_grid(data):

    grid = defaultdict(list)

    for index, row in data.iterrows():

        cell = (
            int(row["grid_x"]),
            int(row["grid_y"]),
        )

        grid[cell].append(index)

    return grid


# =========================================================
# 5. COMPARE TWO SATELLITE GROUPS
# =========================================================

def compare_groups(group_a, group_b):

    grid_b = build_grid(group_b)

    results = []

    max_time = pd.Timedelta(
        hours=MAX_TIME_HOURS
    )

    max_distance_squared = (
        MAX_DISTANCE_KM ** 2
    )

    neighbour_range = int(
        np.ceil(
            MAX_DISTANCE_KM / GRID_SIZE_KM
        )
    )

    for index_a, row_a in group_a.iterrows():

        gx = int(row_a["grid_x"])
        gy = int(row_a["grid_y"])

        # -------------------------------------------------
        # Find candidate detections in neighbouring cells
        # -------------------------------------------------

        candidate_indices = []

        for dx in range(
            -neighbour_range,
            neighbour_range + 1,
        ):

            for dy in range(
                -neighbour_range,
                neighbour_range + 1,
            ):

                cell = (gx + dx, gy + dy)

                candidate_indices.extend(
                    grid_b.get(cell, [])
                )

        if not candidate_indices:
            continue

        candidates = group_b.loc[
            candidate_indices
        ]

        # -------------------------------------------------
        # Temporal filtering
        # -------------------------------------------------

        time_differences = (
            candidates["timestamp_utc"]
            - row_a["timestamp_utc"]
        ).abs()

        time_mask = (
            time_differences <= max_time
        )

        if not time_mask.any():
            continue

        candidates = candidates.loc[
            time_mask
        ]

        time_differences = (
            time_differences.loc[
                candidates.index
            ]
        )

        # -------------------------------------------------
        # Spatial distance
        # -------------------------------------------------

        dx = (
            candidates["x_km"].to_numpy()
            - row_a["x_km"]
        )

        dy = (
            candidates["y_km"].to_numpy()
            - row_a["y_km"]
        )

        distance_squared = (
            dx ** 2 + dy ** 2
        )

        distance_mask = (
            distance_squared
            <= max_distance_squared
        )

        if not distance_mask.any():
            continue

        matched_candidates = candidates.loc[
            distance_mask
        ]

        distances = np.sqrt(
            distance_squared[distance_mask]
        )

        matched_time_differences = (
            time_differences.loc[
                matched_candidates.index
            ]
            .dt.total_seconds()
            .to_numpy()
            / 60.0
        )

        # -------------------------------------------------
        # Save candidate associations
        # -------------------------------------------------

        for candidate_index, distance, time_diff in zip(
            matched_candidates.index,
            distances,
            matched_time_differences,
        ):

            row_b = matched_candidates.loc[
                candidate_index
            ]

            results.append({

                "detection_a_id": (
                    row_a["source_record_id"]
                ),

                "detection_b_id": (
                    row_b["source_record_id"]
                ),

                "source_file_a": row_a["source_file"],
                "source_file_b": row_b["source_file"],

                "sensor_a": row_a["sensor_group"],
                "sensor_b": row_b["sensor_group"],

                "distance_km": float(distance),

                "time_difference_min": float(
                    time_diff
                ),

                "latitude_a": row_a["latitude"],
                "longitude_a": row_a["longitude"],

                "latitude_b": row_b["latitude"],
                "longitude_b": row_b["longitude"],

                "timestamp_a": row_a["timestamp_utc"],
                "timestamp_b": row_b["timestamp_utc"],

                "frp_a": row_a["frp"],
                "frp_b": row_b["frp"],

                "scan_a": row_a["scan"],
                "track_a": row_a["track"],

                "scan_b": row_b["scan"],
                "track_b": row_b["track"],

            })

    return results


# =========================================================
# 6. MAIN ANALYSIS
# =========================================================

def main():

    print("=" * 65)
    print("QORVEX CROSS-SENSOR CANDIDATE ANALYSIS")
    print("=" * 65)

    print("\nLoading raw FIRMS data...\n")

    datasets = {}

    for product, sensor in PRODUCTS.items():

        data = load_product(
            product,
            sensor
        )

        if sensor == "MODIS":

            # Keep Aqua and Terra separate.
            for satellite in ["Aqua", "Terra"]:

                subset = data[
                    data["satellite"]
                    .astype(str)
                    .str.strip()
                    == satellite
                ].copy()

                subset["sensor_group"] = satellite

                datasets[satellite] = (
                    subset.reset_index(drop=True)
                )

        else:

            datasets[sensor] = (
                data.reset_index(drop=True)
            )

        print(
            f"{sensor}: {len(data):,} valid records"
        )

    print("\nSatellite groups:")

    for name, data in datasets.items():

        print(
            f"  {name}: {len(data):,} records"
        )

        # Check source identifier uniqueness.
        assert data["source_record_id"].is_unique, (
            f"Duplicate source IDs found in {name}"
        )

    print("\nSearching candidate pairs...\n")

    all_pairs = []

    for sensor_a, sensor_b in combinations(
        datasets.keys(),
        2,
    ):

        print(
            f"Comparing {sensor_a} with {sensor_b}..."
        )

        pairs = compare_groups(
            datasets[sensor_a],
            datasets[sensor_b],
        )

        print(
            f"  Candidate pairs: {len(pairs):,}"
        )

        all_pairs.extend(pairs)

    if not all_pairs:

        print("\nNo candidate pairs found.")
        return

    pairs_df = pd.DataFrame(all_pairs)

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    print("\nValidating results...")

    assert pairs_df["detection_a_id"].notna().all()
    assert pairs_df["detection_b_id"].notna().all()

    assert (
        pairs_df["time_difference_min"]
        <= MAX_TIME_HOURS * 60
    ).all()

    assert (
        pairs_df["distance_km"]
        <= MAX_DISTANCE_KM
    ).all()

    print("Source IDs: PASSED")
    print("Temporal constraint: PASSED")
    print("Spatial constraint: PASSED")

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print("\n" + "=" * 65)
    print("CROSS-SENSOR CANDIDATE SUMMARY")
    print("=" * 65)

    summary = (
        pairs_df
        .groupby(["sensor_a", "sensor_b"])
        .agg(
            candidate_pairs=("distance_km", "size"),
            unique_detections_a=("detection_a_id", "nunique"),
            unique_detections_b=("detection_b_id", "nunique"),
            median_distance_km=("distance_km", "median"),
            median_time_difference_min=(
                "time_difference_min",
                "median",
            ),
        )
        .reset_index()
    )

    print(summary.to_string(index=False))

    # -----------------------------------------------------
    # Threshold sensitivity
    # -----------------------------------------------------

    print("\n" + "=" * 65)
    print("DISTANCE / TIME THRESHOLD SENSITIVITY")
    print("=" * 65)

    distance_thresholds = [0.5, 1.0, 2.0, 5.0]
    time_thresholds = [
        15, 30, 60, 180, 360, 720, 1440
    ]

    for distance in distance_thresholds:

        for time in time_thresholds:

            count = (
                (pairs_df["distance_km"] <= distance)
                &
                (
                    pairs_df["time_difference_min"]
                    <= time
                )
            ).sum()

            print(
                f"Distance <= {distance:>3} km | "
                f"Time <= {time:>4} min | "
                f"Pairs: {count:>8,}"
            )

    # -----------------------------------------------------
    # Export
    # -----------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        OUTPUT_DIR
        / "cross_sensor_candidate_pairs_2024.csv"
    )

    pairs_df.to_csv(
        output_file,
        index=False
    )

    print("\nResults saved to:")
    print(output_file)

    print("\nSample candidate pairs:")

    print(
        pairs_df[
            [
                "detection_a_id",
                "detection_b_id",
                "sensor_a",
                "sensor_b",
                "distance_km",
                "time_difference_min",
                "timestamp_a",
                "timestamp_b",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

    print("\nAnalysis completed successfully.")


if __name__ == "__main__":
    main()
