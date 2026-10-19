
import csv
import io
import os
import time
import urllib.error
import urllib.request
from datetime import date, timedelta, datetime
from pathlib import Path
from urllib.parse import quote

from qorvex.harmonize_firms import harmonize_record


# Study configuration
AREA = "140.9,-39.2,150.1,-33.9"
START_DATE = date(2024, 1, 1)
END_DATE = date(2024, 12, 31)
CHUNK_DAYS = 5

PRODUCTS = [
    "MODIS_SP",
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
]

DATA_DIR = Path(
    os.getenv("QORVEX_DATA_DIR", "data")
).expanduser().resolve()

BASE_DIR = DATA_DIR / "firms_2024_raw"

OUTPUT_FILE = Path(
    os.getenv(
        "QORVEX_OUTPUT_FILE",
        str(DATA_DIR / "harmonized_fires_2024.csv"),
    )
).expanduser().resolve()

REQUIRED_COLUMNS = {
    "latitude", "longitude", "acq_date", "acq_time",
    "instrument", "satellite", "confidence", "frp",
    "version", "daynight", "type",
}


def validate_csv_header(content):
    """Validate that CSV content has the required FIRMS columns."""

    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        raise ValueError("Response has no CSV header")

    missing = REQUIRED_COLUMNS - set(reader.fieldnames)

    if missing:
        raise ValueError(
            f"Unexpected FIRMS response; missing columns: "
            f"{sorted(missing)}"
        )

    return reader.fieldnames


def fetch_chunk(source, start, day_range, map_key):
    """Fetch one historical chunk, retrying temporary failures."""

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{quote(map_key, safe='')}/{source}/{AREA}/"
        f"{day_range}/{start.isoformat()}"
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "QORVEX-NASA-Space-Apps"},
    )

    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                content = response.read().decode("utf-8-sig")

            validate_csv_header(content)
            return content

        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            if attempt == 3:
                raise RuntimeError(
                    f"{source}, {start}: failed after 3 attempts: {error}"
                ) from error

            wait_seconds = 2 ** attempt
            print(
                f"  Attempt {attempt} failed: {error}. "
                f"Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)


def main():
    map_key = os.getenv("FIRMS_MAP_KEY")

    if not map_key:
        raise RuntimeError(
            "FIRMS_MAP_KEY is not configured in this terminal."
        )

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    chunk_starts = []
    current = START_DATE

    while current <= END_DATE:
        chunk_starts.append(current)
        current += timedelta(days=CHUNK_DAYS)

    total_chunks = len(chunk_starts) * len(PRODUCTS)
    completed = 0

    print("QORVEX — Annual FIRMS collector")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Products: {len(PRODUCTS)}")
    print(f"Planned chunks: {total_chunks}")

    # Download each product in non-overlapping date chunks.
    for product in PRODUCTS:
        for chunk_start in chunk_starts:
            remaining_days = (END_DATE - chunk_start).days + 1
            day_range = min(CHUNK_DAYS, remaining_days)

            chunk_file = BASE_DIR / (
                f"{product}_{chunk_start.isoformat()}.csv"
            )

                        
            if chunk_file.exists():
                try:
                    content = chunk_file.read_text(encoding="utf-8-sig")
                    validate_csv_header(content)
                except (OSError, UnicodeError, ValueError) as error:
                    raise RuntimeError(
                        f"Existing checkpoint is invalid: "
                        f"{chunk_file.name}: {error}"
                    ) from error

                completed += 1
                print(
                    f"[{completed}/{total_chunks}] Reusing "
                    f"{chunk_file.name}"
                )
                continue


            print(
                f"[{completed + 1}/{total_chunks}] Downloading "
                f"{product}, {chunk_start}, {day_range} day(s)"
            )

            content = fetch_chunk(
                product, chunk_start, day_range, map_key
            )

            # Write atomically so an interrupted write isn't mistaken
            # for a completed checkpoint.
            temporary_file = chunk_file.with_suffix(".tmp")
            temporary_file.write_text(content, encoding="utf-8-sig")
            temporary_file.replace(chunk_file)

            completed += 1
            print(f"  Saved checkpoint: {chunk_file.name}")

    print("\nAll download chunks are present.")
    print("Harmonizing downloaded records...")

    fieldnames = [
        "timestamp_utc", "latitude", "longitude", "sensor",
        "satellite_raw", "source_product", "confidence_raw",
        "frp_mw", "brightness_raw", "brightness_11um_raw",
        "viirs_bright_ti4", "viirs_bright_ti5",
        "daynight_raw", "source_type_raw", "product_version",
    ]

    total_raw = 0
    total_harmonized = 0
    total_rejected = 0

    temporary_output = OUTPUT_FILE.with_suffix(".tmp")

    with temporary_output.open(
        "w", newline="", encoding="utf-8-sig"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for product in PRODUCTS:
            for chunk_start in chunk_starts:
                chunk_file = BASE_DIR / (
                    f"{product}_{chunk_start.isoformat()}.csv"
                )

                with chunk_file.open(
                    "r", newline="", encoding="utf-8-sig"
                ) as source_file:
                    reader = csv.DictReader(source_file)

                    for row in reader:
                        total_raw += 1

                        try:
                            record = harmonize_record(row, product)
                            record["timestamp_utc"] = (
                                record["timestamp_utc"].isoformat()
                            )
                            writer.writerow(record)
                            total_harmonized += 1

                        except (ValueError, KeyError) as error:
                            total_rejected += 1
                            print(
                                f"Rejected {product} record "
                                f"in {chunk_file.name}: {error}"
                            )

    temporary_output.replace(OUTPUT_FILE)

    print("\nCollection summary")
    print("-" * 50)
    print(f"Raw records read: {total_raw}")
    print(f"Harmonized records: {total_harmonized}")
    print(f"Rejected records: {total_rejected}")
    print(f"Output file: {OUTPUT_FILE.resolve()}")
    print(f"Raw checkpoints: {BASE_DIR.resolve()}")


if __name__ == "__main__":
    main()
