"""Discover full-swath fire-mask and geolocation granules through NASA CMR."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import re
from urllib.parse import urlparse

import pandas as pd
import requests

from pipeline.common import ROOT, load_regions


CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"
PRODUCT_VERSIONS = {"MYD14": "061", "MYD03": "061", "VNP14IMG": "002", "VNP03IMG": "002"}
ACQUISITION = re.compile(r"\.A(\d{7})\.(\d{4})\.")


def acquisition_key(identifier: str) -> str:
    match = ACQUISITION.search(identifier)
    if match is None:
        raise ValueError(f"Unrecognized NASA granule identifier: {identifier}")
    return f"{match.group(1)}.{match.group(2)}"


def data_url(entry: dict) -> str:
    urls = [link["href"] for link in entry.get("links", [])
            if link.get("rel", "").endswith("/data#")
            and link.get("href", "").startswith("https://")
            and Path(urlparse(link["href"]).path).suffix.lower() in {".hdf", ".nc"}]
    if len(urls) != 1:
        raise ValueError(f"Expected one HTTPS data URL for {entry.get('producer_granule_id')}")
    return urls[0]


def discover(day: date, bbox: tuple[float, float, float, float],
             session: requests.Session | None = None) -> pd.DataFrame:
    if not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
        raise ValueError("Expected a valid west,south,east,north bounding box")
    client = session or requests.Session()
    temporal = f"{day.isoformat()}T00:00:00Z,{(day + timedelta(days=1)).isoformat()}T00:00:00Z"
    rows = []
    for product, version in PRODUCT_VERSIONS.items():
        response = client.get(CMR_GRANULES, params={
            "short_name": product,
            "temporal": temporal,
            "bounding_box": ",".join(map(str, bbox)),
            "page_size": 200,
        }, timeout=30)
        response.raise_for_status()
        entries = response.json()["feed"]["entry"]
        if len(entries) >= 200:
            raise ValueError(f"CMR result page may be truncated for {product}")
        for entry in entries:
            granule = entry["producer_granule_id"]
            if f".{version}." not in granule:
                continue
            rows.append({
                "date": day.isoformat(),
                "product": product,
                "granule_id": granule,
                "acquisition_key": acquisition_key(granule),
                "time_start_utc": entry["time_start"],
                "time_end_utc": entry["time_end"],
                "day_night_flag": entry.get("day_night_flag", ""),
                "size_mb": float(entry.get("granule_size") or 0),
                "data_url": data_url(entry),
                "requires_earthdata_login": True,
            })
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("CMR returned no matching swath granules")
    for fire, geo in (("MYD14", "MYD03"), ("VNP14IMG", "VNP03IMG")):
        fire_keys = set(frame.loc[frame["product"] == fire, "acquisition_key"])
        geo_keys = set(frame.loc[frame["product"] == geo, "acquisition_key"])
        if fire_keys != geo_keys:
            raise ValueError(f"Fire/geolocation granule mismatch: {fire}, {geo}")
    return frame.sort_values(["product", "time_start_utc"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=date(2023, 8, 6))
    parser.add_argument("--region", default="western_iberia")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    region = next((region for region in load_regions() if region.id == args.region), None)
    if region is None:
        raise ValueError(f"Unknown region: {args.region}")
    output = args.output or ROOT / "outputs" / "tables" / f"day8_swath_inventory_{args.date.isoformat()}.csv"
    frame = discover(args.date, region.bbox)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(frame.groupby("product").size().to_string())
    print(f"Saved {len(frame)} CMR granule records to {output}; downloads require Earthdata Login")


if __name__ == "__main__":
    main()
