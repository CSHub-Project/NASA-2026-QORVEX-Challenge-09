"""Cross-check VIIRS L2 swath fire pixels against the FIRMS point export."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from scipy.optimize import linear_sum_assignment

from pipeline.common import ROOT, load_regions
from pipeline.day8_swath_mask import read_viirs_pair


def haversine_m(lat_a: np.ndarray, lon_a: np.ndarray,
                lat_b: np.ndarray, lon_b: np.ndarray) -> np.ndarray:
    a_lat, a_lon = np.deg2rad(lat_a)[:, None], np.deg2rad(lon_a)[:, None]
    b_lat, b_lon = np.deg2rad(lat_b)[None, :], np.deg2rad(lon_b)[None, :]
    delta_lat, delta_lon = b_lat - a_lat, b_lon - a_lon
    h = np.sin(delta_lat / 2) ** 2 + np.cos(a_lat) * np.cos(b_lat) * np.sin(delta_lon / 2) ** 2
    return 2 * 6_371_008.8 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def main() -> None:
    acquisition_key = "2023218.1330"
    region = next(r for r in load_regions() if r.id == "western_iberia")
    directory = ROOT / "data" / "raw" / "swaths" / acquisition_key
    fire = next(directory.glob("VNP14IMG.*.nc"))
    geo = next(directory.glob("VNP03IMG.*.nc"))
    mask, latitude, longitude = read_viirs_pair(fire, geo)
    west, south, east, north = region.bbox
    selected = (mask >= 7) & (mask <= 9) & (latitude >= south) & (latitude <= north) & (longitude >= west) & (longitude <= east)
    swath_lat, swath_lon = latitude[selected], longitude[selected]
    start = datetime(2023, 8, 6, 13, 30, tzinfo=timezone.utc)
    points = pl.read_parquet(ROOT / "data" / "processed" / "overlap_observations_2023.parquet")
    points = points.filter(
        (pl.col("region_id") == region.id)
        & (pl.col("source") == "VIIRS_SNPP_SP")
        & (pl.col("acquired_at_utc") >= start)
        & (pl.col("acquired_at_utc") < start + timedelta(minutes=6))
    )
    point_lat = points["latitude"].to_numpy()
    point_lon = points["longitude"].to_numpy()
    if len(swath_lat) != len(point_lat):
        raise ValueError(f"Different fire counts: L2={len(swath_lat)}, FIRMS={len(point_lat)}")
    distances = haversine_m(swath_lat, swath_lon, point_lat, point_lon)
    rows, cols = linear_sum_assignment(distances)
    result = pd.DataFrame({
        "acquisition_key": acquisition_key,
        "swath_latitude": swath_lat[rows], "swath_longitude": swath_lon[rows],
        "firms_latitude": point_lat[cols], "firms_longitude": point_lon[cols],
        "separation_m": distances[rows, cols],
    })
    if not (result["separation_m"] < 50).all():
        raise ValueError("L2 and FIRMS fire coordinates disagree by 50 m or more")
    target = ROOT / "outputs" / "tables" / "day8_viirs_firms_fire_crosscheck.csv"
    result.to_csv(target, index=False)
    print(f"Matched {len(result)} L2 fire pixels to FIRMS points; maximum separation {result['separation_m'].max():.2f} m")
    print(f"Saved {target}")


if __name__ == "__main__":
    main()
