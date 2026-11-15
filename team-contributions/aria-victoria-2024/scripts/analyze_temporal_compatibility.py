
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

RAW_DATA_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")

OUTPUT_DIR = Path(
    r"C:\Users\Asus\data\temporal_compatibility_analysis"
)

EARTH_RADIUS_KM = 6371.0088

# Maximum spatial distance used to generate candidates.
MAX_DISTANCE_KM = 5.0

# Maximum temporal difference used for candidate generation.
MAX_TIME_DIFFERENCE_MIN = 1440

# Spatial thresholds to investigate.
DISTANCE_THRESHOLDS_KM = [0.5, 1, 2, 5]

# Cumulative temporal windows.
TIME_THRESHOLDS_MIN = [
    15, 30, 60, 180, 360, 720, 1440
]

# Non-overlapping temporal bins.
TIME_BINS = [
    (0, 15, "00-15 min"),
    (15, 30, "15-30 min"),
    (30, 60, "30-60 min"),
    (60, 180, "01-03 hours"),
    (180, 360, "03-06 hours"),
    (360, 720, "06-12 hours"),
    (720, 1440, "12-24 hours"),
]

PRODUCTS = [
    "MODIS_SP",
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
]

REQUIRED_COLUMNS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
]

# A 5 km spatial hash grid.
# Candidate distances are subsequently calculated exactly
# within our approximate local projected coordinate system.
SPATIAL_CELL_SIZE_KM = MAX_DISTANCE_KM


# ============================================================
# 2. IDENTIFY SOURCE PRODUCT
# ============================================================

def identify_product(filename):

    for product in PRODUCTS:
        if product in filename:
            return product

    return None


def identify_satellite(row):

    product = row["product"]

    if product == "VIIRS_SNPP_SP":
        return "VIIRS_SNPP"

    if product == "VIIRS_NOAA20_SP":
        return "VIIRS_NOAA20"

    # MODIS contains both Aqua and Terra.
    satellite = str(row["satellite"]).strip().lower()

    if "aqua" in satellite:
        return "MODIS_AQUA"

    if "terra" in satellite:
        return "MODIS_TERRA"

    return "MODIS_UNKNOWN"


# ============================================================
# 3. LOAD RAW DATA
# ============================================================

def load_data():

    files = sorted(RAW_DATA_DIR.rglob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DATA_DIR}"
        )

    frames = []

    print("=" * 75)
    print("LOADING FIRMS DATA")
    print("=" * 75)

    print(f"CSV files discovered: {len(files):,}")

    for index, file_path in enumerate(files, start=1):

        product = identify_product(file_path.name)

        if product is None:
            continue

        print(
            f"[{index}/{len(files)}] "
            f"{file_path.name}"
        )

        df = pd.read_csv(file_path)

        missing = [
            col for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"{file_path.name} is missing {missing}"
            )

        # Preserve source-row provenance.
        df["source_file"] = file_path.name

        df["latitude"] = pd.to_numeric(
            df["latitude"], errors="coerce"
        )

        df["longitude"] = pd.to_numeric(
            df["longitude"], errors="coerce"
        )

        df["product"] = product

        frames.append(df)

    if not frames:
        raise ValueError("No FIRMS data was loaded.")

    data = pd.concat(
        frames,
        ignore_index=True
    )

    # Validate coordinates.
    valid_coordinates = (
        data["latitude"].between(-90, 90)
        & data["longitude"].between(-180, 180)
    )

    invalid_coordinates = int(
        (~valid_coordinates).sum()
    )

    data = data.loc[valid_coordinates].copy()

    # --------------------------------------------------------
    # Parse acquisition date and time.
    # --------------------------------------------------------

    data["acq_time_numeric"] = pd.to_numeric(
        data["acq_time"], errors="coerce"
    )

    valid_time_numeric = (
        data["acq_time_numeric"].notna()
        & (data["acq_time_numeric"] >= 0)
        & (data["acq_time_numeric"] <= 2359)
        & (
            data["acq_time_numeric"]
            .mod(100) < 60
        )
    )

    data["acq_time_string"] = (
        data["acq_time_numeric"]
        .fillna(-1)
        .astype(int)
        .astype(str)
        .str.zfill(4)
    )

    timestamp_strings = (
        data["acq_date"].astype(str).str.strip()
        + " "
        + data["acq_time_string"]
    )

    data["acquisition_datetime"] = pd.to_datetime(
        timestamp_strings,
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True
    )

    valid_timestamps = (
        valid_time_numeric
        & data["acquisition_datetime"].notna()
    )

    invalid_timestamps = int(
        (~valid_timestamps).sum()
    )

    data = data.loc[valid_timestamps].copy()

    # Separate satellite sources.
    data["source"] = data.apply(
        identify_satellite,
        axis=1
    )

    data = data[
        data["source"].isin([
            "MODIS_AQUA",
            "MODIS_TERRA",
            "VIIRS_SNPP",
            "VIIRS_NOAA20",
        ])
    ].copy()

    data = data.reset_index(drop=True)

    print("\nData validation:")
    print(f"Invalid coordinates: {invalid_coordinates:,}")
    print(f"Invalid timestamps:  {invalid_timestamps:,}")
    print(f"Valid detections:    {len(data):,}")

    print("\nDetections by satellite source:")
    print(
        data["source"].value_counts().to_string()
    )

    print(
        "\nTimestamp interpretation: acquisition date/time "
        "parsed as UTC."
    )

    return data


