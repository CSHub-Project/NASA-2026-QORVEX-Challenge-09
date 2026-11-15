
"""
Independent quality-control validation for the Victoria 2024
geographically filtered QORVEX analytical datasets.

Inputs:
    data/processed/victoria_2024_filtered/
        spatially_indexed_detections.parquet
        daily_activity.parquet

This script is read-only. It does not modify either dataset.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DATA_DIR = Path("data/processed/victoria_2024_filtered")

INDEXED_FILE = DATA_DIR / "spatially_indexed_detections.parquet"
DAILY_FILE = DATA_DIR / "daily_activity.parquet"

EXPECTED_RECORDS = 57_305
EXPECTED_DAILY_COLUMNS = 18

EXPECTED_PRODUCTS = {
    "MODIS_SP": 6_161,
    "VIIRS_NOAA20_SP": 25_300,
    "VIIRS_SNPP_SP": 25_844,
}

EXPECTED_SENSOR_NULLS = {
    "brightness_raw": 51_144,
    "brightness_11um_raw": 51_144,
    "viirs_bright_ti4": 6_161,
    "viirs_bright_ti5": 6_161,
}

H3_COLUMNS = [
    "h3_res5",
    "h3_res7",
    "h3_res8",
    "h3_res9",
]


# ---------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------

def check(condition, message):
    """Raise an error when a validation condition is not satisfied."""

    if not condition:
        raise AssertionError(message)

    print(f"[PASS] {message}")


# ---------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------

def main():

    print("=" * 70)
    print("QORVEX — Independent Victoria 2024 Dataset QC")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Check file availability
    # -------------------------------------------------------------

    print("\n1. FILE AVAILABILITY")
    print("-" * 70)

    check(
        INDEXED_FILE.is_file(),
        f"Indexed dataset exists: {INDEXED_FILE}",
    )

    check(
        DAILY_FILE.is_file(),
        f"Daily dataset exists: {DAILY_FILE}",
    )

    # -------------------------------------------------------------
    # 2. Load datasets
    # -------------------------------------------------------------

    print("\n2. DATASET LOADING")
    print("-" * 70)

    indexed = pd.read_parquet(INDEXED_FILE)
    daily = pd.read_parquet(DAILY_FILE)

    print(f"Indexed records: {len(indexed):,}")
    print(f"Daily records:   {len(daily):,}")

    # -------------------------------------------------------------
    # 3. Indexed dataset structure
    # -------------------------------------------------------------

    print("\n3. INDEXED DATASET STRUCTURE")
    print("-" * 70)

    check(
        len(indexed) == EXPECTED_RECORDS,
        f"Indexed record count is {EXPECTED_RECORDS:,}",
    )

    expected_columns = {
        "timestamp_utc",
        "latitude",
        "longitude",
        "sensor",
        "satellite_raw",
        "source_product",
        "processing_type",
        "source_file",
        "source_record_id",
        "confidence_raw",
        "confidence_type",
        "frp_mw",
        "brightness_raw",
        "brightness_11um_raw",
        "viirs_bright_ti4",
        "viirs_bright_ti5",
        "scan",
        "track",
        "daynight_raw",
        "source_type_raw",
        "product_version",
        *H3_COLUMNS,
    }

    check(
        expected_columns.issubset(set(indexed.columns)),
        "All expected indexed dataset columns exist",
    )

    print(f"Indexed columns: {len(indexed.columns)}")

    # -------------------------------------------------------------
    # 4. Product distribution
    # -------------------------------------------------------------

    print("\n4. PRODUCT DISTRIBUTION")
    print("-" * 70)

    actual_products = (
        indexed["source_product"]
        .value_counts()
        .to_dict()
    )

    print(pd.Series(actual_products).to_string())

    check(
        actual_products == EXPECTED_PRODUCTS,
        "Product distribution matches expected counts",
    )

    # -------------------------------------------------------------
    # 5. Sensor/product consistency
    # -------------------------------------------------------------

    print("\n5. SENSOR AND PRODUCT CONSISTENCY")
    print("-" * 70)

    modis_records = indexed[
        indexed["source_product"] == "MODIS_SP"
    ]

    viirs_records = indexed[
        indexed["source_product"].isin([
            "VIIRS_NOAA20_SP",
            "VIIRS_SNPP_SP",
        ])
    ]

    check(
        (modis_records["sensor"] == "MODIS").all(),
        "All MODIS_SP records are classified as MODIS",
    )

    check(
        (viirs_records["sensor"] == "VIIRS").all(),
        "All VIIRS records are classified as VIIRS",
    )

    check(
        (indexed["processing_type"] == "SP").all(),
        "All records have processing type SP",
    )

    # -------------------------------------------------------------
    # 6. Timestamp and coordinate validation
    # -------------------------------------------------------------

    print("\n6. TIMESTAMP AND COORDINATE VALIDATION")
    print("-" * 70)

    check(
        indexed["timestamp_utc"].notna().all(),
        "No missing timestamps",
    )

    check(
        (indexed["timestamp_utc"].dt.year == 2024).all(),
        "All timestamps belong to 2024",
    )

    check(
        np.isfinite(indexed["latitude"]).all(),
        "All latitudes are finite",
    )

    check(
        np.isfinite(indexed["longitude"]).all(),
        "All longitudes are finite",
    )

    check(
        indexed["latitude"].between(-90, 90).all(),
        "All latitudes are within valid geographic limits",
    )

    check(
        indexed["longitude"].between(-180, 180).all(),
        "All longitudes are within valid geographic limits",
    )

    # -------------------------------------------------------------
    # 7. H3 spatial index validation
    # -------------------------------------------------------------

    print("\n7. H3 SPATIAL INDEX VALIDATION")
    print("-" * 70)

    for column in H3_COLUMNS:

        check(
            indexed[column].notna().all(),
            f"No missing values in {column}",
        )

        print(
            f"{column}: "
            f"{indexed[column].nunique():,} unique cells"
        )

    # -------------------------------------------------------------
    # 8. Sensor-specific thermal null validation
    # -------------------------------------------------------------

    print("\n8. SENSOR-SPECIFIC THERMAL MEASUREMENTS")
    print("-" * 70)

    actual_nulls = indexed.isna().sum()

    for column, expected_count in EXPECTED_SENSOR_NULLS.items():

        actual_count = int(actual_nulls[column])

        print(
            f"{column}: "
            f"{actual_count:,} missing values"
        )

        check(
            actual_count == expected_count,
            f"{column} has the expected {expected_count:,} null values",
        )

    check(
        modis_records["viirs_bright_ti4"].isna().all()
        and modis_records["viirs_bright_ti5"].isna().all(),
        "VIIRS thermal fields are null for all MODIS records",
    )

    check(
        viirs_records["brightness_raw"].isna().all()
        and viirs_records["brightness_11um_raw"].isna().all(),
        "MODIS thermal fields are null for all VIIRS records",
    )

    # -------------------------------------------------------------
    # 9. Daily dataset structure
    # -------------------------------------------------------------

    print("\n9. DAILY DATASET STRUCTURE")
    print("-" * 70)

    check(
        len(daily.columns) == EXPECTED_DAILY_COLUMNS,
        f"Daily dataset contains {EXPECTED_DAILY_COLUMNS} columns",
    )

    check(
        {"date_utc", "h3_res7", "combined_detection_count"}
        .issubset(set(daily.columns)),
        "Required daily aggregation columns exist",
    )

    check(
        not daily.duplicated(
            ["date_utc", "h3_res7"]
        ).any(),
        "Daily date/H3 groups are unique",
    )

    check(
        daily["date_utc"].notna().all(),
        "No missing daily dates",
    )

    check(
        daily["h3_res7"].notna().all(),
        "No missing daily H3 resolution 7 indices",
    )

    # -------------------------------------------------------------
    # 10. Daily detection-count reconciliation
    # -------------------------------------------------------------

    print("\n10. DAILY DETECTION-COUNT RECONCILIATION")
    print("-" * 70)

    check(
        daily["combined_detection_count"].notna().all(),
        "No missing combined detection counts",
    )

    check(
        (daily["combined_detection_count"] >= 0).all(),
        "Daily detection counts are non-negative",
    )

    indexed_total = len(indexed)

    daily_total = int(
        daily["combined_detection_count"].sum()
    )

    print(f"Indexed detection total: {indexed_total:,}")
    print(f"Daily detection total:   {daily_total:,}")

    check(
        indexed_total == daily_total,
        "Daily counts reconcile exactly with indexed records",
    )

    # -------------------------------------------------------------
    # 11. Daily date coverage
    # -------------------------------------------------------------

    print("\n11. DAILY DATE COVERAGE")
    print("-" * 70)

    first_date = daily["date_utc"].min()
    last_date = daily["date_utc"].max()

    print(f"First daily record: {first_date}")
    print(f"Last daily record:  {last_date}")

    check(
        pd.Timestamp(first_date).year == 2024
        and pd.Timestamp(last_date).year == 2024,
        "Daily activity date range belongs to 2024",
    )

    print(
        f"Distinct dates with recorded activity: "
        f"{daily['date_utc'].nunique():,}"
    )

    # -------------------------------------------------------------
    # 12. Final report
    # -------------------------------------------------------------

    print("\n" + "=" * 70)
    print("INDEPENDENT QC COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print(f"Indexed detections: {len(indexed):,}")
    print(f"Daily activity rows: {len(daily):,}")
    print(f"Distinct H3 cells (resolution 7): "
          f"{daily['h3_res7'].nunique():,}")

    print("\nBoth Parquet datasets passed all QC checks.")
    print("No source files or analytical datasets were modified.")


if __name__ == "__main__":
    main()
