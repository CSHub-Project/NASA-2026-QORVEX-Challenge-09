"""Run the frozen Day-11 multi-swath, dual-sensor observation audit."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from pipeline.common import ROOT, load_regions
from pipeline.day2_baseline import EARTH_RADIUS_M
from pipeline.day8_swath_mask import MASK_CLASSES, aggregate_fire_mask, find_dataset


CONFIG_PATH = ROOT / "configs" / "day11_multiswath_audit.json"
INVENTORY_PATH = ROOT / "outputs" / "tables" / "day8_swath_inventory_2023-08-06.csv"


def read_viirs_pair(fire_path: Path, geo_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with h5py.File(fire_path) as fire, h5py.File(geo_path) as geo:
        mask = fire[find_dataset(fire, {"fire mask", "fire_mask"})][:]
        latitude = geo[find_dataset(geo, {"latitude"})][:]
        longitude = geo[find_dataset(geo, {"longitude"})][:]
    return mask, latitude, longitude


def read_modis_pair(fire_path: Path, geo_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    try:
        from pyhdf.SD import SD, SDC
    except ImportError as exc:  # pragma: no cover - exercised only in incomplete environments
        raise RuntimeError("MODIS HDF4 input requires pyhdf>=0.11.7") from exc
    fire = SD(str(fire_path), SDC.READ)
    geo = SD(str(geo_path), SDC.READ)
    try:
        mask = fire.select("fire mask")[:]
        latitude = geo.select("Latitude")[:]
        longitude = geo.select("Longitude")[:]
    finally:
        fire.end()
        geo.end()
    return mask, latitude, longitude


def aoi_cells(bbox: tuple[float, float, float, float], grid_km: float) -> pd.DataFrame:
    west, south, east, north = bbox
    grid_m = grid_km * 1000
    x0 = int(np.floor(EARTH_RADIUS_M * np.deg2rad(west) / grid_m))
    x1 = int(np.floor(EARTH_RADIUS_M * np.deg2rad(east) / grid_m))
    y0 = int(np.floor(EARTH_RADIUS_M * np.sin(np.deg2rad(south)) / grid_m))
    y1 = int(np.floor(EARTH_RADIUS_M * np.sin(np.deg2rad(north)) / grid_m))
    cells = pd.MultiIndex.from_product(
        [range(x0, x1 + 1), range(y0, y1 + 1)], names=["cell_x", "cell_y"]
    ).to_frame(index=False)
    cells["center_lon"] = np.rad2deg((cells["cell_x"] + 0.5) * grid_m / EARTH_RADIUS_M)
    cells["center_lat"] = np.rad2deg(np.arcsin((cells["cell_y"] + 0.5) * grid_m / EARTH_RADIUS_M))
    return cells[
        cells["center_lon"].between(west, east)
        & cells["center_lat"].between(south, north)
    ].reset_index(drop=True)


def classify_state(frame: pd.DataFrame) -> pd.Series:
    observed = frame[["not_processed", "water", "cloud", "clear_nonfire_land", "unknown", "fire"]].sum(axis=1)
    return pd.Series(
        np.select(
            [frame["fire"] > 0, frame["clear_nonfire_land"] > 0, observed > 0],
            ["fire_observed", "clear_sampled_no_detection", "obscured_or_nonland_only"],
            default="not_observed",
        ),
        index=frame.index,
    )


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def locate_pair(key: str, fire_product: str, geo_product: str) -> tuple[Path, Path]:
    directory = ROOT / "data" / "raw" / "swaths" / key
    fire = list(directory.glob(f"{fire_product}.*"))
    geo = list(directory.glob(f"{geo_product}.*"))
    if len(fire) != 1 or len(geo) != 1:
        raise ValueError(f"Expected one complete pair for {key}; found {len(fire)} fire and {len(geo)} geo")
    return fire[0], geo[0]


def run_audit() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = pd.read_csv(INVENTORY_PATH, dtype={"acquisition_key": str})
    region = next(r for r in load_regions() if r.id == config["study_region"])
    grid_km = float(config["grid_km"])
    template = aoi_cells(region.bbox, grid_km)
    all_rows: list[pd.DataFrame] = []
    manifest_rows: list[dict[str, object]] = []
    pair_rows: list[dict[str, object]] = []

    for sensor, definition in config["sensor_families"].items():
        for key in definition["expected_acquisitions"]:
            fire_path, geo_path = locate_pair(key, definition["fire_product"], definition["geolocation_product"])
            reader = read_viirs_pair if sensor == "VIIRS" else read_modis_pair
            mask, latitude, longitude = reader(fire_path, geo_path)
            if mask.shape != latitude.shape or mask.shape != longitude.shape:
                raise ValueError(f"Mask/geolocation shape mismatch for {key}: {mask.shape}, {latitude.shape}")
            codes = set(np.unique(mask).astype(int))
            allowed = set(config["acceptance_gates"]["allowed_mask_codes"])
            if not codes <= allowed:
                raise ValueError(f"Unexpected mask codes for {key}: {sorted(codes - allowed)}")
            evidence = aggregate_fire_mask(mask, latitude, longitude, region.bbox, grid_km=grid_km)
            complete = template.merge(evidence, on=["cell_x", "cell_y"], how="left")
            count_columns = sorted(set(MASK_CLASSES.values())) + ["valid_land_pixels"]
            complete[count_columns] = complete[count_columns].fillna(0).astype(int)
            complete["observed_clear_no_detection"] = (
                complete["clear_nonfire_land"].gt(0) & complete["fire"].eq(0)
            )
            complete["evidence_state"] = classify_state(complete)
            match = inventory[(inventory["product"] == definition["fire_product"])
                              & (inventory["acquisition_key"] == key)].iloc[0]
            complete.insert(0, "sensor", sensor)
            complete.insert(1, "acquisition_key", key)
            complete.insert(2, "time_start_utc", match["time_start_utc"])
            complete.insert(3, "day_night", str(match["day_night_flag"]).upper())
            all_rows.append(complete)
            pair_rows.append({
                "sensor": sensor, "acquisition_key": key,
                "day_night": str(match["day_night_flag"]).upper(),
                "mask_rows": mask.shape[0], "mask_columns": mask.shape[1],
                "aoi_cells": len(complete), "intersected_cells": int((complete["evidence_state"] != "not_observed").sum()),
                "clear_negative_cells": int((complete["evidence_state"] == "clear_sampled_no_detection").sum()),
                "fire_cells": int((complete["evidence_state"] == "fire_observed").sum()),
                "mask_codes": ",".join(map(str, sorted(codes))),
            })
            for product, path in ((definition["fire_product"], fire_path), (definition["geolocation_product"], geo_path)):
                manifest_rows.append({
                    "sensor": sensor, "product": product, "acquisition_key": key,
                    "file_name": path.name, "bytes": path.stat().st_size, "sha256": file_sha256(path),
                })

    cells = pd.concat(all_rows, ignore_index=True)
    pairs = pd.DataFrame(pair_rows)
    manifest = pd.DataFrame(manifest_rows)
    daily_counts = cells.groupby(["sensor", "cell_x", "cell_y", "center_lon", "center_lat"], as_index=False)[
        ["not_processed", "water", "cloud", "clear_nonfire_land", "unknown", "fire"]
    ].sum()
    daily_counts["evidence_state"] = classify_state(daily_counts)
    gates = {
        "complete_pairs": len(pairs) == config["acceptance_gates"]["complete_pairs"],
        "checksums_complete": len(manifest) == 16 and manifest["sha256"].str.len().eq(64).all(),
        "sensor_balance": all(len(pairs[pairs["sensor"] == sensor]) >= 4 for sensor in ("MODIS", "VIIRS")),
        "day_night_balance": all(
            (pairs[pairs["sensor"] == sensor]["day_night"].value_counts().reindex(["DAY", "NIGHT"], fill_value=0) >= 2).all()
            for sensor in ("MODIS", "VIIRS")
        ),
        "valid_mask_codes": pairs["mask_codes"].notna().all(),
        "explicit_not_observed": (cells["evidence_state"] == "not_observed").any(),
        "clear_negative_semantics": (
            cells["observed_clear_no_detection"]
            == ((cells["clear_nonfire_land"] > 0) & (cells["fire"] == 0))
        ).all(),
    }
    decision = pd.DataFrame([{"gate": gate, "passed": bool(value)} for gate, value in gates.items()])
    decision.loc[len(decision)] = ["overall", bool(all(gates.values()))]
    return cells, pairs, manifest, daily_counts, decision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    cells, pairs, manifest, daily, decision = run_audit()
    output = ROOT / "outputs" / "tables"
    cells.to_csv(output / "day11_cell_acquisition_evidence.csv", index=False)
    pairs.to_csv(output / "day11_pair_summary.csv", index=False)
    manifest.to_csv(output / "day11_swath_manifest.csv", index=False)
    daily.to_csv(output / "day11_daily_sensor_evidence.csv", index=False)
    decision.to_csv(output / "day11_decision.csv", index=False)
    overall = decision.loc[decision["gate"] == "overall", "passed"].iloc[0]
    print(pairs.to_string(index=False))
    print(f"Day-11 overall gate: {'PASS' if overall else 'FAIL'}")


if __name__ == "__main__":
    main()
