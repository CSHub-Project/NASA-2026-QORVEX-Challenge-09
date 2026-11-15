"""Pixel-level observation evidence from NASA Level-2 active-fire masks.

An observed clear pixel without a detection is not evidence that every part of
its 10-km cell was observed. Keep all mask classes and report clear sampling.
"""

from __future__ import annotations

import argparse
import numpy as np
import pandas as pd
import h5py
from pathlib import Path

from pipeline.day2_baseline import EARTH_RADIUS_M
from pipeline.common import ROOT, load_regions


MASK_CLASSES = {
    0: "not_processed", 1: "not_processed", 2: "not_processed",
    3: "water", 4: "cloud", 5: "clear_nonfire_land",
    6: "unknown", 7: "fire", 8: "fire", 9: "fire",
}


def aggregate_fire_mask(
    mask: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    bbox: tuple[float, float, float, float],
    *,
    grid_km: float = 10,
) -> pd.DataFrame:
    """Count classified geolocated pixels inside an AOI on an equal-area grid.

    The result never interprets cloudy or missing pixels as fire-free. Pixel
    counts are observation evidence, not equal-area coverage fractions.
    """
    if mask.shape != latitude.shape or mask.shape != longitude.shape:
        raise ValueError("Fire mask and geolocation arrays must have identical shapes")
    if mask.ndim != 2 or grid_km <= 0:
        raise ValueError("Expected two-dimensional arrays and positive grid size")
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid bounding box")
    selected = (
        np.isfinite(latitude) & np.isfinite(longitude)
        & (latitude >= south) & (latitude <= north)
        & (longitude >= west) & (longitude <= east)
    )
    if not selected.any():
        return pd.DataFrame(columns=["cell_x", "cell_y", *sorted(set(MASK_CLASSES.values())),
                                     "valid_land_pixels", "observed_clear_no_detection"])
    codes = mask[selected].astype(np.int16)
    categories = np.array([MASK_CLASSES.get(int(code), "unknown") for code in codes])
    grid_m = grid_km * 1000
    x = np.floor(EARTH_RADIUS_M * np.deg2rad(longitude[selected]) / grid_m).astype(np.int32)
    y = np.floor(EARTH_RADIUS_M * np.sin(np.deg2rad(latitude[selected])) / grid_m).astype(np.int32)
    frame = pd.DataFrame({"cell_x": x, "cell_y": y, "class": categories})
    counts = frame.groupby(["cell_x", "cell_y", "class"]).size().unstack(fill_value=0)
    for category in set(MASK_CLASSES.values()):
        if category not in counts:
            counts[category] = 0
    counts = counts.reset_index().rename_axis(None, axis=1)
    counts["valid_land_pixels"] = counts["clear_nonfire_land"] + counts["fire"]
    counts["observed_clear_no_detection"] = (
        (counts["clear_nonfire_land"] > 0) & (counts["fire"] == 0)
    )
    return counts.sort_values(["cell_x", "cell_y"]).reset_index(drop=True)


def find_dataset(file: h5py.File, names: set[str]) -> str:
    matches: list[str] = []

    def collect(name: str, item: h5py.Group | h5py.Dataset) -> None:
        if isinstance(item, h5py.Dataset) and name.rsplit("/", 1)[-1].lower() in names:
            matches.append(name)

    file.visititems(collect)
    if len(matches) != 1:
        raise ValueError(f"Expected one dataset named {names}, found {matches}")
    return matches[0]


def read_viirs_pair(fire_file: Path, geo_file: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read the full VIIRS I-band fire mask and its colocated geolocation."""
    with h5py.File(fire_file) as fire, h5py.File(geo_file) as geo:
        mask = fire[find_dataset(fire, {"fire mask", "fire_mask"})][:]
        latitude = geo[find_dataset(geo, {"latitude"})][:]
        longitude = geo[find_dataset(geo, {"longitude"})][:]
    if mask.shape != latitude.shape or mask.shape != longitude.shape:
        raise ValueError("VIIRS fire mask and geolocation dimensions disagree")
    return mask, latitude, longitude


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-key", default="2023218.1330")
    parser.add_argument("--region", default="western_iberia")
    args = parser.parse_args()
    region = next((r for r in load_regions() if r.id == args.region), None)
    if region is None:
        raise ValueError(f"Unknown region: {args.region}")
    directory = ROOT / "data" / "raw" / "swaths" / args.acquisition_key
    fire = list(directory.glob("VNP14IMG.*.nc"))
    geo = list(directory.glob("VNP03IMG.*.nc"))
    if len(fire) != 1 or len(geo) != 1:
        raise ValueError("Download exactly one VIIRS fire/geolocation granule pair first")
    mask, latitude, longitude = read_viirs_pair(fire[0], geo[0])
    evidence = aggregate_fire_mask(mask, latitude, longitude, region.bbox)
    evidence.insert(0, "region_id", args.region)
    evidence.insert(1, "acquisition_key", args.acquisition_key)
    target = ROOT / "outputs" / "tables" / f"day8_viirs_observation_{args.acquisition_key}.csv"
    evidence.to_csv(target, index=False)
    print(f"Saved {len(evidence)} geolocated cells to {target}")
    print(evidence[["fire", "clear_nonfire_land", "cloud", "not_processed", "unknown"]].sum().to_string())
    print(f"Cells with clear sampling and no detection: {evidence['observed_clear_no_detection'].sum()}")


if __name__ == "__main__":
    main()
