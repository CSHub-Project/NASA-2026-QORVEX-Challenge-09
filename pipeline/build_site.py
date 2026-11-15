"""Build the zero-dependency Fyrora dashboard from validated day-four outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import pandas as pd

from pipeline.team_spatial import SOURCE_PATHS as TEAM_SPATIAL_SOURCE_PATHS
from pipeline.team_spatial import POINTS_PATH as TEAM_POINTS_PATH
from pipeline.team_spatial import build_qorvex_spatial_payload, build_victoria_point_payload


ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site"
LAND_GEOJSON_PATH = SITE_SOURCE / "data" / "ne_110m_land.geojson"
FONT_DIR = SITE_SOURCE / "fonts"
LEAFLET_DIR = SITE_SOURCE / "vendor" / "leaflet"
DEFAULT_OUTPUT = ROOT / "dist"
CALENDAR_PATH = ROOT / "outputs" / "tables" / "day4_calendar_ready_2017_2020.csv"
METRICS_PATH = ROOT / "outputs" / "tables" / "day4_year_holdout_metrics.csv"
BOOTSTRAP_PATH = ROOT / "outputs" / "tables" / "day4_year_holdout_bootstrap.csv"
TRANSFER_PATH = ROOT / "outputs" / "tables" / "day4_spatial_transfer_metrics.csv"
REGIONS_PATH = ROOT / "configs" / "regions.json"
SOURCE_INVENTORY_PATH = ROOT / "outputs" / "tables" / "day4_source_inventory.csv"
MATCHES_PATH = ROOT / "outputs" / "tables" / "day4_pass_matches.csv"
RAW_MANIFEST_PATH = ROOT / "outputs" / "tables" / "firms_raw_manifest_2017_2020.csv"
INDEPENDENT_METRICS_PATH = ROOT / "outputs" / "tables" / "independent_2021_western_iberia_metrics.csv"
INDEPENDENT_BOOTSTRAP_PATH = ROOT / "outputs" / "tables" / "independent_2021_western_iberia_bootstrap.csv"
INDEPENDENT_MATCHES_PATH = ROOT / "outputs" / "tables" / "independent_2021_western_iberia_pass_matches.csv"
INDEPENDENT_RAW_MANIFEST_PATH = ROOT / "outputs" / "tables" / "firms_raw_manifest_2021_western_iberia.csv"
DAY7_TEST_PATH = ROOT / "outputs" / "tables" / "day7_2022_locked_test.csv"
DAY7_SELECTION_PATH = ROOT / "outputs" / "tables" / "day7_2019_candidate_selection.csv"
DAY7_BOOTSTRAP_PATH = ROOT / "outputs" / "tables" / "day7_2022_candidate_bootstrap.csv"
DAY7_MATCHES_PATH = ROOT / "outputs" / "tables" / "day7_2022_western_iberia_pass_matches.csv"
DAY7_RAW_MANIFEST_PATH = ROOT / "outputs" / "tables" / "firms_raw_manifest_2022_western_iberia.csv"
OBSERVABILITY_AUDIT_PATH = ROOT / "outputs" / "tables" / "detection_support_audit_2017_2023.csv"
GEOMETRY_TEST_PATH = ROOT / "outputs" / "tables" / "geometry_2023_locked_test.csv"
GEOMETRY_SELECTION_PATH = ROOT / "outputs" / "tables" / "geometry_2019_selection.csv"
GEOMETRY_BOOTSTRAP_PATH = ROOT / "outputs" / "tables" / "geometry_2023_bootstrap.csv"
GEOMETRY_INTERVAL_PATH = ROOT / "outputs" / "tables" / "geometry_2023_interval_coverage.csv"
GEOMETRY_PREDICTIONS_PATH = ROOT / "outputs" / "tables" / "geometry_2023_cell_pass_predictions.csv"
GEOMETRY_MATCHES_PATH = ROOT / "outputs" / "tables" / "geometry_2023_pass_matches.csv"
GEOMETRY_RAW_MANIFEST_PATH = ROOT / "outputs" / "tables" / "firms_raw_manifest_2023_western_iberia.csv"
DAY9_METRICS_PATH = ROOT / "outputs" / "tables" / "day9_independent_transfer_metrics.csv"
DAY9_BOOTSTRAP_PATH = ROOT / "outputs" / "tables" / "day9_independent_transfer_bootstrap.csv"
DAY9_DECISION_PATH = ROOT / "outputs" / "tables" / "day9_independent_transfer_decision.csv"
DAY9_MATCHES_PATH = ROOT / "outputs" / "tables" / "day9_independent_transfer_pass_matches.csv"
DAY9_RAW_MANIFEST_PATH = ROOT / "outputs" / "tables" / "day9_firms_raw_manifest_2024.csv"
DAY9_REGIONS_PATH = ROOT / "configs" / "day9_independent_regions.json"
DAY10_METRICS_PATH = ROOT / "outputs" / "tables" / "day10_external_metrics.csv"
DAY10_BOOTSTRAP_PATH = ROOT / "outputs" / "tables" / "day10_external_bootstrap.csv"
DAY10_PERMUTATION_PATH = ROOT / "outputs" / "tables" / "day10_external_permutation.csv"
DAY10_DECISION_PATH = ROOT / "outputs" / "tables" / "day10_external_decision.csv"
DAY10_DIAGNOSTICS_PATH = ROOT / "outputs" / "tables" / "day10_linkage_diagnostics.csv"
DAY10_MANIFEST_PATH = ROOT / "outputs" / "tables" / "day10_effis_manifest.csv"
DAY10_CONFIG_PATH = ROOT / "configs" / "day10_external_validation.json"
DAY11_PAIRS_PATH = ROOT / "outputs" / "tables" / "day11_pair_summary.csv"
DAY11_DECISION_PATH = ROOT / "outputs" / "tables" / "day11_decision.csv"
DAY11_MANIFEST_PATH = ROOT / "outputs" / "tables" / "day11_swath_manifest.csv"
DAY12_CLAIMS_PATH = ROOT / "outputs" / "tables" / "day12_claim_registry.csv"
DAY12_READINESS_PATH = ROOT / "outputs" / "tables" / "day12_readiness_decision.json"
DAY12_PASSPORT_PATH = ROOT / "outputs" / "tables" / "day12_evidence_passport.json"
DAY12_GEOJSON_PATH = ROOT / "outputs" / "tables" / "day12_observation_evidence.geojson"
DAY12_OPENAPI_PATH = ROOT / "outputs" / "tables" / "day12_openapi.json"
DAY12_CONFIG_PATH = ROOT / "configs" / "day12_product_readiness.json"
PROJECT_DEMO_PATH = ROOT / "submission" / "demo" / "fyrora-space-apps-demo-final.pdf"
PROJECT_DEMO_OUTPUT_NAME = "fyrora-space-apps-demo.pdf"
PAIRS_2017_2020_PATH = ROOT / "data" / "processed" / "contemporaneous_pairs_2017_2020_10km.parquet"
SCORED_2020_PATH = ROOT / "data" / "processed" / "year_holdout_scored_2017_2020_10km.parquet"
EARTH_RADIUS_M = 6_371_008.8
GRID_SIZE_M = 10_000.0


def _clean_number(value: object, digits: int = 6) -> int | float | None:
    if pd.isna(value):
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return round(number, digits)


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {column: _clean_number(value) if isinstance(value, (int, float)) else value
         for column, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _region_count_wape(metrics: pd.DataFrame, region_id: str, model: str) -> tuple[float, int]:
    rows = metrics[
        (metrics["region_id"] == region_id)
        & (metrics["model"] == model)
        & (metrics["metric"] == "count")
        & (metrics["daynight"].isin(["D", "N"]))
    ]
    if set(rows["daynight"]) != {"D", "N"}:
        raise ValueError(f"Both day and night count metrics required for {region_id}")
    absolute_error = (rows["mae"] * rows["test_cell_passes"]).sum()
    observed = (rows["mean_observed"] * rows["test_cell_passes"]).sum()
    return float(absolute_error / observed), int(rows["test_cell_passes"].sum())


def build_aoi_payload() -> dict[str, object]:
    """Build a compact, browser-filterable Western Iberia cell-day dataset.

    Historical years retain observed Aqua MODIS counts. The frozen 2020 holdout
    uses the selected VIIRS-to-MODIS-equivalent prediction. A row only asserts
    support inside a matched detection-derived pass; it is not a full-swath
    observation claim.
    """
    keys = ["pair_id", "region_id", "observation_date", "daynight", "cell_x", "cell_y"]
    pairs = pd.read_parquet(
        PAIRS_2017_2020_PATH,
        columns=keys + ["modis_count"],
    )
    pairs = pairs[pairs["region_id"] == "western_iberia"].copy()
    pairs["observation_date"] = pd.to_datetime(pairs["observation_date"]).dt.strftime("%Y-%m-%d")
    pairs["year"] = pairs["observation_date"].str[:4].astype(int)

    historical = (
        pairs[pairs["year"] < 2020]
        .groupby(["observation_date", "daynight", "cell_x", "cell_y"], as_index=False)
        .agg(activity_count=("modis_count", "sum"), matched_passes=("pair_id", "nunique"))
    )
    historical["source_code"] = "M"

    scored = pd.read_parquet(
        SCORED_2020_PATH,
        columns=keys + ["selected_modis_count"],
    )
    scored = scored[scored["region_id"] == "western_iberia"].copy()
    scored["observation_date"] = pd.to_datetime(scored["observation_date"]).dt.strftime("%Y-%m-%d")
    holdout = (
        scored.groupby(["observation_date", "daynight", "cell_x", "cell_y"], as_index=False)
        .agg(activity_count=("selected_modis_count", "sum"), matched_passes=("pair_id", "nunique"))
    )
    holdout["source_code"] = "H"

    cells = pd.concat([historical, holdout], ignore_index=True)
    cells["longitude"] = cells["cell_x"].map(
        lambda value: math.degrees((float(value) + 0.5) * GRID_SIZE_M / EARTH_RADIUS_M)
    )
    cells["latitude"] = cells["cell_y"].map(
        lambda value: math.degrees(
            math.asin(max(-1.0, min(1.0, (float(value) + 0.5) * GRID_SIZE_M / EARTH_RADIUS_M)))
        )
    )
    cells.sort_values(["observation_date", "daynight", "cell_y", "cell_x"], inplace=True)

    rows = [
        [
            row.observation_date,
            row.daynight,
            round(float(row.longitude), 5),
            round(float(row.latitude), 5),
            round(float(row.activity_count), 5),
            int(row.matched_passes),
            row.source_code,
        ]
        for row in cells.itertuples(index=False)
    ]
    return {
        "schemaVersion": 1,
        "columns": [
            "date", "daynight", "longitude", "latitude", "activityCount",
            "matchedPasses", "sourceCode",
        ],
        "scope": {
            "regionId": "western_iberia",
            "bbox": [-9.5, 37.0, -5.5, 43.0],
            "startDate": "2017-01-01",
            "endDate": "2020-12-31",
            "gridKm": 10,
            "sourceCodes": {
                "M": "Aqua MODIS observed",
                "H": "VIIRS harmonized holdout",
            },
            "supportMeaning": (
                "At least one matched detection-derived pass contributed a cell-day row; "
                "absence is unknown support, not a fire-free claim."
            ),
        },
        "rows": rows,
    }


def build_payload() -> dict[str, object]:
    calendar = pd.read_csv(CALENDAR_PATH)
    metrics = pd.read_csv(METRICS_PATH)
    bootstrap = pd.read_csv(BOOTSTRAP_PATH)
    transfer = pd.read_csv(TRANSFER_PATH)
    source_inventory = pd.read_csv(SOURCE_INVENTORY_PATH)
    matches = pd.read_csv(MATCHES_PATH)
    independent_metrics = pd.read_csv(INDEPENDENT_METRICS_PATH)
    independent_bootstrap = pd.read_csv(INDEPENDENT_BOOTSTRAP_PATH)
    independent_matches = pd.read_csv(INDEPENDENT_MATCHES_PATH)
    day7_test = pd.read_csv(DAY7_TEST_PATH)
    day7_selection = pd.read_csv(DAY7_SELECTION_PATH)
    day7_matches = pd.read_csv(DAY7_MATCHES_PATH)
    observability_audit = pd.read_csv(OBSERVABILITY_AUDIT_PATH)
    geometry_test = pd.read_csv(GEOMETRY_TEST_PATH)
    geometry_selection = pd.read_csv(GEOMETRY_SELECTION_PATH)
    geometry_bootstrap = pd.read_csv(GEOMETRY_BOOTSTRAP_PATH)
    geometry_intervals = pd.read_csv(GEOMETRY_INTERVAL_PATH)
    geometry_matches = pd.read_csv(GEOMETRY_MATCHES_PATH)
    day9_metrics = pd.read_csv(DAY9_METRICS_PATH)
    day9_bootstrap = pd.read_csv(DAY9_BOOTSTRAP_PATH)
    day9_decision = pd.read_csv(DAY9_DECISION_PATH).iloc[0]
    day10_metrics = pd.read_csv(DAY10_METRICS_PATH)
    day10_bootstrap = pd.read_csv(DAY10_BOOTSTRAP_PATH)
    day10_permutation = pd.read_csv(DAY10_PERMUTATION_PATH).iloc[0]
    day10_decision = pd.read_csv(DAY10_DECISION_PATH).iloc[0]
    day10_diagnostics = pd.read_csv(DAY10_DIAGNOSTICS_PATH).iloc[0]
    day11_pairs = pd.read_csv(DAY11_PAIRS_PATH)
    day11_decision = pd.read_csv(DAY11_DECISION_PATH)
    day12_passport = json.loads(DAY12_PASSPORT_PATH.read_text(encoding="utf-8"))
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))

    expected_columns = {
        "region_id", "observation_date", "daynight", "activity_count",
        "matched_passes", "series_source", "has_matched_coverage", "year",
        "month", "day", "percentile_vs_history", "robust_z_vs_history",
    }
    if set(calendar.columns) != expected_columns:
        raise ValueError("Calendar schema differs from the reviewed day-four contract")
    if calendar.duplicated(["region_id", "observation_date", "daynight"]).any():
        raise ValueError("Calendar contains duplicate region/date/day-night rows")
    missing = ~calendar["has_matched_coverage"].astype(bool)
    if calendar.loc[missing, "activity_count"].notna().any():
        raise ValueError("No-coverage rows must remain null, never zero-filled")
    if (calendar.loc[~missing, "activity_count"] < 0).any():
        raise ValueError("Activity counts cannot be negative")
    configured_regions = {region["id"] for region in regions}
    if set(calendar["region_id"]) != configured_regions:
        raise ValueError("Configured study regions and validated calendar differ")
    if set(source_inventory["region_id"]) != configured_regions:
        raise ValueError("Source inventory does not cover every study region")

    calendar_rows = []
    for row in calendar.itertuples(index=False):
        calendar_rows.append([
            row.region_id,
            row.observation_date,
            row.daynight,
            _clean_number(row.activity_count),
            _clean_number(row.matched_passes),
            bool(row.has_matched_coverage),
            _clean_number(row.percentile_vs_history),
            _clean_number(row.robust_z_vs_history),
            row.series_source if isinstance(row.series_source, str) else None,
        ])

    overall = metrics[
        (metrics["region_id"] == "all") & (metrics["daynight"] == "all")
    ].copy()
    count_overall = overall[overall["metric"] == "count"].set_index("model")
    baseline_wape = float(count_overall.loc["baseline", "wape"])
    selected_wape = float(count_overall.loc["selected", "wape"])
    europe_id = "western_iberia"
    europe_baseline_wape, europe_test_cells = _region_count_wape(metrics, europe_id, "baseline")
    europe_selected_wape, selected_cells = _region_count_wape(metrics, europe_id, "selected")
    if selected_cells != europe_test_cells:
        raise ValueError("European pilot methods must use the same holdout sample")
    europe_transfer = transfer[transfer["heldout_region"] == europe_id].set_index("method")
    if set(europe_transfer.index) != {"baseline", "model"}:
        raise ValueError("European pilot requires a strict unseen-region transfer test")
    europe_calendar = calendar[
        (calendar["region_id"] == europe_id) & (calendar["year"] == 2020)
    ]
    independent_count = independent_metrics[
        (independent_metrics["region_id"] == "all")
        & (independent_metrics["daynight"] == "all")
        & (independent_metrics["metric"] == "count")
    ].set_index("model")
    if not {"baseline", "selected"}.issubset(independent_count.index):
        raise ValueError("2021 independent count test is incomplete")
    independent_baseline = independent_count.loc["baseline"]
    independent_selected = independent_count.loc["selected"]
    if independent_baseline["test_cell_passes"] != independent_selected["test_cell_passes"]:
        raise ValueError("2021 independent methods use different samples")
    independent_count_bootstrap = independent_bootstrap[
        independent_bootstrap["metric"] == "count"
    ].iloc[0]
    def _day7_index(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[(frame["region_id"] == europe_id) & (frame["daynight"] == "all")].set_index("model")

    day7_test_index = _day7_index(day7_test)
    day7_selection_index = _day7_index(day7_selection)
    required_day7 = {"fixed_ratio", "legacy", "viirs_only", "monotone_viirs_only"}
    if set(day7_test_index.index) != required_day7 or set(day7_selection_index.index) != required_day7:
        raise ValueError("Day 7 test or preregistered selection is incomplete")
    if day7_selection_index.loc[["legacy", "viirs_only", "monotone_viirs_only"], "wape"].idxmin() != "legacy":
        raise ValueError("2019 preregistered selection differs from the reviewed result")
    if day7_test_index["cell_passes"].nunique() != 1:
        raise ValueError("Day 7 candidate methods use different test samples")
    audit2022 = observability_audit[
        (observability_audit["year"] == 2022)
        & (observability_audit["region_id"] == europe_id)
    ]
    if set(audit2022["daynight"]) != {"D", "N"}:
        raise ValueError("The 2022 detection-support audit requires day and night")
    if audit2022["union_cell_passes"].sum() != int(day7_test_index.loc["legacy", "cell_passes"]):
        raise ValueError("The 2022 audit and model test use different samples")
    modis_positive_cells = int((audit2022["modis_only_cell_passes"] + audit2022["shared_positive_cell_passes"]).sum())
    modis_only_cells = int(audit2022["modis_only_cell_passes"].sum())
    modis_detections_without_viirs = int(audit2022["modis_detections_without_viirs_cell"].sum())
    modis_detections = int(audit2022["modis_detections"].sum())
    geometry_test_index = _day7_index(geometry_test)
    geometry_selection_index = _day7_index(geometry_selection)
    if set(geometry_test_index.index) != {"fixed_ratio", "incumbent", "geometry_aware"}:
        raise ValueError("The 2023 geometry test is incomplete")
    if set(geometry_selection_index.index) != {"incumbent", "geometry_aware"}:
        raise ValueError("The 2019 geometry selection is incomplete")
    if geometry_selection_index.loc["geometry_aware", "wape"] >= geometry_selection_index.loc["incumbent", "wape"]:
        raise ValueError("The frozen 2019 geometry choice differs from the reviewed result")
    if geometry_test_index["cell_passes"].nunique() != 1:
        raise ValueError("The 2023 geometry models use different test samples")
    interval_index = geometry_intervals.set_index("daynight")
    if set(interval_index.index) != {"all", "D", "N"}:
        raise ValueError("The 2023 empirical intervals are incomplete")
    geometry_bootstrap_upper = float(geometry_bootstrap.iloc[0]["ci_97_5"])
    geometry_subgroup = geometry_test.set_index(["model", "region_id", "daynight"])
    geometry_promoted = (
        float(geometry_test_index.loc["geometry_aware", "wape"])
        < min(float(geometry_test_index.loc["incumbent", "wape"]),
              float(geometry_test_index.loc["fixed_ratio", "wape"]))
        and all(float(geometry_subgroup.loc[("geometry_aware", europe_id, d), "wape"])
                <= float(geometry_subgroup.loc[("incumbent", europe_id, d), "wape"])
                for d in ("D", "N"))
        and geometry_bootstrap_upper < 0
    )

    return {
        "meta": {
            "product": "Fyrora",
            "challenge": "Harmonization of MODIS and VIIRS Hot Spots",
            "calendarSchema": [
                "regionId", "date", "daynight", "activityCount", "matchedPasses",
                "hasCoverage", "percentile", "robustZ", "seriesSource",
            ],
            "years": sorted(calendar["year"].astype(int).unique().tolist()),
            "defaultView": {"regionId": "western_iberia", "year": 2020, "daynight": "D"},
            "calendarRows": len(calendar_rows),
            "observations": int(source_inventory["observations"].sum()),
            "matchedPasses": len(matches),
            "studyRegions": len(regions),
            "testYear": 2020,
            "countWapeImprovementPct": round((baseline_wape - selected_wape) / baseline_wape * 100, 1),
            "calendarMeaning": "Aqua MODIS observed activity on contemporaneous matched passes",
            "generatedFrom": "validated day-four tables committed with the project",
        },
        "regions": regions,
        "sourceInventory": _records(source_inventory),
        "calendar": calendar_rows,
        "metrics": _records(metrics),
        "bootstrap": _records(bootstrap),
        "spatialTransfer": _records(transfer),
        "observabilityAudit": _records(observability_audit),
        "independentTransfer2024": {
            "regions": json.loads(DAY9_REGIONS_PATH.read_text(encoding="utf-8")),
            "metrics": _records(day9_metrics),
            "bootstrap": _records(day9_bootstrap),
            "gatePassed": bool(day9_decision["external_transfer_gate_passed"]),
            "matchedPasses": int(len(pd.read_csv(DAY9_MATCHES_PATH))),
        },
        "externalOutcome2023": {
            "metrics": _records(day10_metrics),
            "bootstrap": _records(day10_bootstrap),
            "eligibleEvents": int(day10_decision["eligible_events"]),
            "selectedMethod": day10_decision["selected_method"],
            "gatePassed": bool(day10_decision["external_outcome_gate_passed"]),
            "permutationP": round(float(day10_permutation["p_value_one_sided"]), 6),
            "overlapFraction": round(float(day10_diagnostics["fraction_linked_rows_with_overlap"]), 6),
        },
        "evidenceProduct": {
            "fullSwathGatePassed": bool(day11_decision.loc[day11_decision["gate"] == "overall", "passed"].iloc[0]),
            "auditedPairs": len(day11_pairs),
            "sensorFamilies": int(day11_pairs["sensor"].nunique()),
            "fireCells": int(day11_pairs["fire_cells"].sum()),
            "clearNegativeCells": int(day11_pairs["clear_negative_cells"].sum()),
            "releaseStage": day12_passport["releaseStage"],
            "operationalReady": bool(day12_passport["operationalReady"]),
            "supportedClaims": int(day12_passport["supportedClaims"]),
            "failedOrUnsupportedClaims": int(day12_passport["failedOrUnsupportedClaims"]),
        },
        "europePilot": {
            "regionId": europe_id,
            "year": 2020,
            "testCellPasses": europe_test_cells,
            "baselineWape": round(europe_baseline_wape, 6),
            "selectedWape": round(europe_selected_wape, 6),
            "transferBaselineWape": round(float(europe_transfer.loc["baseline", "wape"]), 6),
            "transferModelWape": round(float(europe_transfer.loc["model", "wape"]), 6),
            "coveredSlots": int(europe_calendar["has_matched_coverage"].sum()),
            "calendarSlots": len(europe_calendar),
            "independent2021": {
                "testCellPasses": int(independent_selected["test_cell_passes"]),
                "matchedPasses": len(independent_matches),
                "baselineWape": round(float(independent_baseline["wape"]), 6),
                "selectedWape": round(float(independent_selected["wape"]), 6),
                "maeDifferenceCi": [
                    round(float(independent_count_bootstrap["ci_2_5"]), 6),
                    round(float(independent_count_bootstrap["ci_97_5"]), 6),
                ],
            },
            "locked2022": {
                "testCellPasses": int(day7_test_index.loc["legacy", "cell_passes"]),
                "matchedPasses": len(day7_matches),
                "baselineWape": round(float(day7_test_index.loc["fixed_ratio", "wape"]), 6),
                "selectedWape": round(float(day7_test_index.loc["legacy", "wape"]), 6),
                "viirsOnlyWape": round(float(day7_test_index.loc["viirs_only", "wape"]), 6),
                "monotoneViirsOnlyWape": round(float(day7_test_index.loc["monotone_viirs_only", "wape"]), 6),
                "promoted": False,
                "modisOnlyCellPasses": modis_only_cells,
                "modisPositiveCellPasses": modis_positive_cells,
                "modisDetectionsWithoutViirsCell": modis_detections_without_viirs,
                "modisDetections": modis_detections,
            },
            "locked2023": {
                "testCellPasses": int(geometry_test_index.loc["incumbent", "cell_passes"]),
                "matchedPasses": len(geometry_matches),
                "baselineWape": round(float(geometry_test_index.loc["fixed_ratio", "wape"]), 6),
                "incumbentWape": round(float(geometry_test_index.loc["incumbent", "wape"]), 6),
                "geometryWape": round(float(geometry_test_index.loc["geometry_aware", "wape"]), 6),
                "geometryMinusIncumbentMaeCi": [
                    round(float(geometry_bootstrap.iloc[0]["ci_2_5"]), 6),
                    round(geometry_bootstrap_upper, 6),
                ],
                "empiricalIntervalCoverage": round(float(interval_index.loc["all", "empirical_coverage"]), 6),
                "nominalIntervalCoverage": float(interval_index.loc["all", "nominal_coverage"]),
                "promoted": bool(geometry_promoted),
            },
        },
        "teamSpatialPilot": build_qorvex_spatial_payload(),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(output: Path = DEFAULT_OUTPUT) -> Path:
    payload = build_payload()
    # Keep contributor/repository provenance in the reviewed source package and
    # project documentation, but do not expose internal integration metadata in
    # the public dashboard payload.
    public_team_spatial = dict(payload["teamSpatialPilot"])
    public_team_spatial.pop("source", None)
    payload["teamSpatialPilot"] = public_team_spatial
    aoi_payload = build_aoi_payload()
    output.mkdir(parents=True, exist_ok=True)
    data_dir = output / "data"
    data_dir.mkdir(exist_ok=True)
    demo_dir = output / "demo"
    demo_dir.mkdir(exist_ok=True)

    for filename in ("index.html", "styles.css", "app.js", "favicon.svg"):
        shutil.copy2(SITE_SOURCE / filename, output / filename)
    output_fonts = output / "fonts"
    output_fonts.mkdir(exist_ok=True)
    shutil.copy2(FONT_DIR / "Vazirmatn.woff2", output_fonts / "Vazirmatn.woff2")
    shutil.copy2(FONT_DIR / "OFL.txt", output_fonts / "OFL.txt")
    shutil.copy2(PROJECT_DEMO_PATH, demo_dir / PROJECT_DEMO_OUTPUT_NAME)
    output_leaflet = output / "vendor" / "leaflet"
    output_leaflet.mkdir(parents=True, exist_ok=True)
    for filename in ("leaflet.js", "leaflet.css", "LICENSE"):
        shutil.copy2(LEAFLET_DIR / filename, output_leaflet / filename)

    dashboard_path = data_dir / "dashboard.json"
    dashboard_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    team_spatial_path = data_dir / "qorvex-victoria-2024.json"
    team_spatial_path.write_text(
        json.dumps(public_team_spatial, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    victoria_points_path = data_dir / "victoria-2024-points.json"
    victoria_points_path.write_text(
        json.dumps(build_victoria_point_payload(), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    aoi_path = data_dir / "western_iberia_aoi.json"
    aoi_path.write_text(
        json.dumps(aoi_payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    land_path = data_dir / "ne_110m_land.geojson"
    shutil.copy2(LAND_GEOJSON_PATH, land_path)
    shutil.copy2(CALENDAR_PATH, data_dir / "calendar.csv")
    shutil.copy2(INDEPENDENT_METRICS_PATH, data_dir / "independent_2021_metrics.csv")
    shutil.copy2(DAY7_TEST_PATH, data_dir / "day7_2022_locked_test.csv")
    shutil.copy2(OBSERVABILITY_AUDIT_PATH, data_dir / "detection_support_audit.csv")
    shutil.copy2(GEOMETRY_TEST_PATH, data_dir / "geometry_2023_locked_test.csv")
    shutil.copy2(GEOMETRY_INTERVAL_PATH, data_dir / "geometry_2023_interval_coverage.csv")
    shutil.copy2(GEOMETRY_PREDICTIONS_PATH, data_dir / "geometry_2023_cell_pass_predictions.csv")
    shutil.copy2(DAY9_METRICS_PATH, data_dir / "day9_independent_transfer_metrics.csv")
    shutil.copy2(DAY9_BOOTSTRAP_PATH, data_dir / "day9_independent_transfer_bootstrap.csv")
    shutil.copy2(DAY9_DECISION_PATH, data_dir / "day9_independent_transfer_decision.csv")
    shutil.copy2(DAY10_METRICS_PATH, data_dir / "day10_external_metrics.csv")
    shutil.copy2(DAY10_BOOTSTRAP_PATH, data_dir / "day10_external_bootstrap.csv")
    shutil.copy2(DAY10_PERMUTATION_PATH, data_dir / "day10_external_permutation.csv")
    shutil.copy2(DAY10_DECISION_PATH, data_dir / "day10_external_decision.csv")
    shutil.copy2(DAY11_PAIRS_PATH, data_dir / "day11_pair_summary.csv")
    shutil.copy2(DAY12_CLAIMS_PATH, data_dir / "day12_claim_registry.csv")
    shutil.copy2(DAY12_PASSPORT_PATH, data_dir / "evidence-passport.json")
    shutil.copy2(DAY12_GEOJSON_PATH, data_dir / "day12_observation_evidence.geojson")
    shutil.copy2(DAY12_OPENAPI_PATH, data_dir / "openapi.json")
    team_monthly_path = data_dir / "qorvex-victoria-monthly.csv"
    team_cells_path = data_dir / "qorvex-victoria-top-h3.csv"
    team_overlap_path = data_dir / "qorvex-victoria-sensor-overlap.csv"
    shutil.copy2(TEAM_SPATIAL_SOURCE_PATHS[1], team_monthly_path)
    shutil.copy2(TEAM_SPATIAL_SOURCE_PATHS[2], team_cells_path)
    shutil.copy2(TEAM_SPATIAL_SOURCE_PATHS[4], team_overlap_path)
    europe_calendar_path = data_dir / "western_iberia_calendar.csv"
    pd.read_csv(CALENDAR_PATH).query("region_id == 'western_iberia'").to_csv(
        europe_calendar_path, index=False
    )
    europe_pilot_path = data_dir / "western_iberia_pilot.json"
    europe_pilot_path.write_text(
        json.dumps(payload["europePilot"], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sources = [CALENDAR_PATH, METRICS_PATH, BOOTSTRAP_PATH, TRANSFER_PATH,
               SOURCE_INVENTORY_PATH, MATCHES_PATH, RAW_MANIFEST_PATH, REGIONS_PATH,
               LAND_GEOJSON_PATH, FONT_DIR / "Vazirmatn.woff2", FONT_DIR / "OFL.txt",
               INDEPENDENT_METRICS_PATH, INDEPENDENT_BOOTSTRAP_PATH,
               INDEPENDENT_MATCHES_PATH, INDEPENDENT_RAW_MANIFEST_PATH]
    sources.extend([DAY7_TEST_PATH, DAY7_SELECTION_PATH, DAY7_BOOTSTRAP_PATH,
                    DAY7_MATCHES_PATH, DAY7_RAW_MANIFEST_PATH, OBSERVABILITY_AUDIT_PATH,
                    GEOMETRY_TEST_PATH, GEOMETRY_SELECTION_PATH, GEOMETRY_BOOTSTRAP_PATH,
                    GEOMETRY_INTERVAL_PATH, GEOMETRY_PREDICTIONS_PATH, GEOMETRY_MATCHES_PATH,
                    GEOMETRY_RAW_MANIFEST_PATH])
    sources.extend([DAY9_METRICS_PATH, DAY9_BOOTSTRAP_PATH, DAY9_DECISION_PATH,
                    DAY9_MATCHES_PATH, DAY9_RAW_MANIFEST_PATH, DAY9_REGIONS_PATH])
    sources.extend([DAY10_METRICS_PATH, DAY10_BOOTSTRAP_PATH, DAY10_PERMUTATION_PATH,
                    DAY10_DECISION_PATH, DAY10_DIAGNOSTICS_PATH, DAY10_MANIFEST_PATH,
                    DAY10_CONFIG_PATH])
    sources.extend([DAY11_PAIRS_PATH, DAY11_DECISION_PATH, DAY11_MANIFEST_PATH,
                    DAY12_CLAIMS_PATH, DAY12_READINESS_PATH, DAY12_PASSPORT_PATH,
                    DAY12_GEOJSON_PATH, DAY12_OPENAPI_PATH, DAY12_CONFIG_PATH])
    sources.extend(TEAM_SPATIAL_SOURCE_PATHS)
    sources.extend([TEAM_POINTS_PATH, LEAFLET_DIR / "leaflet.js", LEAFLET_DIR / "leaflet.css", LEAFLET_DIR / "LICENSE"])
    manifest = {
        "schemaVersion": 1,
        "generatedFrom": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": _sha256(path)}
            for path in sources
        ],
        "artifacts": {
            "demo/fyrora-space-apps-demo.pdf": _sha256(demo_dir / PROJECT_DEMO_OUTPUT_NAME),
            "dashboard.json": _sha256(dashboard_path),
            "qorvex-victoria-2024.json": _sha256(team_spatial_path),
            "victoria-2024-points.json": _sha256(victoria_points_path),
            "vendor/leaflet/leaflet.js": _sha256(output_leaflet / "leaflet.js"),
            "vendor/leaflet/leaflet.css": _sha256(output_leaflet / "leaflet.css"),
            "vendor/leaflet/LICENSE": _sha256(output_leaflet / "LICENSE"),
            "qorvex-victoria-monthly.csv": _sha256(team_monthly_path),
            "qorvex-victoria-top-h3.csv": _sha256(team_cells_path),
            "qorvex-victoria-sensor-overlap.csv": _sha256(team_overlap_path),
            "western_iberia_aoi.json": _sha256(aoi_path),
            "ne_110m_land.geojson": _sha256(land_path),
            "fonts/Vazirmatn.woff2": _sha256(output_fonts / "Vazirmatn.woff2"),
            "fonts/OFL.txt": _sha256(output_fonts / "OFL.txt"),
            "calendar.csv": _sha256(data_dir / "calendar.csv"),
            "western_iberia_calendar.csv": _sha256(europe_calendar_path),
            "western_iberia_pilot.json": _sha256(europe_pilot_path),
            "independent_2021_metrics.csv": _sha256(data_dir / "independent_2021_metrics.csv"),
            "day7_2022_locked_test.csv": _sha256(data_dir / "day7_2022_locked_test.csv"),
            "detection_support_audit.csv": _sha256(data_dir / "detection_support_audit.csv"),
            "geometry_2023_locked_test.csv": _sha256(data_dir / "geometry_2023_locked_test.csv"),
            "geometry_2023_interval_coverage.csv": _sha256(data_dir / "geometry_2023_interval_coverage.csv"),
            "geometry_2023_cell_pass_predictions.csv": _sha256(data_dir / "geometry_2023_cell_pass_predictions.csv"),
            "day9_independent_transfer_metrics.csv": _sha256(data_dir / "day9_independent_transfer_metrics.csv"),
            "day9_independent_transfer_bootstrap.csv": _sha256(data_dir / "day9_independent_transfer_bootstrap.csv"),
            "day9_independent_transfer_decision.csv": _sha256(data_dir / "day9_independent_transfer_decision.csv"),
            "day10_external_metrics.csv": _sha256(data_dir / "day10_external_metrics.csv"),
            "day10_external_bootstrap.csv": _sha256(data_dir / "day10_external_bootstrap.csv"),
            "day10_external_permutation.csv": _sha256(data_dir / "day10_external_permutation.csv"),
            "day10_external_decision.csv": _sha256(data_dir / "day10_external_decision.csv"),
            "day11_pair_summary.csv": _sha256(data_dir / "day11_pair_summary.csv"),
            "day12_claim_registry.csv": _sha256(data_dir / "day12_claim_registry.csv"),
            "evidence-passport.json": _sha256(data_dir / "evidence-passport.json"),
            "day12_observation_evidence.geojson": _sha256(data_dir / "day12_observation_evidence.geojson"),
            "openapi.json": _sha256(data_dir / "openapi.json"),
        },
    }
    (data_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build(args.output.resolve())
    print(f"Built Fyrora site at {output}")


if __name__ == "__main__":
    main()
