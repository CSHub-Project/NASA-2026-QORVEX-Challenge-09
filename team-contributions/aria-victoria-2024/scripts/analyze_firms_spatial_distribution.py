
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. CONFIGURATION
# ============================================================

RAW_DATA_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")

OUTPUT_DIR = Path(
    r"C:\Users\Asus\data\spatial_distribution_analysis"
)

GRID_SIZE_KM = 5.0

# Earth radius in kilometres
EARTH_RADIUS_KM = 6371.0088

# Product identifiers expected in the filenames
PRODUCTS = [
    "MODIS_SP",
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
]

REQUIRED_COLUMNS = ["latitude", "longitude"]

# Plot settings
SCATTER_POINT_SIZE = 2
SCATTER_ALPHA = 0.35
DPI = 300


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def identify_product(filename):
    """Identify the FIRMS product from its filename."""

    for product in PRODUCTS:
        if product in filename:
            return product

    return None


def load_firms_data():
    """Load all FIRMS CSV files and preserve their provenance."""

    files = sorted(RAW_DATA_DIR.rglob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV files found in: {RAW_DATA_DIR}"
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
            f"Reading {file_path.name}"
        )

        try:
            df = pd.read_csv(file_path)
        except Exception as exc:
            warnings.warn(
                f"Could not read {file_path}: {exc}"
            )
            continue

        missing = [
            col for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing:
            warnings.warn(
                f"Skipping {file_path.name}: "
                f"missing columns {missing}"
            )
            continue

        df["latitude"] = pd.to_numeric(
            df["latitude"], errors="coerce"
        )

        df["longitude"] = pd.to_numeric(
            df["longitude"], errors="coerce"
        )

        df = df.dropna(
            subset=["latitude", "longitude"]
        ).copy()

        # Preserve source information
        df["product"] = product
        df["source_file"] = file_path.name

        if "satellite" in df.columns:
            df["satellite"] = (
                df["satellite"]
                .astype(str)
                .str.strip()
            )
        else:
            df["satellite"] = "UNKNOWN"

        frames.append(df)

    if not frames:
        raise ValueError(
            "No valid FIRMS records were loaded."
        )

    data = pd.concat(
        frames,
        ignore_index=True
    )

    # Validate geographic coordinate ranges
    valid_coordinates = (
        data["latitude"].between(-90, 90)
        & data["longitude"].between(-180, 180)
    )

    invalid_count = int((~valid_coordinates).sum())

    if invalid_count:
        print(
            f"\nInvalid coordinate records removed: "
            f"{invalid_count:,}"
        )

    data = data.loc[valid_coordinates].copy()

    print("\nTotal valid detections:", f"{len(data):,}")

    print("\nDetections by product:")
    print(data["product"].value_counts().to_string())

    return data


# ============================================================
# 3. PROJECT COORDINATES TO APPROXIMATE LOCAL KILOMETRES
# ============================================================

def project_coordinates(data):
    """
    Apply a local equirectangular approximation.

    The projection is centred on the mean coordinates of
    the complete dataset.

    This is suitable for exploratory spatial analysis,
    not precision geodesic measurement.
    """

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

    return (
        data,
        reference_latitude,
        reference_longitude
    )


# ============================================================
# 4. ASSIGN DETECTIONS TO A COMMON 5 KM GRID
# ============================================================

def create_spatial_grid(data):
    """
    Assign every detection to a 5 km x 5 km grid cell.

    The same grid origin is used for all products.
    """

    data = data.copy()

    x_min = np.floor(
        data["x_km"].min() / GRID_SIZE_KM
    ) * GRID_SIZE_KM

    y_min = np.floor(
        data["y_km"].min() / GRID_SIZE_KM
    ) * GRID_SIZE_KM

    data["grid_x"] = np.floor(
        (data["x_km"] - x_min) / GRID_SIZE_KM
    ).astype(int)

    data["grid_y"] = np.floor(
        (data["y_km"] - y_min) / GRID_SIZE_KM
    ).astype(int)

    data["grid_id"] = (
        "X" + data["grid_x"].astype(str)
        + "_Y" + data["grid_y"].astype(str)
    )

    data["cell_center_x_km"] = (
        x_min
        + (data["grid_x"] + 0.5) * GRID_SIZE_KM
    )

    data["cell_center_y_km"] = (
        y_min
        + (data["grid_y"] + 0.5) * GRID_SIZE_KM
    )

    print("\nSpatial grid configuration:")
    print(f"Grid size: {GRID_SIZE_KM} km")
    print(f"Grid X origin: {x_min:.2f} km")
    print(f"Grid Y origin: {y_min:.2f} km")

    return data, x_min, y_min


# ============================================================
# 5. CREATE GRID-LEVEL DETECTION COUNTS
# ============================================================

def calculate_grid_counts(data):
    """Calculate detection counts per grid cell and product."""

    counts = (
        data.groupby(
            ["grid_id", "grid_x", "grid_y", "product"],
            observed=True
        )
        .size()
        .reset_index(name="detection_count")
    )

    wide = counts.pivot_table(
        index=["grid_id", "grid_x", "grid_y"],
        columns="product",
        values="detection_count",
        fill_value=0
    ).reset_index()

    # Ensure every product has a column
    for product in PRODUCTS:
        if product not in wide.columns:
            wide[product] = 0

    wide.columns.name = None

    wide["total_detections"] = (
        wide[PRODUCTS].sum(axis=1)
    )

    wide = wide.sort_values(
        "total_detections",
        ascending=False
    )

    return counts, wide


# ============================================================
# 6. CREATE OVERALL GEOGRAPHIC SUMMARY
# ============================================================

def calculate_geographic_summary(data):
    """Summarize geographic coverage per product."""

    rows = []

    for product in PRODUCTS:

        subset = data[
            data["product"] == product
        ]

        if subset.empty:
            continue

        rows.append({
            "product": product,
            "total_detections": len(subset),
            "min_latitude": subset["latitude"].min(),
            "max_latitude": subset["latitude"].max(),
            "min_longitude": subset["longitude"].min(),
            "max_longitude": subset["longitude"].max(),
            "mean_latitude": subset["latitude"].mean(),
            "mean_longitude": subset["longitude"].mean(),
            "occupied_grid_cells": subset["grid_id"].nunique(),
            "detections_per_occupied_cell": (
                len(subset) / subset["grid_id"].nunique()
            )
        })

    return pd.DataFrame(rows)


# ============================================================
# 7. PLOT ALL DETECTIONS
# ============================================================

def plot_all_detections(data):

    fig, ax = plt.subplots(figsize=(12, 9))

    for product in PRODUCTS:

        subset = data[
            data["product"] == product
        ]

        ax.scatter(
            subset["longitude"],
            subset["latitude"],
            s=SCATTER_POINT_SIZE,
            alpha=SCATTER_ALPHA,
            label=product
        )

    ax.set_title(
        "FIRMS Active Fire Detections - Victoria Region (2024)",
        fontsize=14
    )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    ax.legend()
    ax.grid(alpha=0.25)

    ax.set_aspect("equal", adjustable="datalim")

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "01_all_detections.png",
        dpi=DPI
    )

    plt.close(fig)