# ============================================================
# 4. PROJECT COORDINATES
# ============================================================

def project_coordinates(data):

    data = data.copy()

    reference_latitude = data["latitude"].mean()
    reference_longitude = data["longitude"].mean()

    lat0_rad = np.radians(reference_latitude)

    data["x_km"] = (
        EARTH_RADIUS_KM
        * np.radians(
            data["longitude"] - reference_longitude
        )
        * np.cos(lat0_rad)
    )

    data["y_km"] = (
        EARTH_RADIUS_KM
        * np.radians(
            data["latitude"] - reference_latitude
        )
    )

    print("\nProjection reference:")
    print(f"Latitude:  {reference_latitude:.6f}")
    print(f"Longitude: {reference_longitude:.6f}")

    return data


# ============================================================
# 5. BUILD SPATIAL HASH FOR SECOND SOURCE
# ============================================================

def build_spatial_hash(data_b):

    spatial_hash = defaultdict(list)

    for index, row in data_b.iterrows():

        gx = int(
            np.floor(
                row["x_km"] / SPATIAL_CELL_SIZE_KM
            )
        )

        gy = int(
            np.floor(
                row["y_km"] / SPATIAL_CELL_SIZE_KM
            )
        )

        spatial_hash[(gx, gy)].append(index)

    # Convert index lists into NumPy arrays.
    for key in spatial_hash:
        spatial_hash[key] = np.array(
            spatial_hash[key],
            dtype=np.int64
        )

    return spatial_hash


# ============================================================
# 6. GENERATE SPATIAL AND TEMPORAL CANDIDATES
# ============================================================

def generate_candidates(data_a, data_b):

    """
    Generate candidate pairs satisfying:

        Distance <= 5 km
        Absolute time difference <= 24 hours

    Candidate pairs are not confirmed fire-event matches.
    """

    data_a = data_a.reset_index(drop=True)
    data_b = data_b.reset_index(drop=True)

    spatial_hash = build_spatial_hash(data_b)

    b_x = data_b["x_km"].to_numpy()
    b_y = data_b["y_km"].to_numpy()

    # Convert timestamps into Unix seconds.
    b_time = (
        data_b["acquisition_datetime"]
        .astype("int64")
        .to_numpy()
        / 1_000_000_000
    )

    a_x = data_a["x_km"].to_numpy()
    a_y = data_a["y_km"].to_numpy()

    a_time = (
        data_a["acquisition_datetime"]
        .astype("int64")
        .to_numpy()
        / 1_000_000_000
    )

    all_distances = []
    all_time_differences = []
    all_a_indices = []
    all_b_indices = []

    for i in range(len(data_a)):

        gx = int(
            np.floor(
                a_x[i] / SPATIAL_CELL_SIZE_KM
            )
        )

        gy = int(
            np.floor(
                a_y[i] / SPATIAL_CELL_SIZE_KM
            )
        )

        nearby_indices = []

        # Search the surrounding 3 x 3 spatial cells.
        for dx in (-1, 0, 1):

            for dy in (-1, 0, 1):

                key = (gx + dx, gy + dy)

                if key in spatial_hash:
                    nearby_indices.append(
                        spatial_hash[key]
                    )

        if not nearby_indices:
            continue

        candidate_indices = np.concatenate(
            nearby_indices
        )

        # Euclidean distance in projected kilometres.
        dx = b_x[candidate_indices] - a_x[i]
        dy = b_y[candidate_indices] - a_y[i]

        distances = np.sqrt(
            dx * dx + dy * dy
        )

        spatial_mask = (
            distances <= MAX_DISTANCE_KM
        )

        if not np.any(spatial_mask):
            continue

        candidate_indices = (
            candidate_indices[spatial_mask]
        )

        distances = distances[spatial_mask]

        # Absolute acquisition-time difference in minutes.
        time_differences = (
            np.abs(
                b_time[candidate_indices] - a_time[i]
            ) / 60.0
        )

        temporal_mask = (
            time_differences
            <= MAX_TIME_DIFFERENCE_MIN
        )

        if not np.any(temporal_mask):
            continue

        candidate_indices = (
            candidate_indices[temporal_mask]
        )

        distances = distances[temporal_mask]

        time_differences = (
            time_differences[temporal_mask]
        )

        all_a_indices.append(
            np.full(
                len(candidate_indices),
                i,
                dtype=np.int64
            )
        )

        all_b_indices.append(candidate_indices)

        all_distances.append(distances)

        all_time_differences.append(
            time_differences
        )

    if not all_distances:

        return {
            "a_indices": np.array([], dtype=np.int64),
            "b_indices": np.array([], dtype=np.int64),
            "distances": np.array([], dtype=float),
            "time_differences": np.array([], dtype=float),
        }

    return {
        "a_indices": np.concatenate(all_a_indices),
        "b_indices": np.concatenate(all_b_indices),
        "distances": np.concatenate(all_distances),
        "time_differences": np.concatenate(
            all_time_differences
        ),
    }


