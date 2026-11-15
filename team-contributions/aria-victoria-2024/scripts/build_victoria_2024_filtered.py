
"""
Build geographically filtered Victoria 2024 QORVEX datasets.

Input:
    C:/Users/Asus/data/victoria_fires_2024.csv

Outputs:
    data/processed/victoria_2024_filtered/
        spatially_indexed_detections.parquet
        daily_activity.parquet

Important:
    - This script reads an already-harmonized and geographically
      filtered CSV. It does not harmonize the records again.
    - Sensor-specific missing thermal values are preserved as null.
    - Missing optional metadata is preserved as null.
    - Existing final output files are never overwritten.
"""

from pathlib import Path
import math

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from qorvex.spatial_index import add_h3_indices
from qorvex.daily_aggregation import aggregate_daily_activity


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SOURCE_FILE = Path(
    r"C:\Users\Asus\data\victoria_fires_2024.csv"
)

OUTPUT_DIR = Path("data/processed/victoria_2024_filtered")

EXPECTED_RECORDS = 57_305

EXPECTED_PRODUCTS = {
    "MODIS_SP",
    "VIIRS_NOAA20_SP",
    "VIIRS_SNPP_SP",
}

BATCH_SIZE = 10_000


# These columns must exist in the source CSV.
# Their values are not necessarily required in every record.
REQUIRED_SOURCE_COLUMNS = {
    "timestamp_utc",
    "latitude",
    "longitude",
    "sensor",
    "satellite_raw",
    "source_product",
    "confidence_raw",
    "frp_mw",
    "brightness_raw",
    "brightness_11um_raw",
    "viirs_bright_ti4",
    "viirs_bright_ti5",
    "daynight_raw",
    "source_type_raw",
    "product_version",
}


# Only these fields must contain values in every record.
MANDATORY_SOURCE_COLUMNS = [
    "timestamp_utc",
    "latitude",
    "longitude",
    "sensor",
    "source_product",
]


# ---------------------------------------------------------------------
# Analytical Parquet schema
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
# Value conversion helpers
# ---------------------------------------------------------------------

def optional_text(value):
    """Convert an optional text value, preserving missing values as None."""

    if pd.isna(value):
        return None

    return str(value).strip()


def optional_float(value, field_name):
    """
    Convert an optional numerical value to float.

    Missing values remain None.
    Non-numeric and non-finite values are rejected.
    """

    if pd.isna(value):
        return None

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid numerical value in '{field_name}': {value!r}"
        ) from exc

    if not math.isfinite(result):
        raise ValueError(
            f"Non-finite numerical value in '{field_name}': {value!r}"
        )

    return result


def required_float(value, field_name):
    """Convert a mandatory numerical value and reject invalid values."""

    result = optional_float(value, field_name)

    if result is None:
        raise ValueError(
            f"Mandatory numerical field '{field_name}' is missing."
        )

    return result


# ---------------------------------------------------------------------
# Source validation
# ---------------------------------------------------------------------

def load_source_data():
    """Load and validate the geographically filtered source CSV."""

    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(
            f"Victoria source file not found: {SOURCE_FILE}"
        )

    print(f"Loading source: {SOURCE_FILE}")

    data = pd.read_csv(SOURCE_FILE)

    # Validate the source CSV structure.
    missing_columns = REQUIRED_SOURCE_COLUMNS - set(data.columns)

    if missing_columns:
        raise ValueError(
            f"Source CSV is missing columns: "
            f"{sorted(missing_columns)}"
        )

    # Validate the expected number of records.
    if len(data) != EXPECTED_RECORDS:
        raise ValueError(
            f"Expected {EXPECTED_RECORDS:,} records, "
            f"found {len(data):,}."
        )

    # Validate only mandatory fields.
    missing_counts = data[MANDATORY_SOURCE_COLUMNS].isnull().sum()

    if missing_counts.any():
        raise ValueError(
            "Mandatory source fields contain missing values:\n"
            f"{missing_counts[missing_counts > 0]}"
        )

    # Validate product distribution.
    products = set(
        data["source_product"].astype(str).str.strip().str.upper().unique()
    )

    if products != EXPECTED_PRODUCTS:
        raise ValueError(
            f"Unexpected products: {sorted(products)}"
        )

    # Report optional missing values for transparency.
    optional_missing = data.isnull().sum()
    optional_missing = optional_missing[optional_missing > 0]

    if not optional_missing.empty:
        print("\nMissing values preserved as null:")
        print(optional_missing.to_string())

    print("\nSource validation passed.")

    return data


# ---------------------------------------------------------------------
# Record conversion
# ---------------------------------------------------------------------

