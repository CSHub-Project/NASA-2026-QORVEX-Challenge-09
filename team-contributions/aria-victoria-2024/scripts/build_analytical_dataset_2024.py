
"""Build QORVEX analytical datasets from the Victoria 2024 FIRMS archive."""

import csv
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from qorvex.harmonize_firms import harmonize_record
from qorvex.spatial_index import add_h3_indices
from qorvex.daily_aggregation import aggregate_daily_activity


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SOURCE_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")

OUTPUT_DIR = Path("data/processed/victoria_2024")

BATCH_SIZE = 10_000

EXPECTED_PRODUCTS = {
    "MODIS_SP",
    "VIIRS_NOAA20_SP",
    "VIIRS_SNPP_SP",
}

EXPECTED_FILES_PER_PRODUCT = 74
EXPECTED_TOTAL_RECORDS = 91_265

FILENAME_PATTERN = re.compile(
    r"^(MODIS_SP|VIIRS_NOAA20_SP|VIIRS_SNPP_SP)_(\d{4}-\d{2}-\d{2})\.csv$"
)


COMMON_SOURCE_COLUMNS = {
    "latitude",
    "longitude",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "daynight",
    "frp",
    "type",
}

PRODUCT_SOURCE_COLUMNS = {
    "MODIS_SP": {
        "brightness",
        "bright_t31",
    },
    "VIIRS_NOAA20_SP": {
        "bright_ti4",
        "bright_ti5",
    },
    "VIIRS_SNPP_SP": {
        "bright_ti4",
        "bright_ti5",
    },
}


# ---------------------------------------------------------------------
# Parquet schema
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# Source validation
# ---------------------------------------------------------------------

def discover_source_files():
    """Discover and validate the expected 2024 source archive."""

    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(
            f"Source directory does not exist: {SOURCE_DIR}"
        )

    csv_files = sorted(SOURCE_DIR.glob("*.csv"))

    if not csv_files:
        raise ValueError("No CSV files found in the source directory.")

    product_counts = Counter()
    validated_files = []

    for path in csv_files:
        match = FILENAME_PATTERN.fullmatch(path.name)

        if not match:
            raise ValueError(
                f"Unexpected source filename: {path.name}"
            )

        product, file_date = match.groups()

        # Validate the date encoded in the filename.
        pd.Timestamp(file_date)

        product_counts[product] += 1
        validated_files.append((path, product))

    if set(product_counts) != EXPECTED_PRODUCTS:
        raise ValueError(
            f"Unexpected source products: {sorted(product_counts)}"
        )

    for product in sorted(EXPECTED_PRODUCTS):
        count = product_counts[product]

        if count != EXPECTED_FILES_PER_PRODUCT:
            raise ValueError(
                f"{product}: expected {EXPECTED_FILES_PER_PRODUCT} files, "
                f"found {count}."
            )

    if len(validated_files) != 222:
        raise ValueError(
            f"Expected 222 source files, found {len(validated_files)}."
        )

    return validated_files



def validate_source_header(reader, path, product):
    """Validate common and product-specific FIRMS CSV columns."""

    if not reader.fieldnames:
        raise ValueError(f"Missing CSV header: {path.name}")

    required_columns = (
        COMMON_SOURCE_COLUMNS | PRODUCT_SOURCE_COLUMNS[product]
    )

    missing = required_columns - set(reader.fieldnames)

    if missing:
        raise ValueError(
            f"{path.name}: missing columns {sorted(missing)}"
        )


# ---------------------------------------------------------------------
# Record conversion
# ---------------------------------------------------------------------

def convert_record(row, product, source_file, row_number):
    """Harmonize one source row and add H3 spatial identifiers."""

    processing_type = product.rsplit("_", 1)[-1]

    record = harmonize_record(
        row,
        source_product=product,
        processing_type=processing_type,
        source_file=source_file,
        source_record_id=row_number,
    )

    record = add_h3_indices(record)

    # Keep raw categorical/source values as strings in the Parquet schema.
    for column in (
        "satellite_raw",
        "confidence_raw",
        "daynight_raw",
        "source_type_raw",
        "product_version",
    ):
        value = record[column]
        record[column] = None if value is None else str(value)

    return record


# ---------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------

