"""
Build a one-day global QORVEX analytical test dataset from a combined,
already-harmonized FIRMS CSV.

Outputs:
  data/processed/global_test_2024-01-01/
    spatially_indexed_detections.parquet
    daily_activity.parquet

The script preserves source metadata, adds H3 resolutions 5/7/8/9,
aggregates daily activity at H3 resolution 7, and refuses to overwrite
existing final outputs.
"""

from pathlib import Path
import math

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import h3

from qorvex.spatial_index import add_h3_indices
from qorvex.daily_aggregation import aggregate_daily_activity


SOURCE_FILE = Path("data/global_test/global_all_products_2024-01-01.csv")
OUTPUT_DIR = Path("data/processed/global_test_2024-01-01")
BATCH_SIZE = 10_000

EXPECTED_PRODUCTS = {
    "MODIS_SP",
    "VIIRS_NOAA20_SP",
    "VIIRS_SNPP_SP",
}

REQUIRED_SOURCE_COLUMNS = {
    "timestamp_utc", "latitude", "longitude", "sensor", "satellite_raw",
    "source_product", "processing_type", "source_file", "source_record_id",
    "confidence_raw", "confidence_type", "frp_mw", "brightness_raw",
    "brightness_11um_raw", "viirs_bright_ti4", "viirs_bright_ti5",
    "scan", "track", "daynight_raw", "source_type_raw", "product_version",
}

MANDATORY_SOURCE_COLUMNS = [
    "timestamp_utc", "latitude", "longitude", "sensor", "source_product",
]

INDEXED_SCHEMA = pa.schema([
    pa.field("timestamp_utc", pa.timestamp("us", tz="UTC")),
    pa.field("latitude", pa.float64()),
    pa.field("longitude", pa.float64()),
    pa.field("sensor", pa.string()),
    pa.field("satellite_raw", pa.string()),
    pa.field("source_product", pa.string()),
    pa.field("processing_type", pa.string()),
    pa.field("source_file", pa.string()),
    pa.field("source_record_id", pa.int64()),
    pa.field("confidence_raw", pa.string()),
    pa.field("confidence_type", pa.string()),
    pa.field("frp_mw", pa.float64()),
    pa.field("brightness_raw", pa.float64()),
    pa.field("brightness_11um_raw", pa.float64()),
    pa.field("viirs_bright_ti4", pa.float64()),
    pa.field("viirs_bright_ti5", pa.float64()),
    pa.field("scan", pa.float64()),
    pa.field("track", pa.float64()),
    pa.field("daynight_raw", pa.string()),
    pa.field("source_type_raw", pa.string()),
    pa.field("product_version", pa.string()),
    pa.field("h3_res5", pa.string()),
    pa.field("h3_res7", pa.string()),
    pa.field("h3_res8", pa.string()),
    pa.field("h3_res9", pa.string()),
])


def optional_text(value):
    if pd.isna(value):
        return None
    return str(value).strip()


def optional_float(value, field_name):
    if pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid numerical value in {field_name}: {value!r}"
        ) from exc
    if not math.isfinite(number):
        raise ValueError(
            f"Non-finite numerical value in {field_name}: {value!r}"
        )
    return number


def optional_int(value, field_name):
    number = optional_float(value, field_name)
    if number is None:
        return None
    if not number.is_integer():
        raise ValueError(
            f"Expected integer in {field_name}, received {value!r}"
        )
    return int(number)


def required_float(value, field_name):
    number = optional_float(value, field_name)
    if number is None:
        raise ValueError(f"Mandatory field {field_name} is missing.")
    return number