def convert_record(row):
    """Convert an already-harmonized CSV row to analytical schema."""

    sensor = str(row["sensor"]).strip().upper()

    source_product = (
        str(row["source_product"]).strip().upper()
    )

    # Validate sensor.
    if sensor not in {"MODIS", "VIIRS"}:
        raise ValueError(
            f"Unsupported sensor: {sensor}"
        )

    # Validate product.
    if source_product not in EXPECTED_PRODUCTS:
        raise ValueError(
            f"Unsupported product: {source_product}"
        )

    # Validate sensor/product consistency.
    expected_sensor = (
        "MODIS"
        if source_product == "MODIS_SP"
        else "VIIRS"
    )

    if sensor != expected_sensor:
        raise ValueError(
            f"Sensor/product mismatch: "
            f"{sensor}, {source_product}"
        )

    # Convert and validate timestamp.
    timestamp = pd.to_datetime(
        row["timestamp_utc"],
        utc=True,
        errors="raise",
    )

    if pd.isna(timestamp):
        raise ValueError(
            f"Invalid timestamp: {row['timestamp_utc']!r}"
        )

    # Convert and validate coordinates.
    latitude = required_float(
        row["latitude"],
        "latitude",
    )

    longitude = required_float(
        row["longitude"],
        "longitude",
    )

    if not -90 <= latitude <= 90:
        raise ValueError(
            f"Invalid latitude: {latitude}"
        )

    if not -180 <= longitude <= 180:
        raise ValueError(
            f"Invalid longitude: {longitude}"
        )

    # Convert optional numerical measurements.
    frp = optional_float(
        row["frp_mw"],
        "frp_mw",
    )

    brightness = optional_float(
        row["brightness_raw"],
        "brightness_raw",
    )

    brightness_11um = optional_float(
        row["brightness_11um_raw"],
        "brightness_11um_raw",
    )

    viirs_bright_ti4 = optional_float(
        row["viirs_bright_ti4"],
        "viirs_bright_ti4",
    )

    viirs_bright_ti5 = optional_float(
        row["viirs_bright_ti5"],
        "viirs_bright_ti5",
    )

    # Validate FRP.
    if frp is not None and frp < 0:
        raise ValueError(
            f"Negative FRP: {frp}"
        )

    # Construct analytical record.
    record = {
        "timestamp_utc": timestamp.to_pydatetime(),
        "latitude": latitude,
        "longitude": longitude,

        "sensor": sensor,
        "satellite_raw": optional_text(row["satellite_raw"]),
        "source_product": source_product,

        # All three source products are standard SP products.
        "processing_type": "SP",

        # These fields are unavailable in the filtered CSV.
        # Do not fabricate their original values.
        "source_file": None,
        "source_record_id": None,

        "confidence_raw": optional_text(row["confidence_raw"]),

        "confidence_type": (
            "numeric_0_100"
            if sensor == "MODIS"
            else "categorical"
        ),

        "frp_mw": frp,

        # MODIS thermal measurements.
        "brightness_raw": brightness,
        "brightness_11um_raw": brightness_11um,

        # VIIRS thermal measurements.
        "viirs_bright_ti4": viirs_bright_ti4,
        "viirs_bright_ti5": viirs_bright_ti5,

        # These fields are unavailable in the filtered CSV.
        "scan": None,
        "track": None,

        "daynight_raw": optional_text(row["daynight_raw"]),
        "source_type_raw": optional_text(row["source_type_raw"]),
        "product_version": optional_text(row["product_version"]),
    }

    # Add H3 spatial indices at resolutions 5, 7, 8 and 9.
    return add_h3_indices(record)


# ---------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------

