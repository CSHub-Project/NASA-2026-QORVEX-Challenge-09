
"""Independently validate the QORVEX Victoria 2024 Parquet datasets."""

from pathlib import Path

import h3
import pandas as pd
import pyarrow.parquet as pq


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

OUTPUT_DIR = Path("data/processed/victoria_2024")

INDEXED_PATH = OUTPUT_DIR / "spatially_indexed_detections.parquet"
DAILY_PATH = OUTPUT_DIR / "daily_activity.parquet"

EXPECTED_INDEXED_ROWS = 91_265
EXPECTED_DAILY_ROWS = 25_779

EXPECTED_PRODUCT_COUNTS = {
    "MODIS_SP": 10_582,
    "VIIRS_NOAA20_SP": 39_314,
    "VIIRS_SNPP_SP": 41_369,
}

INDEXED_COLUMNS = [
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
    "h3_res5",
    "h3_res7",
    "h3_res8",
    "h3_res9",
]

DAILY_COLUMNS = [
    "date_utc",
    "h3_res7",
    "modis_detection_count",
    "noaa20_detection_count",
    "snpp_detection_count",
    "combined_detection_count",
    "modis_frp_mean_mw",
    "modis_frp_max_mw",
    "modis_frp_sum_mw",
    "noaa20_frp_mean_mw",
    "noaa20_frp_max_mw",
    "noaa20_frp_sum_mw",
    "snpp_frp_mean_mw",
    "snpp_frp_max_mw",
    "snpp_frp_sum_mw",
    "active_product_count",
    "first_detection_utc",
    "last_detection_utc",
]

H3_COLUMNS = {
    "h3_res5": 5,
    "h3_res7": 7,
    "h3_res8": 8,
    "h3_res9": 9,
}


# ---------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------

def require(condition, message):
    """Raise an assertion error when a validation fails."""
    if not condition:
        raise AssertionError(message)


def validate_h3_cells(series, expected_resolution, column_name):
    """Validate H3 cell identifiers and their resolutions."""

    invalid = []

    for index, cell in enumerate(series):
        if not isinstance(cell, str):
            invalid.append((index, cell, "not a string"))
            continue

        if not h3.is_valid_cell(cell):
            invalid.append((index, cell, "invalid H3 cell"))
            continue

        if h3.get_resolution(cell) != expected_resolution:
            invalid.append((index, cell, "incorrect resolution"))

        if len(invalid) >= 5:
            break

    require(
        not invalid,
        f"{column_name}: invalid H3 values found: {invalid}",
    )


# ---------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------

