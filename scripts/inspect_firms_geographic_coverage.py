
from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")

OUTPUT_DIR = Path(
    r"C:\Users\Asus\data\geographic_coverage_analysis"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Approximate bounding box for Victoria, Australia.
# This is a broad geographic screening rectangle,
# NOT an official state boundary polygon.

VICTORIA_BOUNDS = {
    "min_lat": -39.2,
    "max_lat": -33.9,
    "min_lon": 140.9,
    "max_lon": 150.1
}


# ============================================================
# FIND CSV FILES
# ============================================================

if not DATA_DIR.exists():
    raise FileNotFoundError(
        f"Data directory not found: {DATA_DIR}"
    )

csv_files = sorted(DATA_DIR.rglob("*.csv"))

if not csv_files:
    raise FileNotFoundError(
        f"No CSV files found in {DATA_DIR}"
    )

print("=" * 75)
print("FIRMS GEOGRAPHIC COVERAGE INSPECTION")
print("=" * 75)

print(f"\nCSV files discovered: {len(csv_files)}")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_product(filename):

    name = filename.upper()

    if "MODIS_SP" in name:
        return "MODIS_SP"

    if "VIIRS_SNPP_SP" in name:
        return "VIIRS_SNPP_SP"

    if "VIIRS_NOAA20_SP" in name:
        return "VIIRS_NOAA20_SP"

    return "UNKNOWN"


def find_coordinate_columns(df):

    columns = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    lat_col = columns.get("latitude")
    lon_col = columns.get("longitude")

    if lat_col is None or lon_col is None:
        raise ValueError(
            "Latitude or longitude column not found."
        )

    return lat_col, lon_col


# ============================================================
# READ AND ANALYZE ALL FILES
# ============================================================

all_records = []
file_summary = []

for index, file_path in enumerate(csv_files, start=1):

    product = classify_product(file_path.name)

    print(
        f"[{index}/{len(csv_files)}] "
        f"Reading {file_path.name}"
    )

    try:

        data = pd.read_csv(
            file_path,
            low_memory=False
        )

        lat_col, lon_col = find_coordinate_columns(data)

        data[lat_col] = pd.to_numeric(
            data[lat_col],
            errors="coerce"
        )

        data[lon_col] = pd.to_numeric(
            data[lon_col],
            errors="coerce"
        )

        valid = data.dropna(
            subset=[lat_col, lon_col]
        ).copy()

        valid = valid.rename(
            columns={
                lat_col: "latitude",
                lon_col: "longitude"
            }
        )

        valid["source_file"] = file_path.name
        valid["product"] = product

        # Geographic validity check.
        valid_coordinates = (
            valid["latitude"].between(-90, 90)
            & valid["longitude"].between(-180, 180)
        )

        invalid_count = (~valid_coordinates).sum()

        valid = valid.loc[valid_coordinates].copy()

        # Victoria bounding-box test.
        inside_victoria_bbox = (
            valid["latitude"].between(
                VICTORIA_BOUNDS["min_lat"],
                VICTORIA_BOUNDS["max_lat"]
            )
            &
            valid["longitude"].between(
                VICTORIA_BOUNDS["min_lon"],
                VICTORIA_BOUNDS["max_lon"]
            )
        )

        valid["inside_victoria_bbox"] = inside_victoria_bbox

        file_summary.append({
            "filename": file_path.name,
            "product": product,
            "rows_in_file": len(data),
            "valid_coordinate_rows": len(valid),
            "invalid_coordinate_rows": invalid_count,
            "inside_victoria_bbox": inside_victoria_bbox.sum(),
            "outside_victoria_bbox": (~inside_victoria_bbox).sum()
        })

        all_records.append(valid)

    except Exception as error:

        print(f"ERROR reading {file_path.name}: {error}")


if not all_records:
    raise RuntimeError(
        "No valid coordinate records could be loaded."
    )


# ============================================================
# COMBINE RECORDS
# ============================================================

combined = pd.concat(
    all_records,
    ignore_index=True
)

print("\nTotal valid coordinate records:")
print(f"{len(combined):,}")


# ============================================================
# 1. OVERALL GEOGRAPHIC EXTENT
# ============================================================

print("\n" + "=" * 75)
print("OVERALL GEOGRAPHIC EXTENT")
print("=" * 75)

overall = {
    "total_records": len(combined),
    "minimum_latitude": combined["latitude"].min(),
    "maximum_latitude": combined["latitude"].max(),
    "minimum_longitude": combined["longitude"].min(),
    "maximum_longitude": combined["longitude"].max(),
    "mean_latitude": combined["latitude"].mean(),
    "mean_longitude": combined["longitude"].mean(),
    "inside_victoria_bbox": combined[
        "inside_victoria_bbox"
    ].sum(),
    "outside_victoria_bbox": (
        ~combined["inside_victoria_bbox"]
    ).sum()
}

for key, value in overall.items():
    print(f"{key}: {value}")


# ============================================================
# 2. PRODUCT-LEVEL GEOGRAPHIC EXTENT
# ============================================================

print("\n" + "=" * 75)
print("GEOGRAPHIC EXTENT BY PRODUCT")
print("=" * 75)

product_summary = (
    combined.groupby("product")
    .agg(
        total_detections=("latitude", "size"),
        min_latitude=("latitude", "min"),
        max_latitude=("latitude", "max"),
        min_longitude=("longitude", "min"),
        max_longitude=("longitude", "max"),
        mean_latitude=("latitude", "mean"),
        mean_longitude=("longitude", "mean"),
        inside_victoria_bbox=("inside_victoria_bbox", "sum")
    )
    .reset_index()
)

product_summary["outside_victoria_bbox"] = (
    product_summary["total_detections"]
    - product_summary["inside_victoria_bbox"]
)

product_summary["inside_bbox_percentage"] = (
    product_summary["inside_victoria_bbox"]
    / product_summary["total_detections"]
    * 100
)

print(
    product_summary.to_string(index=False)
)


# ============================================================
# 3. COORDINATE QUANTILES
# ============================================================

print("\n" + "=" * 75)
print("COORDINATE DISTRIBUTION")
print("=" * 75)

print(
    combined[
        ["latitude", "longitude"]
    ].describe(
        percentiles=[
            0.01,
            0.05,
            0.25,
            0.50,
            0.75,
            0.95,
            0.99
        ]
    ).to_string()
)


# ============================================================
# 4. DETECTIONS OUTSIDE VICTORIA BOUNDING BOX
# ============================================================

outside = combined.loc[
    ~combined["inside_victoria_bbox"]
].copy()

print("\n" + "=" * 75)
print("DETECTIONS OUTSIDE VICTORIA BOUNDING BOX")
print("=" * 75)

print(f"Outside records: {len(outside):,}")

if len(outside):

    print("\nSample of 20 outside records:")

    print(
        outside[
            [
                "product",
                "latitude",
                "longitude",
                "source_file"
            ]
        ].head(20).to_string(index=False)
    )


# ============================================================
# 5. SAVE RESULTS
# ============================================================

pd.DataFrame([overall]).to_csv(
    OUTPUT_DIR / "overall_geographic_extent.csv",
    index=False
)

product_summary.to_csv(
    OUTPUT_DIR / "product_geographic_extent.csv",
    index=False
)

pd.DataFrame(file_summary).to_csv(
    OUTPUT_DIR / "file_geographic_summary.csv",
    index=False
)

outside.to_csv(
    OUTPUT_DIR / "detections_outside_victoria_bbox.csv",
    index=False
)


# ============================================================
# 6. FINAL INTERPRETATION
# ============================================================

print("\n" + "=" * 75)
print("INITIAL GEOGRAPHIC ASSESSMENT")
print("=" * 75)

outside_percentage = (
    len(outside) / len(combined) * 100
)

inside_percentage = 100 - outside_percentage

print(
    f"Inside Victoria bounding box: "
    f"{inside_percentage:.2f}%"
)

print(
    f"Outside Victoria bounding box: "
    f"{outside_percentage:.2f}%"
)

if outside_percentage == 0:

    print(
        "\nAll detections fall inside the approximate "
        "Victoria bounding rectangle."
    )

    print(
        "This is consistent with Victoria-only coverage, "
        "but does not prove the original FIRMS AOI."
    )

elif inside_percentage >= 95:

    print(
        "\nMost detections fall inside the approximate "
        "Victoria bounding rectangle."
    )

    print(
        "Inspect outside records to determine whether "
        "they are boundary effects or genuinely distant detections."
    )

else:

    print(
        "\nThe dataset contains substantial detections "
        "outside the approximate Victoria bounding rectangle."
    )

    print(
        "It is not restricted to Victoria based on this "
        "geographic screening test."
    )

print("\nResults saved to:")
print(OUTPUT_DIR)

print("\nInspection completed.")