def main():

    print("=" * 65)
    print("QORVEX — Victoria 2024 Filtered Analytical Dataset Builder")
    print("=" * 65)

    # Load and validate source data.
    data = load_source_data()

    print(f"\nSource records: {len(data):,}")

    print("\nSource product distribution:")
    print(
        data["source_product"]
        .value_counts()
        .to_string()
    )

    # Define output paths.
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    indexed_path = (
        OUTPUT_DIR / "spatially_indexed_detections.parquet"
    )

    daily_path = (
        OUTPUT_DIR / "daily_activity.parquet"
    )

    indexed_temp = (
        OUTPUT_DIR / "spatially_indexed_detections.tmp.parquet"
    )

    daily_temp = (
        OUTPUT_DIR / "daily_activity.tmp.parquet"
    )

    # Protect existing final outputs.
    existing_outputs = [
        path for path in [indexed_path, daily_path]
        if path.exists()
    ]

    if existing_outputs:
        raise FileExistsError(
            "The following final output files already exist. "
            "They will not be overwritten:\n"
            + "\n".join(str(path) for path in existing_outputs)
            + "\n\nPlease inspect or move these files before rerunning."
        )

    # Remove incomplete temporary files from a previous interrupted run.
    indexed_temp.unlink(missing_ok=True)
    daily_temp.unlink(missing_ok=True)

    total_indexed = 0
    batch = []

    try:

        # -------------------------------------------------------------
        # Build spatially indexed detection dataset.
        # -------------------------------------------------------------

        print("\nBuilding spatially indexed detections...")

        with pq.ParquetWriter(
            indexed_temp,
            INDEXED_SCHEMA,
            compression="zstd",
        ) as writer:

            for start in range(0, len(data), BATCH_SIZE):

                chunk = data.iloc[
                    start:start + BATCH_SIZE
                ]

                for row in chunk.to_dict("records"):

                    record = convert_record(row)

                    batch.append(record)
                    total_indexed += 1

                if batch:

                    table = pa.Table.from_pylist(
                        batch,
                        schema=INDEXED_SCHEMA,
                    )

                    writer.write_table(table)

                    batch.clear()

                print(
                    f"Processed "
                    f"{min(start + BATCH_SIZE, len(data)):,}"
                    f" / {len(data):,} records"
                )

        if total_indexed != EXPECTED_RECORDS:
            raise RuntimeError(
                f"Expected {EXPECTED_RECORDS:,} indexed records, "
                f"found {total_indexed:,}."
            )

        # -------------------------------------------------------------
        # Build daily activity dataset.
        # -------------------------------------------------------------

        print("\nGenerating daily activity...")

        indexed_data = pd.read_parquet(indexed_temp)

        daily_data = aggregate_daily_activity(
            indexed_data
        )

        # Validate daily schema.
        if len(daily_data.columns) != 18:
            raise RuntimeError(
                "Daily activity dataset does not have 18 columns. "
                f"Found {len(daily_data.columns)}."
            )

        # Validate detection-count reconciliation.
        daily_total = int(
            daily_data["combined_detection_count"].sum()
        )

        if daily_total != total_indexed:
            raise RuntimeError(
                "Daily detection counts do not reconcile. "
                f"Expected {total_indexed:,}, found {daily_total:,}."
            )

        # Validate uniqueness of daily spatial groups.
        if daily_data.duplicated(
            ["date_utc", "h3_res7"]
        ).any():

            raise RuntimeError(
                "Duplicate date/H3 cell groups found."
            )

        # Write daily dataset to temporary file.
        daily_data.to_parquet(
            daily_temp,
            engine="pyarrow",
            compression="zstd",
            index=False,
        )

        # -------------------------------------------------------------
        # Independent output validation.
        # -------------------------------------------------------------

        print("\nValidating generated Parquet files...")

        indexed_check = pq.read_table(
            indexed_temp
        )

        daily_check = pq.read_table(
            daily_temp
        )

        if indexed_check.num_rows != EXPECTED_RECORDS:
            raise RuntimeError(
                "Indexed Parquet row-count validation failed."
            )

        if indexed_check.num_columns != len(INDEXED_SCHEMA):
            raise RuntimeError(
                "Indexed Parquet column-count validation failed."
            )

        if not indexed_check.schema.equals(INDEXED_SCHEMA):
            raise RuntimeError(
                "Indexed Parquet schema validation failed."
            )

        if daily_check.num_columns != 18:
            raise RuntimeError(
                "Daily Parquet schema validation failed."
            )

        if daily_check.num_rows != len(daily_data):
            raise RuntimeError(
                "Daily Parquet row-count validation failed."
            )

        # -------------------------------------------------------------
        # Publish validated outputs.
        # -------------------------------------------------------------

        indexed_temp.replace(indexed_path)
        daily_temp.replace(daily_path)

        # -------------------------------------------------------------
        # Completion report.
        # -------------------------------------------------------------

        print("\n" + "=" * 65)
        print("VICTORIA FILTERED DATASET BUILD COMPLETED")
        print("=" * 65)

        print(
            f"Indexed detections: {indexed_check.num_rows:,}"
        )

        print(
            f"Daily activity rows: {daily_check.num_rows:,}"
        )

        print(
            f"Indexed dataset: {indexed_path}"
        )

        print(
            f"Daily dataset: {daily_path}"
        )

        print("\nDaily activity date range:")

        print(
            f"{daily_data['date_utc'].min()} "
            f"to {daily_data['date_utc'].max()}"
        )

        print("\nAll validation checks passed.")

    finally:

        # Remove temporary files.
        indexed_temp.unlink(missing_ok=True)
        daily_temp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