def main():
    print("=" * 65)
    print("QORVEX — Victoria 2024 Parquet Quality Control")
    print("=" * 65)

    require(INDEXED_PATH.is_file(), f"Missing file: {INDEXED_PATH}")
    require(DAILY_PATH.is_file(), f"Missing file: {DAILY_PATH}")

    # Read Parquet metadata and schemas.
    indexed_metadata = pq.read_metadata(INDEXED_PATH)
    daily_metadata = pq.read_metadata(DAILY_PATH)

    indexed_schema = pq.read_schema(INDEXED_PATH)
    daily_schema = pq.read_schema(DAILY_PATH)

    print("\n[1/7] Checking Parquet schemas...")

    require(
        indexed_schema.names == INDEXED_COLUMNS,
        "Indexed dataset columns do not match the expected schema.",
    )

    require(
        daily_schema.names == DAILY_COLUMNS,
        "Daily dataset columns do not match the expected schema.",
    )

    print("PASS: Both schemas contain the expected columns and order.")

    # Load datasets for content-level validation.
    indexed = pq.read_table(INDEXED_PATH).to_pandas()
    daily = pq.read_table(DAILY_PATH).to_pandas()

    print("\n[2/7] Checking row counts...")

    require(
        len(indexed) == EXPECTED_INDEXED_ROWS,
        f"Expected {EXPECTED_INDEXED_ROWS:,} indexed rows; "
        f"found {len(indexed):,}.",
    )

    require(
        len(daily) == EXPECTED_DAILY_ROWS,
        f"Expected {EXPECTED_DAILY_ROWS:,} daily rows; "
        f"found {len(daily):,}.",
    )

    print(f"PASS: Indexed rows = {len(indexed):,}")
    print(f"PASS: Daily rows = {len(daily):,}")

    print("\n[3/7] Checking indexed detection records...")

    required_indexed = [
        "timestamp_utc",
        "latitude",
        "longitude",
        "source_product",
        "source_file",
        "source_record_id",
        "frp_mw",
    ]

    require(
        not indexed[required_indexed].isnull().any().any(),
        "Null values found in required indexed fields.",
    )

    require(
        indexed["source_product"].isin(EXPECTED_PRODUCT_COUNTS).all(),
        "Unexpected source_product value found.",
    )

    require(
        indexed["latitude"].between(-90, 90).all(),
        "Latitude outside valid geographic bounds.",
    )

    require(
        indexed["longitude"].between(-180, 180).all(),
        "Longitude outside valid geographic bounds.",
    )

    require(
        (indexed["frp_mw"] >= 0).all(),
        "Negative FRP value found.",
    )

    require(
        indexed["timestamp_utc"].dt.tz is not None,
        "Indexed timestamps are not timezone-aware.",
    )

    require(
        str(indexed["timestamp_utc"].dt.tz) == "UTC",
        "Indexed timestamps are not in UTC.",
    )

    require(
        not indexed.duplicated(
            subset=["source_file", "source_record_id"]
        ).any(),
        "Duplicate source file/record ID combination found.",
    )

    actual_product_counts = (
        indexed["source_product"].value_counts().to_dict()
    )

    require(
        actual_product_counts == EXPECTED_PRODUCT_COUNTS,
        f"Product counts mismatch: {actual_product_counts}",
    )

    print("PASS: Required fields, coordinates, FRP and timestamps.")
    print("PASS: Source record identifiers are unique within files.")
    print("PASS: Product counts reconcile with ingestion.")

    for product, count in sorted(actual_product_counts.items()):
        print(f"  {product}: {count:,}")

    print("\n[4/7] Validating H3 identifiers...")

    for column, resolution in H3_COLUMNS.items():
        validate_h3_cells(
            indexed[column],
            resolution,
            column,
        )
        print(f"PASS: {column} — resolution {resolution}")

    print("\n[5/7] Checking H3 coordinates against source coordinates...")

    for column, resolution in H3_COLUMNS.items():
        expected_cells = [
            h3.latlng_to_cell(lat, lon, resolution)
            for lat, lon in zip(
                indexed["latitude"],
                indexed["longitude"],
            )
        ]

        mismatches = sum(
            actual != expected
            for actual, expected in zip(
                indexed[column],
                expected_cells,
            )
        )

        require(
            mismatches == 0,
            f"{column}: {mismatches:,} cells do not match coordinates.",
        )

        print(f"PASS: {column} matches all source coordinates.")

    print("\n[6/7] Checking daily activity aggregates...")

    require(
        not daily[
            ["date_utc", "h3_res7"]
        ].isnull().any().any(),
        "Null date or H3 cell found in daily dataset.",
    )

    require(
        not daily.duplicated(
            subset=["date_utc", "h3_res7"]
        ).any(),
        "Duplicate date/H3 resolution-7 group found.",
    )

    validate_h3_cells(daily["h3_res7"], 7, "daily.h3_res7")

    count_columns = [
        "modis_detection_count",
        "noaa20_detection_count",
        "snpp_detection_count",
        "combined_detection_count",
        "active_product_count",
    ]

    require(
        not daily[count_columns].isnull().any().any(),
        "Null detection count found.",
    )

    require(
        (daily[count_columns] >= 0).all().all(),
        "Negative detection count found.",
    )

    calculated_combined = (
        daily["modis_detection_count"]
        + daily["noaa20_detection_count"]
        + daily["snpp_detection_count"]
    )

    require(
        (calculated_combined == daily["combined_detection_count"]).all(),
        "Combined detection counts do not equal product-specific counts.",
    )

    calculated_active_products = (
        (daily["modis_detection_count"] > 0).astype(int)
        + (daily["noaa20_detection_count"] > 0).astype(int)
        + (daily["snpp_detection_count"] > 0).astype(int)
    )

    require(
        (
            calculated_active_products == daily["active_product_count"]
        ).all(),
        "Active product counts are inconsistent.",
    )

    daily_product_totals = {
        "MODIS_SP": int(daily["modis_detection_count"].sum()),
        "VIIRS_NOAA20_SP": int(daily["noaa20_detection_count"].sum()),
        "VIIRS_SNPP_SP": int(daily["snpp_detection_count"].sum()),
    }

    require(
        daily_product_totals == EXPECTED_PRODUCT_COUNTS,
        f"Daily product totals mismatch: {daily_product_totals}",
    )

    require(
        int(daily["combined_detection_count"].sum())
        == EXPECTED_INDEXED_ROWS,
        "Daily combined detection total does not equal indexed row count.",
    )

    require(
        daily["date_utc"].min() == pd.Timestamp("2024-01-01").date(),
        "Unexpected daily dataset start date.",
    )

    require(
        daily["date_utc"].max() == pd.Timestamp("2024-12-31").date(),
        "Unexpected daily dataset end date.",
    )

    require(
        daily["first_detection_utc"].notna().all()
        and daily["last_detection_utc"].notna().all(),
        "Missing first/last detection timestamp.",
    )

    require(
        (
            daily["first_detection_utc"]
            <= daily["last_detection_utc"]
        ).all(),
        "First detection occurs after last detection.",
    )

    print("PASS: Unique date/H3 groups.")
    print("PASS: Combined counts reconcile with product counts.")
    print("PASS: Daily product totals reconcile with indexed records.")
    print("PASS: Daily date range is 2024-01-01 to 2024-12-31.")
    print("PASS: First/last detection timestamps are consistent.")

    print("\n[7/7] Checking FRP aggregate consistency...")

    frp_columns = {
        "modis": (
            "modis_detection_count",
            "modis_frp_mean_mw",
            "modis_frp_max_mw",
            "modis_frp_sum_mw",
        ),
        "noaa20": (
            "noaa20_detection_count",
            "noaa20_frp_mean_mw",
            "noaa20_frp_max_mw",
            "noaa20_frp_sum_mw",
        ),
        "snpp": (
            "snpp_detection_count",
            "snpp_frp_mean_mw",
            "snpp_frp_max_mw",
            "snpp_frp_sum_mw",
        ),
    }

    for product, columns in frp_columns.items():
        count_col, mean_col, max_col, sum_col = columns

        present = daily[count_col] > 0
        absent = ~present

        require(
            daily.loc[present, [mean_col, max_col, sum_col]]
            .notna()
            .all()
            .all(),
            f"{product}: FRP statistics missing where detections exist.",
        )

        require(
            daily.loc[absent, [mean_col, max_col, sum_col]]
            .isna()
            .all()
            .all(),
            f"{product}: FRP statistics should be null without detections.",
        )

        require(
            (daily.loc[present, mean_col] >= 0).all()
            and (daily.loc[present, max_col] >= 0).all()
            and (daily.loc[present, sum_col] >= 0).all(),
            f"{product}: negative FRP aggregate found.",
        )

        require(
            (
                daily.loc[present, max_col]
                >= daily.loc[present, mean_col] - 1e-9
            ).all(),
            f"{product}: FRP maximum is below its mean.",
        )

        require(
            (
                daily.loc[present, sum_col]
                >= daily.loc[present, max_col] - 1e-9
            ).all(),
            f"{product}: FRP sum is below its maximum.",
        )

        print(f"PASS: {product} FRP statistics.")

    # Final report.
    print("\n" + "=" * 65)
    print("QUALITY CONTROL PASSED")
    print("=" * 65)

    print(f"Indexed Parquet rows: {len(indexed):,}")
    print(f"Daily activity rows: {len(daily):,}")
    print(f"Indexed Parquet size: {INDEXED_PATH.stat().st_size:,} bytes")
    print(f"Daily Parquet size: {DAILY_PATH.stat().st_size:,} bytes")

    print("\nAll implemented structural and consistency checks passed.")


if __name__ == "__main__":
    main()
