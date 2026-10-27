
"""Configurable NASA FIRMS collector for QORVEX.

Defaults preserve the original Victoria 2024 collection settings.

Environment variables:
    QORVEX_DATA_DIR
    QORVEX_AREA              Bounding box or "world"
    QORVEX_START_DATE        YYYY-MM-DD
    QORVEX_END_DATE          YYYY-MM-DD
    QORVEX_PRODUCTS          Comma-separated FIRMS product IDs
    QORVEX_OUTPUT_FILE       Optional explicit output path
    QORVEX_CHUNK_DAYS        1 to 5

FIRMS_MAP_KEY must be configured locally and must never be committed.
"""

import csv
import hashlib
import io
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from qorvex.harmonize_firms import harmonize_record


DEFAULT_AREA = "140.9,-39.2,150.1,-33.9"
DEFAULT_START_DATE = date(2024, 1, 1)
DEFAULT_END_DATE = date(2024, 12, 31)
DEFAULT_PRODUCTS = (
    "MODIS_SP",
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
)
MAX_CHUNK_DAYS = 5

REQUIRED_COLUMNS = {
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "instrument",
    "satellite",
    "confidence",
    "frp",
    "version",
    "daynight",
    "type",
}

OUTPUT_COLUMNS = [
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
]

VALID_PRODUCTS = set(DEFAULT_PRODUCTS)


def validate_area(area: str) -> str:
    """Validate and normalize 'world' or a west,south,east,north bounding box."""
    area = area.strip()

    if area.lower() == "world":
        return "world"

    parts = [part.strip() for part in area.split(",")]

    if len(parts) != 4:
        raise ValueError(
            'QORVEX_AREA must be "world" or west,south,east,north.'
        )

    try:
        west, south, east, north = map(float, parts)
    except ValueError:
        raise ValueError(
            "QORVEX_AREA must contain four numeric coordinates."
        ) from None

    if not all(math.isfinite(value) for value in (west, south, east, north)):
        raise ValueError("QORVEX_AREA coordinates must be finite numbers.")

    if not (-180 <= west <= 180 and -180 <= east <= 180):
        raise ValueError("Bounding-box longitudes must be between -180 and 180.")

    if not (-90 <= south <= 90 and -90 <= north <= 90):
        raise ValueError("Bounding-box latitudes must be between -90 and 90.")

    if west >= east:
        raise ValueError(
            "The bounding box must have west < east. "
            "Antimeridian-crossing boxes are not supported."
        )

    if south >= north:
        raise ValueError("The bounding box must have south < north.")

    # Normalize equivalent inputs so they use the same checkpoint identity.
    return ",".join(format(value, ".15g") for value in (west, south, east, north))


