from __future__ import annotations

import argparse
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

from pipeline.common import DATA_RAW, ensure_directories, load_regions


BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
STATUS_URL = "https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/"
SOURCES = ("MODIS_SP", "VIIRS_SNPP_SP")
AVAILABLE_SOURCES = SOURCES + ("VIIRS_NOAA20_SP",)
CHUNK_DAYS = 5
MAX_ATTEMPTS = 8
REQUEST_DELAY_SECONDS = 0.2
BUDGET_HEADROOM = 250


def iter_chunks(year: int):
    cursor = date(year, 1, 1)
    stop = date(year + 1, 1, 1)
    while cursor < stop:
        days = min(CHUNK_DAYS, (stop - cursor).days)
        yield cursor, days
        cursor += timedelta(days=days)


def get_transaction_status(client: httpx.Client, map_key: str) -> tuple[int, int] | None:
    try:
        response = client.get(STATUS_URL, params={"MAP_KEY": map_key})
        if response.status_code != 200:
            return None
        payload = response.json()
        return int(payload["current_transactions"]), int(payload["transaction_limit"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None


def download_chunk(
    client: httpx.Client,
    map_key: str,
    source: str,
    bbox: str,
    start: date,
    days: int,
    output: Path,
) -> None:
    if output.exists() and output.stat().st_size > 0:
        return
    url = f"{BASE_URL}/{map_key}/{source}/{bbox}/{days}/{start.isoformat()}"
    response = None
    last_status: int | None = None
    last_message = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.get(url)
            response.raise_for_status()
            break
        except httpx.HTTPStatusError as error:
            last_status = error.response.status_code
            last_message = error.response.text[:200].replace(map_key, "[REDACTED]")
            response = None
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            last_message = type(error).__name__
            response = None
        if response is None:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"FIRMS request failed after {MAX_ATTEMPTS} attempts "
                    f"(status={last_status}, source={source}, start={start}): {last_message}"
                ) from None
            delay = min(30.0, 2 ** (attempt - 1)) + random.uniform(0.0, 0.5)
            print(
                f"retry {attempt}/{MAX_ATTEMPTS} {source} {start} after {delay:.1f}s",
                flush=True,
            )
            time.sleep(delay)
    assert response is not None
    if response.text.lstrip().lower().startswith(("invalid", "error")):
        raise RuntimeError(f"FIRMS rejected {source} request for {start}: {response.text[:200]}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--region", action="append", help="Region id; repeat to select several")
    parser.add_argument("--regions-file", type=Path, help="Alternative versioned region JSON")
    parser.add_argument(
        "--source",
        action="append",
        choices=AVAILABLE_SOURCES,
        help="FIRMS product to fetch; repeat for several. Defaults to the model's two sensors.",
    )
    args = parser.parse_args()

    load_dotenv()
    map_key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not map_key:
        raise SystemExit("FIRMS_MAP_KEY is missing. Copy .env.example to .env and add the key.")

    ensure_directories()
    regions = load_regions(args.regions_file)
    if args.region:
        selected = set(args.region)
        regions = [region for region in regions if region.id in selected]
        unknown = selected - {region.id for region in regions}
        if unknown:
            raise SystemExit(f"Unknown region ids: {sorted(unknown)}")

    timeout = httpx.Timeout(connect=20.0, read=180.0, write=60.0, pool=60.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        new_requests = 0
        selected_sources = tuple(args.source) if args.source else SOURCES
        for region in regions:
            for source in selected_sources:
                for start, days in iter_chunks(args.year):
                    filename = f"{start.isoformat()}_{days}d.csv"
                    output = DATA_RAW / str(args.year) / region.id / source / filename
                    if output.exists() and output.stat().st_size > 0:
                        print(
                            f"ready {region.id:18} {source:14} {start} {days}d",
                            flush=True,
                        )
                        continue
                    if new_requests % 10 == 0:
                        status = get_transaction_status(client, map_key)
                        if status is not None:
                            current, limit = status
                            if current >= limit - BUDGET_HEADROOM:
                                raise SystemExit(
                                    "FIRMS transaction budget is near its 10-minute limit; "
                                    "rerun later to resume safely."
                                )
                    download_chunk(
                        client, map_key, source, region.firms_bbox, start, days, output
                    )
                    new_requests += 1
                    print(f"ready {region.id:18} {source:14} {start} {days}d", flush=True)
                    time.sleep(REQUEST_DELAY_SECONDS)


if __name__ == "__main__":
    main()