# ============================================================
# 7. SUMMARIZE CANDIDATE DISTRIBUTIONS
# ============================================================

def summarize_pair(
    pair_name,
    source_a,
    source_b,
    candidates
):

    distances = candidates["distances"]
    time_differences = candidates["time_differences"]

    a_indices = candidates["a_indices"]
    b_indices = candidates["b_indices"]

    summary_rows = []
    histogram_rows = []
    ambiguity_rows = []

    total_candidates = len(distances)

    print(
        f"\n{pair_name}: "
        f"{total_candidates:,} candidates within "
        f"{MAX_DISTANCE_KM} km and "
        f"{MAX_TIME_DIFFERENCE_MIN} minutes"
    )

    for distance_limit in DISTANCE_THRESHOLDS_KM:

        spatial_mask = (
            distances <= distance_limit
        )

        selected_distances = distances[spatial_mask]

        selected_times = (
            time_differences[spatial_mask]
        )

        selected_a = a_indices[spatial_mask]
        selected_b = b_indices[spatial_mask]

        if len(selected_times) == 0:

            for time_limit in TIME_THRESHOLDS_MIN:

                summary_rows.append({
                    "pair": pair_name,
                    "source_a": source_a,
                    "source_b": source_b,
                    "distance_limit_km": distance_limit,
                    "time_limit_min": time_limit,
                    "candidate_pairs": 0,
                    "unique_detections_a": 0,
                    "unique_detections_b": 0,
                })

            continue

        # Non-overlapping temporal bins.
        for lower, upper, label in TIME_BINS:

            if upper == 1440:
                mask = (
                    (selected_times >= lower)
                    & (selected_times <= upper)
                )
            else:
                mask = (
                    (selected_times >= lower)
                    & (selected_times < upper)
                )

            histogram_rows.append({
                "pair": pair_name,
                "source_a": source_a,
                "source_b": source_b,
                "distance_limit_km": distance_limit,
                "time_bin": label,
                "time_lower_min": lower,
                "time_upper_min": upper,
                "candidate_pairs": int(mask.sum()),
            })

        # Cumulative temporal thresholds.
        for time_limit in TIME_THRESHOLDS_MIN:

            temporal_mask = (
                selected_times <= time_limit
            )

            pair_count = int(
                temporal_mask.sum()
            )

            unique_a = int(
                np.unique(
                    selected_a[temporal_mask]
                ).size
            )

            unique_b = int(
                np.unique(
                    selected_b[temporal_mask]
                ).size
            )

            summary_rows.append({
                "pair": pair_name,
                "source_a": source_a,
                "source_b": source_b,
                "distance_limit_km": distance_limit,
                "time_limit_min": time_limit,
                "candidate_pairs": pair_count,
                "unique_detections_a": unique_a,
                "unique_detections_b": unique_b,
            })

        # Candidate degree / ambiguity at 24 hours.
        unique_a, counts_a = np.unique(
            selected_a,
            return_counts=True
        )

        unique_b, counts_b = np.unique(
            selected_b,
            return_counts=True
        )

        ambiguity_rows.extend([
            {
                "pair": pair_name,
                "distance_limit_km": distance_limit,
                "source": source_a,
                "unique_detections": len(unique_a),
                "median_candidate_partners": float(
                    np.median(counts_a)
                ),
                "p90_candidate_partners": float(
                    np.percentile(counts_a, 90)
                ),
                "maximum_candidate_partners": int(
                    counts_a.max()
                ),
            },
            {
                "pair": pair_name,
                "distance_limit_km": distance_limit,
                "source": source_b,
                "unique_detections": len(unique_b),
                "median_candidate_partners": float(
                    np.median(counts_b)
                ),
                "p90_candidate_partners": float(
                    np.percentile(counts_b, 90)
                ),
                "maximum_candidate_partners": int(
                    counts_b.max()
                ),
            }
        ])

    return (
        summary_rows,
        histogram_rows,
        ambiguity_rows
    )