def load_configuration() -> dict:
    """Load and validate collection settings and derive safe paths."""
    data_dir = Path(
        os.getenv("QORVEX_DATA_DIR", "data")
    ).expanduser().resolve()

    area = validate_area(os.getenv("QORVEX_AREA", DEFAULT_AREA))

    try:
        start_date = date.fromisoformat(
            os.getenv("QORVEX_START_DATE", DEFAULT_START_DATE.isoformat())
        )
        end_date = date.fromisoformat(
            os.getenv("QORVEX_END_DATE", DEFAULT_END_DATE.isoformat())
        )
    except ValueError as error:
        raise ValueError(
            "QORVEX_START_DATE and QORVEX_END_DATE must use YYYY-MM-DD."
        ) from error

    if end_date < start_date:
        raise ValueError(
            "QORVEX_END_DATE must be on or after QORVEX_START_DATE."
        )

    products_text = os.getenv(
        "QORVEX_PRODUCTS", ",".join(DEFAULT_PRODUCTS)
    )
    products = tuple(
        product.strip().upper()
        for product in products_text.split(",")
        if product.strip()
    )

    if not products:
        raise ValueError("At least one FIRMS product must be configured.")

    unsupported = set(products) - VALID_PRODUCTS
    if unsupported:
        raise ValueError(
            f"Unsupported FIRMS products: {sorted(unsupported)}. "
            f"Currently supported products: {sorted(VALID_PRODUCTS)}"
        )

    if len(set(products)) != len(products):
        raise ValueError("QORVEX_PRODUCTS contains duplicate products.")

    try:
        chunk_days = int(
            os.getenv("QORVEX_CHUNK_DAYS", str(MAX_CHUNK_DAYS))
        )
    except ValueError:
        raise ValueError("QORVEX_CHUNK_DAYS must be an integer from 1 to 5.") from None

    if not 1 <= chunk_days <= MAX_CHUNK_DAYS:
        raise ValueError(
            f"QORVEX_CHUNK_DAYS must be between 1 and {MAX_CHUNK_DAYS}."
        )

    # Date ranges are intentionally excluded from the checkpoint identity.
    # This lets later runs reuse completed chunks when the period is extended.
    checkpoint_identity = {
        "area": area,
        "products": list(products),
        "chunk_days": chunk_days,
    }
    fingerprint = hashlib.sha256(
        json.dumps(checkpoint_identity, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]

    is_original_default = (
        area == DEFAULT_AREA
        and start_date == DEFAULT_START_DATE
        and end_date == DEFAULT_END_DATE
        and products == DEFAULT_PRODUCTS
        and chunk_days == MAX_CHUNK_DAYS
    )

    if is_original_default:
        # Preserve compatibility with the original Victoria 2024 workflow.
        default_filename = "harmonized_fires_2024.csv"
    else:
        # Keep different configurations from silently overwriting each other.
        default_filename = (
            f"harmonized_fires_{start_date.isoformat()}_"
            f"{end_date.isoformat()}_{fingerprint}.csv"
        )

    default_output = data_dir / default_filename
    output_file = Path(
        os.getenv("QORVEX_OUTPUT_FILE", str(default_output))
    ).expanduser().resolve()

    return {
        "area": area,
        "start_date": start_date,
        "end_date": end_date,
        "products": products,
        "chunk_days": chunk_days,
        "data_dir": data_dir,
        "output_file": output_file,
        "checkpoint_dir": data_dir / "firms_checkpoints" / fingerprint,
        "fingerprint": fingerprint,
    }


def validate_csv_header(content: str) -> list[str]:
    """Validate a FIRMS CSV response, including valid empty responses."""
    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        raise ValueError("Response has no CSV header.")

    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValueError(
            "Unexpected FIRMS response; missing columns: "
            f"{sorted(missing)}"
        )

    return reader.fieldnames


def fetch_chunk(
    source: str,
    start: date,
    day_range: int,
    map_key: str,
    area: str,
) -> str:
    """Fetch one historical chunk, retrying temporary failures."""
    if not 1 <= day_range <= MAX_CHUNK_DAYS:
        raise ValueError(
            f"FIRMS request length must be between 1 and {MAX_CHUNK_DAYS} days."
        )

    area = validate_area(area)

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{quote(map_key, safe='')}/{source}/{quote(area, safe=',')}/"
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

        except urllib.error.HTTPError as error:
            if error.code in {400, 401, 403, 404}:
                raise RuntimeError(
                    f"FIRMS rejected {source} request starting {start}: "
                    f"HTTP {error.code}. Check the API key, product, "
                    "area, and request parameters."
                ) from error

            if attempt == 3:
                raise RuntimeError(
                    f"{source}, {start}: failed after 3 attempts: {error}"
                ) from error

        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            if attempt == 3:
                raise RuntimeError(
                    f"{source}, {start}: failed after 3 attempts: {error}"
                ) from error

        wait_seconds = 2 ** attempt
        print(f"  Attempt {attempt} failed; retrying in {wait_seconds}s...")
        time.sleep(wait_seconds)

    raise RuntimeError(f"Unexpected retry failure for {source}, {start}.")


def build_chunk_starts(
    start_date: date,
    end_date: date,
    chunk_days: int,
) -> list[date]:
    """Return the start date for each non-overlapping collection chunk."""
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date.")

    if not 1 <= chunk_days <= MAX_CHUNK_DAYS:
        raise ValueError(
            f"chunk_days must be between 1 and {MAX_CHUNK_DAYS}."
        )

    starts = []
    current = start_date

    while current <= end_date:
        starts.append(current)
        current += timedelta(days=chunk_days)

    return starts


def checkpoint_is_valid(path: Path) -> bool:
    """Return whether a checkpoint has a valid FIRMS CSV header."""
    try:
        validate_csv_header(path.read_text(encoding="utf-8-sig"))
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def write_checkpoint(path: Path, content: str) -> None:
    """Write a checkpoint atomically."""
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(content, encoding="utf-8-sig")
    temporary_path.replace(path)


def main() -> None:
    map_key = os.getenv("FIRMS_MAP_KEY")
    if not map_key:
        raise RuntimeError(
            "FIRMS_MAP_KEY is not configured in this terminal. "
            "Set it locally; never place the key in source code."
        )

    config = load_configuration()
    config["checkpoint_dir"].mkdir(parents=True, exist_ok=True)
    config["output_file"].parent.mkdir(parents=True, exist_ok=True)

    chunk_starts = build_chunk_starts(
        config["start_date"],
        config["end_date"],
        config["chunk_days"],
    )

    total_chunks = len(chunk_starts) * len(config["products"])
    completed = 0

    print("QORVEX — Configurable FIRMS collector")
    print(f"Area: {config['area']}")
    print(f"Period: {config['start_date']} to {config['end_date']}")
    print(f"Products: {', '.join(config['products'])}")
    print(f"Chunk size: {config['chunk_days']} day(s)")
    print(f"Planned chunks: {total_chunks}")
    print(f"Configuration ID: {config['fingerprint']}")
    print(f"Checkpoint directory: {config['checkpoint_dir']}")
    print(f"Output file: {config['output_file']}")

    for product in config["products"]:
        for chunk_start in chunk_starts:
            remaining_days = (
                config["end_date"] - chunk_start
            ).days + 1
            day_range = min(config["chunk_days"], remaining_days)

            chunk_file = config["checkpoint_dir"] / (
                f"{product}_{chunk_start.isoformat()}_{day_range}d.csv"
            )

            if chunk_file.exists():
                if checkpoint_is_valid(chunk_file):
                    completed += 1
                    print(
                        f"[{completed}/{total_chunks}] Reusing "
                        f"{chunk_file.name}"
                    )
                    continue

                raise RuntimeError(
                    f"Existing checkpoint is invalid: {chunk_file}. "
                    "Inspect or remove it before retrying."
                )

            print(
                f"[{completed + 1}/{total_chunks}] Downloading "
                f"{product}, {chunk_start}, {day_range} day(s)"
            )

            content = fetch_chunk(
                product,
                chunk_start,
                day_range,
                map_key,
                config["area"],
            )
            write_checkpoint(chunk_file, content)

            completed += 1
            print(f"  Saved checkpoint: {chunk_file.name}")

    print("\nAll download chunks are present.")
    print("Harmonizing downloaded records...")

    total_raw = 0
    total_harmonized = 0
    total_rejected = 0
    temporary_output = config["output_file"].with_suffix(".tmp")

    with temporary_output.open(
        "w", newline="", encoding="utf-8-sig"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for product in config["products"]:
            for chunk_start in chunk_starts:
                remaining_days = (
                    config["end_date"] - chunk_start
                ).days + 1
                day_range = min(config["chunk_days"], remaining_days)

                chunk_file = config["checkpoint_dir"] / (
                    f"{product}_{chunk_start.isoformat()}_{day_range}d.csv"
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
                                record["timestamp_utc"]
                                .astimezone(timezone.utc)
                                .isoformat()
                            )
                            writer.writerow(record)
                            total_harmonized += 1

                        except (ValueError, KeyError) as error:
                            total_rejected += 1
                            print(
                                f"Rejected {product} record "
                                f"in {chunk_file.name}: {error}"
                            )

    temporary_output.replace(config["output_file"])

    print("\nCollection summary")
    print("-" * 50)
    print(f"Raw records read: {total_raw:,}")
    print(f"Harmonized records: {total_harmonized:,}")
    print(f"Rejected records: {total_rejected:,}")
    print(f"Output file: {config['output_file']}")
    print(f"Raw checkpoints: {config['checkpoint_dir']}")


if __name__ == "__main__":
    main()
