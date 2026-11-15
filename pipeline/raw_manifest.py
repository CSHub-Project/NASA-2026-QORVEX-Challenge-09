"""Record hashes of the exact FIRMS downloads without publishing the MAP key."""

from __future__ import annotations

import csv
import hashlib
import argparse
from pathlib import Path

from pipeline.common import DATA_RAW, ROOT, load_regions
from pipeline.fetch_firms import SOURCES, iter_chunks


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(
    years: list[int],
    region_ids: set[str] | None = None,
    output: Path | None = None,
    regions_file: Path | None = None,
) -> int:
    rows = []
    regions = load_regions(regions_file)
    if region_ids is not None:
        regions = [region for region in regions if region.id in region_ids]
        unknown = region_ids - {region.id for region in regions}
        if unknown:
            raise ValueError(f"Unknown region ids: {sorted(unknown)}")
    for year in years:
        for region in regions:
            for source in SOURCES:
                for start, days in iter_chunks(year):
                    filename = f"{start.isoformat()}_{days}d.csv"
                    path = DATA_RAW / str(year) / region.id / source / filename
                    if not path.is_file() or path.stat().st_size == 0:
                        raise FileNotFoundError(f"Incomplete FIRMS partition: {path.relative_to(ROOT)}")
                    rows.append({
                        "year": year,
                        "region_id": region.id,
                        "source": source,
                        "partition": filename,
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    })
    if output is None:
        output = ROOT / "outputs" / "tables" / "firms_raw_manifest_2017_2020.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--region", action="append")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--regions-file", type=Path)
    args = parser.parse_args()
    count = build(
        args.year or [2017, 2018, 2019, 2020],
        set(args.region) if args.region else None,
        args.output,
        args.regions_file,
    )
    print(f"FIRMS raw manifest recorded {count} partitions")