# ============================================================
# 8. DEFINE SIX SATELLITE PAIRS
# ============================================================

SATELLITE_PAIRS = [
    ("MODIS_AQUA", "VIIRS_NOAA20"),
    ("MODIS_AQUA", "VIIRS_SNPP"),
    ("MODIS_TERRA", "VIIRS_NOAA20"),
    ("MODIS_TERRA", "VIIRS_SNPP"),
    ("MODIS_AQUA", "MODIS_TERRA"),
    ("VIIRS_SNPP", "VIIRS_NOAA20"),
]


# ============================================================
# 9. MAIN EXECUTION
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    data = load_data()

    data = project_coordinates(data)

    # Retain only sources used in this experiment.
    data = data[
        data["source"].isin([
            source
            for pair in SATELLITE_PAIRS
            for source in pair
        ])
    ].copy()

    all_summary = []
    all_histograms = []
    all_ambiguity = []

    print("\n" + "=" * 75)
    print("TEMPORAL COMPATIBILITY ANALYSIS")
    print("=" * 75)

    for source_a, source_b in SATELLITE_PAIRS:

        print("\n" + "-" * 75)
        print(f"PAIR: {source_a} vs {source_b}")
        print("-" * 75)

        data_a = data[
            data["source"] == source_a
        ].copy()

        data_b = data[
            data["source"] == source_b
        ].copy()

        print(f"{source_a} detections: {len(data_a):,}")
        print(f"{source_b} detections: {len(data_b):,}")

        if data_a.empty or data_b.empty:
            print("Skipping: one source has no detections.")
            continue

        candidates = generate_candidates(
            data_a,
            data_b
        )

        (
            summary_rows,
            histogram_rows,
            ambiguity_rows
        ) = summarize_pair(
            f"{source_a}__{source_b}",
            source_a,
            source_b,
            candidates
        )

        all_summary.extend(summary_rows)
        all_histograms.extend(histogram_rows)
        all_ambiguity.extend(ambiguity_rows)

        del candidates

    # --------------------------------------------------------
    # Save outputs.
    # --------------------------------------------------------

    summary_df = pd.DataFrame(all_summary)

    histogram_df = pd.DataFrame(all_histograms)

    ambiguity_df = pd.DataFrame(all_ambiguity)

    summary_df.to_csv(
        OUTPUT_DIR / "temporal_candidate_summary.csv",
        index=False
    )

    histogram_df.to_csv(
        OUTPUT_DIR / "temporal_difference_histograms.csv",
        index=False
    )

    ambiguity_df.to_csv(
        OUTPUT_DIR / "candidate_partner_ambiguity.csv",
        index=False
    )

    # --------------------------------------------------------
    # Print important results.
    # --------------------------------------------------------

    print("\n" + "=" * 75)
    print("CANDIDATE COUNTS BY PAIR")
    print("=" * 75)

    if not summary_df.empty:

        overview = (
            summary_df[
                summary_df["time_limit_min"] == 1440
            ][
                [
                    "pair",
                    "distance_limit_km",
                    "candidate_pairs",
                    "unique_detections_a",
                    "unique_detections_b",
                ]
            ]
        )

        print(
            overview.to_string(index=False)
        )

    print("\n" + "=" * 75)
    print("TEMPORAL DIFFERENCE HISTOGRAMS")
    print("=" * 75)

    if not histogram_df.empty:
        print(
            histogram_df.to_string(index=False)
        )

    print("\n" + "=" * 75)
    print("CANDIDATE PARTNER AMBIGUITY")
    print("=" * 75)

    if not ambiguity_df.empty:
        print(
            ambiguity_df.to_string(index=False)
        )

    print("\n" + "=" * 75)
    print("ANALYSIS COMPLETED")
    print("=" * 75)

    print(f"\nOutput directory:\n{OUTPUT_DIR}")

    for file_path in sorted(OUTPUT_DIR.iterdir()):
        print(" -", file_path.name)


if __name__ == "__main__":
    main()
