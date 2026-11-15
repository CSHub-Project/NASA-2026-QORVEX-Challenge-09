"""Build the compact, validated Victoria 2024 FIRMS point archive for the web map."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "2024" / "southeast_australia"
OUTPUT = ROOT / "data" / "team" / "qorvex_victoria_2024" / "victoria_2024_bbox_points.parquet"
BBOX = (140.9, -39.2, 150.1, -33.9)
PRODUCTS = {
    "MODIS_SP": ("M", 10_582),
    "VIIRS_NOAA20_SP": ("N", 39_314),
    "VIIRS_SNPP_SP": ("S", 41_369),
}


def _source_id(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def build(output: Path = OUTPUT) -> Path:
    """Filter the frozen Southeast Australia archive to the reviewed study box."""
    west, south, east, north = BBOX
    frames: list[pd.DataFrame] = []
    for product, (code, expected) in PRODUCTS.items():
        paths = sorted((RAW_ROOT / product).glob("*.csv"))
        if len(paths) != 74:
            raise ValueError(f"{product}: expected 74 five-day FIRMS partitions, found {len(paths)}")
        product_frames: list[pd.DataFrame] = []
        for path in paths:
            frame = pd.read_csv(
                path,
                usecols=["latitude", "longitude", "acq_date", "acq_time", "daynight", "frp"],
                dtype={"acq_date": "string", "acq_time": "string", "daynight": "string"},
            )
            frame = frame[
                frame["latitude"].between(south, north)
                & frame["longitude"].between(west, east)
            ].copy()
            frame["source_partition"] = _source_id(path)
            product_frames.append(frame)
        product_frame = pd.concat([frame for frame in product_frames if not frame.empty], ignore_index=True)
        if len(product_frame) != expected:
            raise ValueError(f"{product}: expected {expected:,} records in the study box, found {len(product_frame):,}")
        product_frame["product"] = code
        frames.append(product_frame)

    points = pd.concat(frames, ignore_index=True)
    points["acq_time"] = points["acq_time"].str.replace(".0", "", regex=False).str.zfill(4)
    points["timestamp_utc"] = pd.to_datetime(
        points["acq_date"] + " " + points["acq_time"].str[:2] + ":" + points["acq_time"].str[2:],
        format="%Y-%m-%d %H:%M",
        utc=True,
        errors="raise",
    )
    if len(points) != 91_265 or points["timestamp_utc"].dt.year.unique().tolist() != [2024]:
        raise ValueError("Victoria point archive failed its frozen total/year check")
    if not points["daynight"].isin(["D", "N"]).all():
        raise ValueError("Unexpected day/night code in FIRMS archive")

    compact = pd.DataFrame({
        "date": points["timestamp_utc"].dt.strftime("%Y-%m-%d"),
        "minute_utc": points["timestamp_utc"].dt.hour * 60 + points["timestamp_utc"].dt.minute,
        "latitude": points["latitude"].round(5),
        "longitude": points["longitude"].round(5),
        "product": points["product"],
        "daynight": points["daynight"],
        "frp_mw": pd.to_numeric(points["frp"], errors="coerce").round(2),
        "source_partition": points["source_partition"],
    }).sort_values(["date", "minute_utc", "product", "latitude", "longitude"])
    output.parent.mkdir(parents=True, exist_ok=True)
    compact.to_parquet(output, index=False, compression="zstd")
    return output


if __name__ == "__main__":
    result = build()
    print(f"Built {result} ({len(pd.read_parquet(result)):,} records)")