def load_source_data():
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(f"Source CSV not found: {SOURCE_FILE}")

    print(f"Loading source: {SOURCE_FILE}")
    data = pd.read_csv(SOURCE_FILE)

    missing = REQUIRED_SOURCE_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Source CSV is missing columns: {sorted(missing)}")
    if data.empty:
        raise ValueError("Source CSV contains no records.")

    missing_mandatory = data[MANDATORY_SOURCE_COLUMNS].isna().sum()
    if missing_mandatory.any():
        raise ValueError(
            "Mandatory source fields contain nulls:\n"
            f"{missing_mandatory[missing_mandatory > 0]}"
        )

    products = set(
        data["source_product"].astype(str).str.strip().str.upper().unique()
    )
    if products != EXPECTED_PRODUCTS:
        raise ValueError(f"Unexpected product set: {sorted(products)}")

    expected_sensors = data["source_product"].map({
        "MODIS_SP": "MODIS",
        "VIIRS_NOAA20_SP": "VIIRS",
        "VIIRS_SNPP_SP": "VIIRS",
    })
    actual_sensors = data["sensor"].astype(str).str.strip().str.upper()
    mismatch = actual_sensors.ne(expected_sensors)
    if mismatch.any():
        raise ValueError(
            "Sensor/product mismatch:\n"
            f"{data.loc[mismatch, ['sensor', 'source_product']].head(10)}"
        )

    processing_types = set(
        data["processing_type"].dropna().astype(str).str.strip().str.upper()
    )
    if processing_types != {"SP"}:
        raise ValueError(
            f"Expected only SP processing type; found {sorted(processing_types)}"
        )

    optional_missing = data.isna().sum()
    optional_missing = optional_missing[optional_missing > 0]
    if not optional_missing.empty:
        print("\nOptional missing values (will be preserved as null):")
        print(optional_missing.to_string())

    return data


def convert_record(row):
    sensor = str(row["sensor"]).strip().upper()
    product = str(row["source_product"]).strip().upper()
    expected_sensor = {
        "MODIS_SP": "MODIS",
        "VIIRS_NOAA20_SP": "VIIRS",
        "VIIRS_SNPP_SP": "VIIRS",
    }.get(product)

    if expected_sensor is None or sensor != expected_sensor:
        raise ValueError(f"Unsupported or inconsistent sensor/product: {sensor}/{product}")

    timestamp = pd.to_datetime(row["timestamp_utc"], utc=True, errors="raise")
    if pd.isna(timestamp):
        raise ValueError(f"Invalid timestamp: {row['timestamp_utc']!r}")

    latitude = required_float(row["latitude"], "latitude")
    longitude = required_float(row["longitude"], "longitude")
    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitude out of range: {latitude}")
    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitude out of range: {longitude}")

    frp = optional_float(row["frp_mw"], "frp_mw")
    if frp is not None and frp < 0:
        raise ValueError(f"Negative FRP: {frp}")

    record = {
        "timestamp_utc": timestamp.to_pydatetime(),
        "latitude": latitude,
        "longitude": longitude,
        "sensor": sensor,
        "satellite_raw": optional_text(row["satellite_raw"]),
        "source_product": product,
        "processing_type": optional_text(row["processing_type"]),
        "source_file": optional_text(row["source_file"]),
        "source_record_id": optional_int(row["source_record_id"], "source_record_id"),
        "confidence_raw": optional_text(row["confidence_raw"]),
        "confidence_type": optional_text(row["confidence_type"]),
        "frp_mw": frp,
        "brightness_raw": optional_float(row["brightness_raw"], "brightness_raw"),
        "brightness_11um_raw": optional_float(
            row["brightness_11um_raw"], "brightness_11um_raw"
        ),
        "viirs_bright_ti4": optional_float(
            row["viirs_bright_ti4"], "viirs_bright_ti4"
        ),
        "viirs_bright_ti5": optional_float(
            row["viirs_bright_ti5"], "viirs_bright_ti5"
        ),
        "scan": optional_float(row["scan"], "scan"),
        "track": optional_float(row["track"], "track"),
        "daynight_raw": optional_text(row["daynight_raw"]),
        "source_type_raw": optional_text(row["source_type_raw"]),
        "product_version": optional_text(row["product_version"]),
    }
    return add_h3_indices(record)


def validate_h3_columns(indexed):
    for resolution in (5, 7, 8, 9):
        column = f"h3_res{resolution}"
        valid = indexed[column].map(
            lambda cell: (
                isinstance(cell, str)
                and h3.is_valid_cell(cell)
                and h3.get_resolution(cell) == resolution
            )
        )
        if not valid.all():
            raise RuntimeError(
                f"Invalid H3 identifiers in {column}: {(~valid).sum()}"
            )


