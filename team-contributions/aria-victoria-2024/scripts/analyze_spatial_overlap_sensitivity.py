
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

RAW_DATA_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")

OUTPUT_DIR = Path(
    r"C:\Users\Asus\data\spatial_overlap_sensitivity"
)

PRODUCTS = [
    "MODIS_SP",
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
]

GRID_SIZES_KM = [1, 2, 5, 10]

# Each pair represents a shift in grid origin:
# (east-west fraction, north-south fraction)
GRID_OFFSETS = [
    (0.0, 0.0),
    (0.5, 0.0),
    (0.0, 0.5),
    (0.5, 0.5),
]

EARTH_RADIUS_KM = 6371.0088

REQUIRED_COLUMNS = ["latitude", "longitude"]


# ============================================================
# 2. LOAD RAW DATA
# ============================================================

def identify_product(filename):

    for product in PRODUCTS:
        if product in filename:
            return product

    return None


def load_data():

    files = sorted(RAW_DATA_DIR.rglob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DATA_DIR}"
        )

    frames = []

    print("=" * 75)
    print("LOADING RAW FIRMS DETECTIONS")
    print("=" * 75)

    for i, file_path in enumerate(files, start=1):

        product = identify_product(file_path.name)

        if product is None:
            continue

        print(
            f"[{i}/{len(files)}] {file_path.name}"
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

        df["latitude"] = pd.to_numeric(
            df["latitude"], errors="coerce"
        )

        df["longitude"] = pd.to_numeric(
            df["longitude"], errors="coerce"
        )

        df = df.dropna(
            subset=["latitude", "longitude"]
        ).copy()

        valid = (
            df["latitude"].between(-90, 90)
            & df["longitude"].between(-180, 180)
        )

        df = df.loc[valid].copy()

        df["product"] = product

        frames.append(
            df[["latitude", "longitude", "product"]]
        )

    if not frames:
        raise ValueError("No valid records loaded.")

    data = pd.concat(
        frames,
        ignore_index=True
    )

    print("\nTotal detections:", f"{len(data):,}")

    print("\nDetections by product:")
    print(data["product"].value_counts().to_string())

    return data


# ============================================================
# 3. PROJECT COORDINATES
# ============================================================

def project_coordinates(data):

    data = data.copy()

    lat0 = data["latitude"].mean()
    lon0 = data["longitude"].mean()

    lat0_rad = np.radians(lat0)

    data["x_km"] = (
        EARTH_RADIUS_KM
        * np.radians(data["longitude"] - lon0)
        * np.cos(lat0_rad)
    )

    data["y_km"] = (
        EARTH_RADIUS_KM
        * np.radians(data["latitude"] - lat0)
    )

    print("\nProjection reference:")
    print(f"Latitude:  {lat0:.6f}")
    print(f"Longitude: {lon0:.6f}")

    return data


# ============================================================
# 4. CALCULATE OVERLAP FOR ONE CONFIGURATION
# ============================================================

def analyze_configuration(
    data,
    grid_size,
    offset_x,
    offset_y
):

    # Establish a fixed reference origin for this resolution.
    base_x = (
        np.floor(data["x_km"].min() / grid_size)
        * grid_size
    )

    base_y = (
        np.floor(data["y_km"].min() / grid_size)
        * grid_size
    )

    # Shift the origin by the specified fraction of a cell.
    origin_x = base_x + offset_x * grid_size
    origin_y = base_y + offset_y * grid_size

    work = data.copy()

    work["grid_x"] = np.floor(
        (work["x_km"] - origin_x) / grid_size
    ).astype(int)

    work["grid_y"] = np.floor(
        (work["y_km"] - origin_y) / grid_size
    ).astype(int)

    work["grid_id"] = (
        work["grid_x"].astype(str)
        + "_"
        + work["grid_y"].astype(str)
    )

    # One set of occupied cells per product.
    product_cells = {}

    for product in PRODUCTS:

        subset = work[
            work["product"] == product
        ]

        product_cells[product] = set(
            zip(
                subset["grid_x"],
                subset["grid_y"]
            )
        )

    # Detection counts per occupied cell and product.
    cell_counts = (
        work.groupby(
            ["grid_x", "grid_y", "product"]
        )
        .size()
        .unstack(fill_value=0)
    )

    for product in PRODUCTS:
        if product not in cell_counts.columns:
            cell_counts[product] = 0

    cell_counts = cell_counts[PRODUCTS]

    # Cell occupancy composition.
    sets = [
        product_cells[p] for p in PRODUCTS
    ]

    only_one = (
        (sets[0] - sets[1] - sets[2])
        | (sets[1] - sets[0] - sets[2])
        | (sets[2] - sets[0] - sets[1])
    )

    exactly_two = (
        (sets[0] & sets[1]) - sets[2]
    ) | (
        (sets[0] & sets[2]) - sets[1]
    ) | (
        (sets[1] & sets[2]) - sets[0]
    )

    all_three = (
        sets[0] & sets[1] & sets[2]
    )

    union_cells = sets[0] | sets[1] | sets[2]

    occupancy_rows = [
        {
            "grid_size_km": grid_size,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "occupancy": "one_product",
            "grid_cells": len(only_one),
        },
        {
            "grid_size_km": grid_size,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "occupancy": "exactly_two_products",
            "grid_cells": len(exactly_two),
        },
        {
            "grid_size_km": grid_size,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "occupancy": "all_three_products",
            "grid_cells": len(all_three),
        },
    ]

    # Configuration-level summary.
    summary = {
        "grid_size_km": grid_size,
        "offset_x": offset_x,
        "offset_y": offset_y,
        "total_occupied_cells": len(union_cells),
        "one_product_cells": len(only_one),
        "exactly_two_product_cells": len(exactly_two),
        "all_three_product_cells": len(all_three),
    }

    if union_cells:
        summary["one_product_percentage"] = (
            len(only_one) / len(union_cells) * 100
        )

        summary["exactly_two_product_percentage"] = (
            len(exactly_two) / len(union_cells) * 100
        )

        summary["all_three_product_percentage"] = (
            len(all_three) / len(union_cells) * 100
        )

    # Pairwise overlap.
    pair_rows = []

    for product_a, product_b in combinations(PRODUCTS, 2):

        cells_a = product_cells[product_a]
        cells_b = product_cells[product_b]

        shared = cells_a & cells_b

        detections_a = int(
            cell_counts.loc[
                cell_counts.index.isin(shared),
                product_a
            ].sum()
        )

        detections_b = int(
            cell_counts.loc[
                cell_counts.index.isin(shared),
                product_b
            ].sum()
        )

        pair_rows.append({
            "grid_size_km": grid_size,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "product_a": product_a,
            "product_b": product_b,
            "occupied_cells_a": len(cells_a),
            "occupied_cells_b": len(cells_b),
            "shared_cells": len(shared),
            "percentage_a_cells_shared": (
                len(shared) / len(cells_a) * 100
                if cells_a else 0
            ),
            "percentage_b_cells_shared": (
                len(shared) / len(cells_b) * 100
                if cells_b else 0
            ),
            "detections_a_in_shared_cells": detections_a,
            "detections_b_in_shared_cells": detections_b,
            "percentage_a_detections_in_shared_cells": (
                detections_a
                / int(cell_counts[product_a].sum())
                * 100
                if cell_counts[product_a].sum() else 0
            ),
            "percentage_b_detections_in_shared_cells": (
                detections_b
                / int(cell_counts[product_b].sum())
                * 100
                if cell_counts[product_b].sum() else 0
            ),
        })

    # Three-way overlap.
    three_way_rows = []

    for product in PRODUCTS:

        total_detections = int(
            cell_counts[product].sum()
        )

        detections_in_three_way = int(
            cell_counts.loc[
                cell_counts.index.isin(all_three),
                product
            ].sum()
        )

        three_way_rows.append({
            "grid_size_km": grid_size,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "product": product,
            "three_way_shared_cells": len(all_three),
            "total_product_detections": total_detections,
            "detections_in_three_way_cells": (
                detections_in_three_way
            ),
            "percentage_detections_in_three_way_cells": (
                detections_in_three_way
                / total_detections * 100
                if total_detections else 0
            ),
        })

    # Save cell counts for this configuration.
    cell_output = cell_counts.reset_index()

    cell_output["grid_size_km"] = grid_size
    cell_output["offset_x"] = offset_x
    cell_output["offset_y"] = offset_y

    return (
        summary,
        occupancy_rows,
        pair_rows,
        three_way_rows,
        cell_output
    )


# ============================================================
# 5. MAIN EXECUTION
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    data = load_data()

    data = project_coordinates(data)

    summary_results = []
    occupancy_results = []
    pair_results = []
    three_way_results = []
    cell_results = []

    total_experiments = (
        len(GRID_SIZES_KM) * len(GRID_OFFSETS)
    )

    experiment = 0

    print("\n" + "=" * 75)
    print("MULTI-RESOLUTION SPATIAL OVERLAP SENSITIVITY")
    print("=" * 75)

    for grid_size in GRID_SIZES_KM:

        for offset_x, offset_y in GRID_OFFSETS:

            experiment += 1

            print(
                f"\nExperiment {experiment}/{total_experiments}"
            )

            print(
                f"Grid: {grid_size} km | "
                f"Offset X: {offset_x} | "
                f"Offset Y: {offset_y}"
            )

            (
                summary,
                occupancy,
                pairs,
                three_way,
                cells
            ) = analyze_configuration(
                data,
                grid_size,
                offset_x,
                offset_y
            )

            summary_results.append(summary)
            occupancy_results.extend(occupancy)
            pair_results.extend(pairs)
            three_way_results.extend(three_way)
            cell_results.append(cells)

            print(
                "Occupied cells:",
                summary["total_occupied_cells"]
            )

            print(
                "Three-way shared cells:",
                summary["all_three_product_cells"]
            )

    # Convert results to DataFrames.
    summary_df = pd.DataFrame(summary_results)
    occupancy_df = pd.DataFrame(occupancy_results)
    pairs_df = pd.DataFrame(pair_results)
    three_way_df = pd.DataFrame(three_way_results)

    cells_df = pd.concat(
        cell_results,
        ignore_index=True
    )

    # Save all outputs.
    summary_df.to_csv(
        OUTPUT_DIR / "resolution_origin_sensitivity.csv",
        index=False
    )

    occupancy_df.to_csv(
        OUTPUT_DIR / "occupancy_composition.csv",
        index=False
    )

    pairs_df.to_csv(
        OUTPUT_DIR / "pairwise_overlap_sensitivity.csv",
        index=False
    )

    three_way_df.to_csv(
        OUTPUT_DIR / "three_way_overlap_sensitivity.csv",
        index=False
    )

    cells_df.to_csv(
        OUTPUT_DIR / "grid_cell_counts_all_scenarios.csv",
        index=False
    )

    # Print concise results.
    print("\n" + "=" * 75)
    print("CONFIGURATION SUMMARY")
    print("=" * 75)

    print(
        summary_df.to_string(index=False)
    )

    print("\n" + "=" * 75)
    print("PAIRWISE OVERLAP SUMMARY")
    print("=" * 75)

    print(
        pairs_df[
            [
                "grid_size_km",
                "offset_x",
                "offset_y",
                "product_a",
                "product_b",
                "shared_cells",
                "percentage_a_cells_shared",
                "percentage_b_cells_shared",
            ]
        ].to_string(index=False)
    )

    print("\n" + "=" * 75)
    print("THREE-WAY OVERLAP SUMMARY")
    print("=" * 75)

    print(
        three_way_df.to_string(index=False)
    )

    print("\n" + "=" * 75)
    print("ANALYSIS COMPLETED")
    print("=" * 75)

    print(f"\nOutput directory:\n{OUTPUT_DIR}")

    for file_path in sorted(OUTPUT_DIR.iterdir()):
        print(" -", file_path.name)


if __name__ == "__main__":
    main()