def main():
    print("=" * 65)
    print("QORVEX — Victoria 2024 Analytical Dataset Builder")
    print("=" * 65)

    files = discover_source_files()

    print(f"Source directory: {SOURCE_DIR}")
    print(f"Validated source files: {len(files)}")
    print(f"Batch size: {BATCH_SIZE:,}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    indexed_path = OUTPUT_DIR / "spatially_indexed_detections.parquet"
    daily_path = OUTPUT_DIR / "daily_activity.parquet"

    indexed_temp = OUTPUT_DIR / "spatially_indexed_detections.tmp.parquet"
    daily_temp = OUTPUT_DIR / "daily_activity.tmp.parquet"

    total_raw = 0
    total_indexed = 0
    total_rejected = 0

    product_record_counts = Counter()
    rejection_examples = []
    batch = []

    # Remove abandoned temporary outputs from previous interrupted runs.
    indexed_temp.unlink(missing_ok=True)
    daily_temp.unlink(missing_ok=True)

    try:
        with pq.ParquetWriter(
            indexed_temp,
            INDEXED_SCHEMA,
            compression="zstd",
        ) as writer:

            for file_number, (path, product) in enumerate(files, start=1):
                print(
                    f"[{file_number}/222] Processing "
                    f"{product}: {path.name}"
                )

                with path.open(
                    "r",
                    newline="",
                    encoding="utf-8-sig",
                ) as source:
                    reader = csv.DictReader(source)
                    validate_source_header(reader, path, product)

                    for row_number, row in enumerate(reader, start=2):
                        total_raw += 1

                        try:
                            record = convert_record(
                                row,
                                product,
                                path.name,
                                row_number,
                            )

                            batch.append(record)
                            total_indexed += 1
                            product_record_counts[product] += 1

                        except (ValueError, KeyError, TypeError) as error:
                            total_rejected += 1

                            if len(rejection_examples) < 10:
                                rejection_examples.append(
                                    f"{path.name}, row {row_number}: {error}"
                                )

                        if len(batch) >= BATCH_SIZE:
                            table = pa.Table.from_pylist(
                                batch,
                                schema=INDEXED_SCHEMA,
                            )
                            writer.write_table(table)
                            batch.clear()

            if batch:
                table = pa.Table.from_pylist(
                    batch,
                    schema=INDEXED_SCHEMA,
                )
                writer.write_table(table)
                batch.clear()

        print("\nIngestion summary")
        print("-" * 65)
        print(f"Raw records read: {total_raw:,}")
        print(f"Spatially indexed records: {total_indexed:,}")
        print(f"Rejected records: {total_rejected:,}")

        for product in sorted(EXPECTED_PRODUCTS):
            print(
                f"{product}: "
                f"{product_record_counts[product]:,}"
            )

        if rejection_examples:
            print("\nRejection examples:")
            for example in rejection_examples:
                print(f"  {example}")

        # Never publish incomplete or rejected datasets.
        if total_rejected != 0:
            raise RuntimeError(
                f"Processing produced {total_rejected} rejected records. "
                "Inspect the rejection examples before proceeding."
            )

        if total_raw != EXPECTED_TOTAL_RECORDS:
            raise RuntimeError(
                f"Expected {EXPECTED_TOTAL_RECORDS:,} source records, "
                f"found {total_raw:,}."
            )

        if total_indexed != EXPECTED_TOTAL_RECORDS:
            raise RuntimeError(
                "The indexed record count does not match the expected "
                "source record count."
            )

        print("\nGenerating daily activity dataset...")

        indexed_data = pd.read_parquet(indexed_temp)

        daily_data = aggregate_daily_activity(indexed_data)

        if len(daily_data.columns) != 18:
            raise RuntimeError(
                "Daily activity dataset does not have 18 columns."
            )

        if int(daily_data["combined_detection_count"].sum()) != total_indexed:
            raise RuntimeError(
                "Daily aggregation detection counts do not match "
                "the indexed record count."
            )

        if daily_data.duplicated(["date_utc", "h3_res7"]).any():
            raise RuntimeError(
                "Duplicate date/H3 cell groups found in daily activity."
            )

        daily_data.to_parquet(
            daily_temp,
            engine="pyarrow",
            compression="zstd",
            index=False,
        )

        # Validate the written Parquet files before publishing.
        indexed_check = pq.read_table(indexed_temp)
        daily_check = pq.read_table(daily_temp)

        if indexed_check.num_rows != EXPECTED_TOTAL_RECORDS:
            raise RuntimeError("Indexed Parquet row-count validation failed.")

        if daily_check.num_columns != 18:
            raise RuntimeError("Daily Parquet schema validation failed.")

        # Publish the completed outputs.
        indexed_temp.replace(indexed_path)
        daily_temp.replace(daily_path)

        print("\n" + "=" * 65)
        print("ANALYTICAL DATASET BUILD COMPLETED")
        print("=" * 65)
        print(f"Indexed detections: {indexed_path}")
        print(f"Daily activity: {daily_path}")
        print(f"Indexed rows: {indexed_check.num_rows:,}")
        print(f"Daily activity rows: {daily_check.num_rows:,}")

        print("\nDaily activity date range:")
        print(
            f"{daily_data['date_utc'].min()} "
            f"to {daily_data['date_utc'].max()}"
        )

    finally:
        indexed_temp.unlink(missing_ok=True)
        daily_temp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