def main():
    print("=" * 68)
    print("QORVEX — Global Test Analytical Dataset Builder")
    print("=" * 68)

    source = load_source_data()
    expected_records = len(source)

    print(f"\nSource records: {expected_records:,}")
    print("\nSource product counts:")
    print(source["source_product"].value_counts().to_string())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    indexed_path = OUTPUT_DIR / "spatially_indexed_detections.parquet"
    daily_path = OUTPUT_DIR / "daily_activity.parquet"
    indexed_tmp = OUTPUT_DIR / "spatially_indexed_detections.tmp.parquet"
    daily_tmp = OUTPUT_DIR / "daily_activity.tmp.parquet"

    existing = [path for path in (indexed_path, daily_path) if path.exists()]
    if existing:
        raise FileExistsError(
            "Existing final outputs will not be overwritten:\n"
            + "\n".join(str(path) for path in existing)
        )

    indexed_tmp.unlink(missing_ok=True)
    daily_tmp.unlink(missing_ok=True)

    try:
        total_indexed = 0
        batch = []

        print("\nBuilding spatially indexed detections...")
        with pq.ParquetWriter(
            indexed_tmp, INDEXED_SCHEMA, compression="zstd"
        ) as writer:
            for start in range(0, expected_records, BATCH_SIZE):
                chunk = source.iloc[start:start + BATCH_SIZE]
                for row in chunk.to_dict("records"):
                    batch.append(convert_record(row))
                    total_indexed += 1

                if batch:
                    writer.write_table(
                        pa.Table.from_pylist(batch, schema=INDEXED_SCHEMA)
                    )
                    batch.clear()

                print(
                    f"Processed {min(start + BATCH_SIZE, expected_records):,}"
                    f" / {expected_records:,}"
                )

        if total_indexed != expected_records:
            raise RuntimeError(
                f"Indexed count mismatch: {total_indexed:,} vs {expected_records:,}"
            )

        print("\nReading indexed Parquet for aggregation...")
        indexed = pd.read_parquet(indexed_tmp)
        validate_h3_columns(indexed)

        print("\nGenerating daily H3 resolution-7 activity...")
        daily = aggregate_daily_activity(indexed)

        if len(daily.columns) != 18:
            raise RuntimeError(f"Expected 18 daily columns; found {len(daily.columns)}")

        if daily.duplicated(["date_utc", "h3_res7"]).any():
            raise RuntimeError("Duplicate date_utc/h3_res7 groups found.")

        daily_total = int(daily["combined_detection_count"].sum())
        if daily_total != expected_records:
            raise RuntimeError(
                f"Daily counts do not reconcile: {daily_total:,} vs {expected_records:,}"
            )

        daily.to_parquet(
            daily_tmp, engine="pyarrow", compression="zstd", index=False
        )

        print("\nPerforming output validation...")
        indexed_check = pq.read_table(indexed_tmp)
        daily_check = pq.read_table(daily_tmp)

        if indexed_check.num_rows != expected_records:
            raise RuntimeError("Indexed Parquet row-count validation failed.")
        if not indexed_check.schema.equals(INDEXED_SCHEMA):
            raise RuntimeError("Indexed Parquet schema validation failed.")
        if daily_check.num_columns != 18 or daily_check.num_rows != len(daily):
            raise RuntimeError("Daily Parquet structure validation failed.")

        source_counts = source["source_product"].value_counts().sort_index()
        output_counts = (
            indexed["source_product"].value_counts().sort_index()
        )
        if not source_counts.equals(output_counts):
            raise RuntimeError("Per-product counts changed during indexing.")

        # Publish only after all validation checks have passed.
        indexed_tmp.replace(indexed_path)
        daily_tmp.replace(daily_path)

        print("\n" + "=" * 68)
        print("GLOBAL TEST DATASET BUILD COMPLETED")
        print("=" * 68)
        print(f"Indexed detections: {indexed_check.num_rows:,}")
        print(f"Daily activity rows: {daily_check.num_rows:,}")
        print(f"Indexed output: {indexed_path}")
        print(f"Daily output: {daily_path}")
        print(f"Date range: {daily['date_utc'].min()} to {daily['date_utc'].max()}")
        print("\nProduct counts:")
        print(output_counts.to_string())
        print("\nH3 cell counts:")
        for resolution in (5, 7, 8, 9):
            print(f"  Resolution {resolution}: {indexed[f'h3_res{resolution}'].nunique():,} unique cells")
        print("\nAll validation checks passed.")
        print(
            "\nInterpretation: daily *_frp_sum_mw fields are sums of recorded "
            "detection FRP measurements. They are not estimates of total "
            "fire energy or unique-fire energy."
        )

    finally:
        indexed_tmp.unlink(missing_ok=True)
        daily_tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