# ============================================================
# 8. PLOT INDIVIDUAL PRODUCT DISTRIBUTIONS
# ============================================================

def plot_individual_products(data):

    for index, product in enumerate(PRODUCTS, start=2):

        subset = data[
            data["product"] == product
        ]

        fig, ax = plt.subplots(figsize=(12, 9))

        ax.scatter(
            subset["longitude"],
            subset["latitude"],
            s=SCATTER_POINT_SIZE,
            alpha=SCATTER_ALPHA
        )

        ax.set_title(
            f"Geographic Distribution - {product}",
            fontsize=14
        )

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        ax.grid(alpha=0.25)

        ax.set_aspect("equal", adjustable="datalim")

        fig.tight_layout()

        fig.savefig(
            OUTPUT_DIR / f"{index:02d}_{product}_scatter.png",
            dpi=DPI
        )

        plt.close(fig)


# ============================================================
# 9. CREATE SPATIAL DENSITY HEATMAPS
# ============================================================

def plot_density_heatmap(
    data,
    x_min,
    y_min,
    product=None,
    output_filename="density.png",
    title="Spatial Density"
):
    """
    Plot detection counts in the common 5 km grid.

    Coordinates are displayed in approximate local kilometres.
    """

    if product is None:
        subset = data
    else:
        subset = data[
            data["product"] == product
        ]

    if subset.empty:
        print(f"No data available for {title}")
        return

    max_x = subset["grid_x"].max()
    max_y = subset["grid_y"].max()

    # Count detections in each cell
    grid = np.zeros(
        (max_y + 1, max_x + 1),
        dtype=np.int64
    )

    grouped = (
        subset.groupby(
            ["grid_x", "grid_y"]
        )
        .size()
    )

    for (gx, gy), count in grouped.items():
        grid[gy, gx] = count

    x_edges = (
        x_min
        + np.arange(max_x + 2) * GRID_SIZE_KM
    )

    y_edges = (
        y_min
        + np.arange(max_y + 2) * GRID_SIZE_KM
    )

    fig, ax = plt.subplots(figsize=(12, 9))

    mesh = ax.pcolormesh(
        x_edges,
        y_edges,
        grid,
        shading="flat"
    )

    colorbar = fig.colorbar(mesh, ax=ax)
    colorbar.set_label("Number of detections per 5 km cell")

    ax.set_title(title, fontsize=14)

    ax.set_xlabel(
        "Approximate distance east of reference point (km)"
    )

    ax.set_ylabel(
        "Approximate distance north of reference point (km)"
    )

    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.15)

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / output_filename,
        dpi=DPI
    )

    plt.close(fig)


