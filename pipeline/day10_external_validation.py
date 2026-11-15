"""Locked external-outcome validation against EFFIS burned-area perimeters."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from shapely import make_valid
from shapely.geometry import Point, Polygon, box
from shapely.ops import transform, unary_union

from pipeline.common import ROOT
from pipeline.day2_baseline import EARTH_RADIUS_M


CONFIG_PATH = ROOT / "configs" / "day10_external_validation.json"
PREDICTIONS_PATH = ROOT / "outputs" / "tables" / "geometry_2023_cell_pass_predictions.csv"
RAW_DIRECTORY = ROOT / "data" / "raw" / "day10_effis"
ZIP_PATH = RAW_DIRECTORY / "effis_layer.zip"
SHAPEFILE_PATH = RAW_DIRECTORY / "extracted" / "effis_layer" / "modis.ba.poly.shp"
DBF_PATH = SHAPEFILE_PATH.with_suffix(".dbf")
PRJ_PATH = SHAPEFILE_PATH.with_suffix(".prj")
OUTPUT = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"


@dataclass(frozen=True)
class Day10Result:
    events: pd.DataFrame
    metrics: pd.DataFrame
    bootstrap: pd.DataFrame
    permutation: pd.DataFrame
    diagnostics: pd.DataFrame
    decision: pd.DataFrame
    manifest: pd.DataFrame


def _intersects_bbox(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> bool:
    return left[0] <= right[2] and left[2] >= right[0] and left[1] <= right[3] and left[3] >= right[1]


def read_polygon_shapefile(path: Path, bbox_filter: tuple[float, float, float, float]) -> dict[int, object]:
    """Read only intersecting Polygon/PolygonZ/PolygonM records using the public SHP spec."""
    geometries: dict[int, object] = {}
    with path.open("rb") as stream:
        header = stream.read(100)
        if len(header) != 100 or struct.unpack(">i", header[:4])[0] != 9994:
            raise ValueError("Invalid EFFIS shapefile header")
        record_index = 0
        while True:
            record_header = stream.read(8)
            if not record_header:
                break
            if len(record_header) != 8:
                raise ValueError("Truncated EFFIS shapefile record header")
            _, words = struct.unpack(">2i", record_header)
            content = stream.read(words * 2)
            if len(content) != words * 2:
                raise ValueError("Truncated EFFIS shapefile record")
            shape_type = struct.unpack_from("<i", content, 0)[0]
            if shape_type == 0:
                record_index += 1
                continue
            if shape_type not in {5, 15, 25}:
                raise ValueError(f"Unsupported EFFIS shape type: {shape_type}")
            record_bbox = struct.unpack_from("<4d", content, 4)
            if not _intersects_bbox(record_bbox, bbox_filter):
                record_index += 1
                continue
            part_count, point_count = struct.unpack_from("<2i", content, 36)
            if part_count <= 0 or point_count < 4:
                record_index += 1
                continue
            parts = list(struct.unpack_from(f"<{part_count}i", content, 44)) + [point_count]
            point_offset = 44 + 4 * part_count
            points = struct.unpack_from(f"<{point_count * 2}d", content, point_offset)
            rings = [
                [(points[2 * i], points[2 * i + 1]) for i in range(parts[j], parts[j + 1])]
                for j in range(part_count)
            ]
            # EFFIS events are normally single exterior rings. Treating additional
            # rings as parts before make_valid is conservative for cell linkage.
            polygons = [Polygon(ring) for ring in rings if len(ring) >= 4]
            geometry = make_valid(unary_union(polygons)) if polygons else None
            if geometry is not None and not geometry.is_empty:
                geometries[record_index] = geometry
            record_index += 1
    return geometries


def _dbf_layout(path: Path) -> tuple[int, int, int, list[tuple[str, str, int]]]:
    with path.open("rb") as stream:
        header = stream.read(32)
        if len(header) != 32:
            raise ValueError("Invalid EFFIS DBF header")
        record_count, header_length, record_length = struct.unpack("<xxxxIHH20x", header)
        descriptors = stream.read(header_length - 33)
    fields = []
    for offset in range(0, len(descriptors), 32):
        descriptor = descriptors[offset:offset + 32]
        name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii")
        fields.append((name, chr(descriptor[11]), descriptor[16]))
    return record_count, header_length, record_length, fields


def read_dbf_records(path: Path, indices: set[int]) -> dict[int, dict[str, str]]:
    record_count, header_length, record_length, fields = _dbf_layout(path)
    if indices and max(indices) >= record_count:
        raise ValueError("SHP/DBF record counts are inconsistent")
    records: dict[int, dict[str, str]] = {}
    with path.open("rb") as stream:
        for index in sorted(indices):
            stream.seek(header_length + index * record_length)
            raw = stream.read(record_length)
            if len(raw) != record_length or raw[:1] == b"*":
                continue
            position = 1
            row: dict[str, str] = {}
            for name, _, length in fields:
                row[name] = raw[position:position + length].decode("utf-8", "replace").strip()
                position += length
            records[index] = row
    return records


def _parse_effis_date(value: str) -> date:
    return datetime.fromisoformat(value.strip()).date()


def load_effis_events(config: dict[str, object]) -> list[dict[str, object]]:
    bbox = tuple(config["study_region"]["bbox"])
    geometries = read_polygon_shapefile(SHAPEFILE_PATH, bbox)
    attributes = read_dbf_records(DBF_PATH, set(geometries))
    aoi = box(*bbox)
    test_year = int(config["test_year"])
    minimum_area = float(config["linkage"]["minimum_event_area_ha"])
    rows = []
    for index, geometry in geometries.items():
        record = attributes[index]
        try:
            start = _parse_effis_date(record["FIREDATE"])
            end = _parse_effis_date(record["FINALDATE"])
            area = float(record["AREA_HA"])
        except (KeyError, TypeError, ValueError):
            continue
        clipped = make_valid(geometry.intersection(aoi))
        if start.year != test_year or area < minimum_area or clipped.is_empty:
            continue
        rows.append({
            "event_id": record["id"], "start_date": start, "end_date": max(end, start),
            "area_ha": area, "country": record.get("COUNTRY", ""),
            "province": record.get("PROVINCE", ""), "geometry": clipped,
        })
    if len({row["event_id"] for row in rows}) != len(rows):
        raise ValueError("EFFIS event IDs are not unique after filtering")
    return sorted(rows, key=lambda row: (row["start_date"], row["event_id"]))


def cell_centres(frame: pd.DataFrame, grid_km: float = 10.0) -> pd.DataFrame:
    output = frame.copy()
    grid_m = grid_km * 1_000.0
    output["longitude"] = np.degrees((output["cell_x"] + 0.5) * grid_m / EARTH_RADIUS_M)
    output["latitude"] = np.degrees(np.arcsin(np.clip((output["cell_y"] + 0.5) * grid_m / EARTH_RADIUS_M, -1, 1)))
    output["observation_date"] = pd.to_datetime(output["observation_date"]).dt.date
    return output


def _to_local_metric(geometry: object, latitude_origin: float = 40.0) -> object:
    cosine = math.cos(math.radians(latitude_origin))
    return transform(
        lambda x, y, z=None: (EARTH_RADIUS_M * np.radians(x) * cosine, EARTH_RADIUS_M * np.radians(y)),
        geometry,
    )


def build_spatial_masks(events: list[dict[str, object]], predictions: pd.DataFrame, config: dict[str, object]) -> list[np.ndarray]:
    spatial_buffer = float(config["linkage"]["spatial_buffer_km"]) * 1_000.0
    points = [_to_local_metric(Point(lon, lat)) for lon, lat in predictions[["longitude", "latitude"]].itertuples(index=False)]
    masks = []
    for event in events:
        buffered = _to_local_metric(event["geometry"]).buffer(spatial_buffer)
        masks.append(np.fromiter((buffered.covers(point) for point in points), dtype=bool, count=len(points)))
    return masks


def score_events(
    events: list[dict[str, object]],
    predictions: pd.DataFrame,
    config: dict[str, object],
    shift_days: int = 0,
    spatial_masks: list[np.ndarray] | None = None,
) -> pd.DataFrame:
    temporal_buffer = int(config["linkage"]["temporal_buffer_days"])
    if spatial_masks is None:
        spatial_masks = build_spatial_masks(events, predictions, config)
    if len(spatial_masks) != len(events):
        raise ValueError("Event and spatial-mask counts differ")
    dates = predictions["observation_date"].to_numpy()
    if shift_days:
        year = int(config["test_year"])
        origin = date(year, 1, 1)
        days_in_year = (date(year + 1, 1, 1) - origin).days
        dates = np.array([origin + timedelta(days=((day - origin).days + shift_days) % days_in_year) for day in dates], dtype=object)
    rows = []
    methods = ["modis_count", "viirs_count", "incumbent_prediction", "geometry_aware_prediction"]
    for event, spatial in zip(events, spatial_masks, strict=True):
        start = event["start_date"] - timedelta(days=temporal_buffer)
        end = event["end_date"] + timedelta(days=temporal_buffer)
        temporal = np.fromiter((start <= day <= end for day in dates), dtype=bool, count=len(dates))
        selected = predictions.loc[spatial & temporal]
        row = {key: event[key] for key in ("event_id", "start_date", "end_date", "area_ha", "country", "province")}
        row["linked_cell_passes"] = len(selected)
        row["linked_day_passes"] = int((selected["daynight"] == "D").sum())
        row["linked_night_passes"] = int((selected["daynight"] == "N").sum())
        row.update({method: float(selected[method].sum()) for method in methods})
        rows.append(row)
    return pd.DataFrame(rows)


def association_table(events: pd.DataFrame, selected_method: str, analysis: str = "primary_many_to_many") -> pd.DataFrame:
    rows = []
    for method in ("modis_count", "viirs_count", "incumbent_prediction", "geometry_aware_prediction"):
        x = np.log1p(events["area_ha"].to_numpy(float))
        y = np.log1p(events[method].to_numpy(float))
        rows.append({
            "analysis": analysis,
            "method": method,
            "is_primary": method == selected_method,
            "events": len(events),
            "zero_activity_events": int((events[method] <= 0).sum()),
            "spearman": float(spearmanr(x, y).statistic),
            "kendall_tau": float(kendalltau(x, y).statistic),
        })
    return pd.DataFrame(rows)


def overlap_sensitivity(
    events_geometry: list[dict[str, object]],
    events: pd.DataFrame,
    predictions: pd.DataFrame,
    config: dict[str, object],
    spatial_masks: list[np.ndarray],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    temporal_buffer = int(config["linkage"]["temporal_buffer_days"])
    dates = predictions["observation_date"].to_numpy()
    linkage = []
    for event, spatial in zip(events_geometry, spatial_masks, strict=True):
        start = event["start_date"] - timedelta(days=temporal_buffer)
        end = event["end_date"] + timedelta(days=temporal_buffer)
        temporal = np.fromiter((start <= day <= end for day in dates), dtype=bool, count=len(dates))
        linkage.append(spatial & temporal)
    matrix = np.vstack(linkage)
    multiplicity = matrix.sum(axis=0)
    methods = ["modis_count", "viirs_count", "incumbent_prediction", "geometry_aware_prediction"]
    sensitivity = events.copy()
    denominators = np.maximum(multiplicity, 1)
    for event_index in range(len(events)):
        weights = matrix[event_index].astype(float) / denominators
        for method in methods:
            sensitivity.loc[event_index, method] = float(np.sum(predictions[method].to_numpy(float) * weights))
    associations = int(matrix.sum())
    diagnostics = pd.DataFrame([{
        "linked_prediction_rows": int((multiplicity > 0).sum()),
        "linked_event_row_associations": associations,
        "rows_linked_to_multiple_events": int((multiplicity > 1).sum()),
        "fraction_linked_rows_with_overlap": float(np.mean(multiplicity[multiplicity > 0] > 1))
        if np.any(multiplicity > 0) else 0.0,
        "duplicate_association_fraction": float((associations - (multiplicity > 0).sum()) / associations)
        if associations else 0.0,
        "maximum_event_multiplicity": int(multiplicity.max(initial=0)),
        "sensitivity_rule": "each linked prediction row contributes 1/n to each of n overlapping events",
    }])
    return sensitivity, diagnostics


def bootstrap_events(events: pd.DataFrame, selected_method: str, replicates: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    values = np.empty((replicates, 2))
    for index in range(replicates):
        sample = events.iloc[rng.integers(0, len(events), len(events))]
        area = np.log1p(sample["area_ha"])
        primary = spearmanr(area, np.log1p(sample[selected_method])).statistic
        raw = spearmanr(area, np.log1p(sample["viirs_count"])).statistic
        values[index] = primary, primary - raw
    rows = []
    for column, comparison in enumerate(("harmonized_spearman", "harmonized_minus_viirs_spearman")):
        rows.append({
            "comparison": comparison, "replicates": replicates,
            "estimate": float(spearmanr(np.log1p(events["area_ha"]), np.log1p(events[selected_method])).statistic)
            if column == 0 else float(
                spearmanr(np.log1p(events["area_ha"]), np.log1p(events[selected_method])).statistic
                - spearmanr(np.log1p(events["area_ha"]), np.log1p(events["viirs_count"])).statistic
            ),
            "ci_2_5": float(np.nanquantile(values[:, column], 0.025)),
            "ci_97_5": float(np.nanquantile(values[:, column], 0.975)),
        })
    return pd.DataFrame(rows)


def permutation_test(
    events: list[dict[str, object]],
    predictions: pd.DataFrame,
    config: dict[str, object],
    selected_method: str,
    spatial_masks: list[np.ndarray] | None = None,
) -> pd.DataFrame:
    settings = config["permutation"]
    replicates, seed = int(settings["replicates"]), int(settings["seed"])
    if spatial_masks is None:
        spatial_masks = build_spatial_masks(events, predictions, config)
    observed = score_events(events, predictions, config, spatial_masks=spatial_masks)
    observed_rho = float(spearmanr(np.log1p(observed["area_ha"]), np.log1p(observed[selected_method])).statistic)
    rng = np.random.default_rng(seed)
    shifts = rng.integers(1, 365, size=replicates)
    cache: dict[int, float] = {}
    for shift in np.unique(shifts):
        shifted = score_events(events, predictions, config, int(shift), spatial_masks)
        cache[int(shift)] = float(spearmanr(np.log1p(shifted["area_ha"]), np.log1p(shifted[selected_method])).statistic)
    null = np.array([cache[int(shift)] for shift in shifts])
    p_value = (1 + np.sum(null >= observed_rho)) / (replicates + 1)
    return pd.DataFrame([{
        "test": "shared_circular_calendar_shift", "replicates": replicates,
        "observed_spearman": observed_rho, "null_median": float(np.nanmedian(null)),
        "null_95pct": float(np.nanquantile(null, 0.95)), "p_value_one_sided": float(p_value),
        "unique_shifts_evaluated": len(cache),
    }])


def make_manifest(events: list[dict[str, object]]) -> pd.DataFrame:
    projection = PRJ_PATH.read_text(encoding="utf-8").strip()
    return pd.DataFrame([{
        "source_url": "https://forest-fire.emergency.copernicus.eu/downloads/data.request.form/effis_layer.zip",
        "sha256": hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest(),
        "bytes": ZIP_PATH.stat().st_size, "download_date": date.today().isoformat(),
        "shapefile_records_in_locked_bbox": len(read_polygon_shapefile(SHAPEFILE_PATH, (-9.5, 37.0, -5.5, 43.0))),
        "eligible_2023_events": len(events), "projection_wkt": projection,
    }])


def evaluate() -> Day10Result:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not config.get("frozen_before_reference_download"):
        raise ValueError("Day-10 protocol is not marked frozen")
    predictions = cell_centres(pd.read_csv(PREDICTIONS_PATH))
    if set(pd.to_datetime(predictions["observation_date"]).dt.year) != {int(config["test_year"])}:
        raise ValueError("Prediction year differs from the frozen external test")
    selected_methods = predictions["selected_method"].unique()
    if len(selected_methods) != 1:
        raise ValueError("The locked prediction table has no unique selected method")
    selected_method = f"{selected_methods[0]}_prediction"
    events_geometry = load_effis_events(config)
    spatial_masks = build_spatial_masks(events_geometry, predictions, config)
    events = score_events(events_geometry, predictions, config, spatial_masks=spatial_masks)
    metrics = association_table(events, selected_method)
    sensitivity, diagnostics = overlap_sensitivity(
        events_geometry, events, predictions, config, spatial_masks
    )
    metrics = pd.concat([
        metrics,
        association_table(sensitivity, selected_method, "fractional_overlap_sensitivity"),
    ], ignore_index=True)
    bootstrap = bootstrap_events(events, selected_method, int(config["bootstrap"]["replicates"]), int(config["bootstrap"]["seed"]))
    permutation = permutation_test(events_geometry, predictions, config, selected_method, spatial_masks)
    primary_metrics = metrics[metrics["analysis"] == "primary_many_to_many"].set_index("method")
    primary = primary_metrics.loc[selected_method]
    raw = primary_metrics.loc["viirs_count"]
    gates = config["locked_gates"]
    checks = {
        "minimum_event_support": len(events) >= int(gates["minimum_eligible_events"]),
        "harmonized_spearman_at_least_0_3": primary["spearman"] >= float(gates["harmonized_spearman_minimum"]),
        "no_material_loss_vs_viirs": primary["spearman"] >= raw["spearman"] - float(gates["harmonized_vs_viirs_spearman_tolerance"]),
        "bootstrap_ci_lower_above_zero": bootstrap.set_index("comparison").loc["harmonized_spearman", "ci_2_5"] > 0,
        "permutation_p_at_most_0_05": permutation.loc[0, "p_value_one_sided"] <= float(gates["permutation_p_maximum"]),
    }
    decision = pd.DataFrame([{**checks, "external_outcome_gate_passed": all(checks.values()),
                              "eligible_events": len(events), "selected_method": selected_method}])
    return Day10Result(
        events, metrics, bootstrap, permutation, diagnostics, decision, make_manifest(events_geometry)
    )


def save_figure(events: pd.DataFrame, selected_method: str) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.scatter(events["area_ha"], events[selected_method], alpha=0.65, edgecolor="none")
    axis.set_xscale("log")
    axis.set_yscale("symlog", linthresh=0.1)
    axis.set_xlabel("EFFIS mapped burned area (ha, log scale)")
    axis.set_ylabel("Harmonized MODIS-equivalent activity")
    axis.set_title("Western Iberia 2023: locked external-outcome check")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(FIGURES / "day10_effis_event_association_2023.png", dpi=180)
    plt.close(figure)


def main() -> None:
    result = evaluate()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result.events.to_csv(OUTPUT / "day10_effis_event_scores.csv", index=False)
    result.metrics.to_csv(OUTPUT / "day10_external_metrics.csv", index=False)
    result.bootstrap.to_csv(OUTPUT / "day10_external_bootstrap.csv", index=False)
    result.permutation.to_csv(OUTPUT / "day10_external_permutation.csv", index=False)
    result.diagnostics.to_csv(OUTPUT / "day10_linkage_diagnostics.csv", index=False)
    result.decision.to_csv(OUTPUT / "day10_external_decision.csv", index=False)
    result.manifest.to_csv(OUTPUT / "day10_effis_manifest.csv", index=False)
    selected = str(result.decision.loc[0, "selected_method"])
    save_figure(result.events, selected)
    print(result.metrics.to_string(index=False))
    print(result.bootstrap.to_string(index=False))
    print(result.permutation.to_string(index=False))
    print(result.decision.to_string(index=False))


if __name__ == "__main__":
    main()