# ============================================================
# 10. COMPARE PRODUCT DISTRIBUTIONS
# ============================================================

def calculate_product_grid_comparison(data):

    # Each row represents one occupied grid cell.
    # Each product has its own detection count.

    comparison = (
        data.groupby(
            ["grid_id", "grid_x", "grid_y", "product"]
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for product in PRODUCTS:
        if product not in comparison.columns:
            comparison[product] = 0

    comparison.columns.name = None

    comparison["total_detections"] = (
        comparison[PRODUCTS].sum(axis=1)
    )

    # Calculate each product's share of its own detections
    for product in PRODUCTS:

        total = comparison[product].sum()

        if total > 0:
            comparison[
                f"{product}_percentage_of_product"
            ] = (
                comparison[product] / total * 100
            )
        else:
            comparison[
                f"{product}_percentage_of_product"
            ] = 0.0

    return comparison


# ============================================================
# 11. MAIN EXECUTION
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\n" + "=" * 75)
    print("FIRMS SPATIAL DISTRIBUTION ANALYSIS")
    print("=" * 75)

    # Step 1: Load data
    data = load_firms_data()

    # Step 2: Project coordinates
    (
        data,
        reference_latitude,
        reference_longitude
    ) = project_coordinates(data)

    # Step 3: Create common spatial grid
    data, x_min, y_min = create_spatial_grid(data)

    # Step 4: Calculate grid counts
    long_counts, wide_counts = calculate_grid_counts(data)

    # Step 5: Geographic summary
    geographic_summary = calculate_geographic_summary(data)

    # Step 6: Product grid comparison
    grid_comparison = calculate_product_grid_comparison(data)

    # Step 7: Save CSV outputs
    data.to_csv(
        OUTPUT_DIR / "detections_with_spatial_grid.csv",
        index=False
    )

    long_counts.to_csv(
        OUTPUT_DIR / "grid_counts_long_format.csv",
        index=False
    )

    wide_counts.to_csv(
        OUTPUT_DIR / "grid_counts_by_product.csv",
        index=False
    )

    geographic_summary.to_csv(
        OUTPUT_DIR / "geographic_summary_by_product.csv",
        index=False
    )

    grid_comparison.to_csv(
        OUTPUT_DIR / "product_spatial_comparison.csv",
        index=False
    )

    # Step 8: Scatter plots
    print("\nGenerating scatter plots...")

    plot_all_detections(data)

    plot_individual_products(data)

    # Step 9: Density heatmaps
    print("\nGenerating spatial-density heatmaps...")

    plot_density_heatmap(
        data,
        x_min,
        y_min,
        output_filename="05_combined_density.png",
        title="Combined FIRMS Detection Density - 5 km Grid"
    )

    for index, product in enumerate(PRODUCTS, start=6):

        plot_density_heatmap(
            data,
            x_min,
            y_min,
            product=product,
            output_filename=(
                f"{index:02d}_{product}_density.png"
            ),
            title=f"Detection Density - {product}"
        )

    # Step 10: Print summary
    print("\n" + "=" * 75)
    print("GEOGRAPHIC SUMMARY BY PRODUCT")
    print("=" * 75)

    print(
        geographic_summary.to_string(index=False)
    )

    print("\n" + "=" * 75)
    print("MOST ACTIVE GRID CELLS")
    print("=" * 75)

    print(
        wide_counts.head(20).to_string(index=False)
    )

    print("\n" + "=" * 75)
    print("SPATIAL DISTRIBUTION ANALYSIS COMPLETED")
    print("=" * 75)

    print(f"\nOutput directory:\n{OUTPUT_DIR}")

    print("\nGenerated files:")
    for file_path in sorted(OUTPUT_DIR.iterdir()):
        print(" -", file_path.name)


if __name__ == "__main__":
    main()
