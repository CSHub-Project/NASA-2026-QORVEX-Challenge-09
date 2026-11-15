"""Build the Day-12 Evidence Passport, GeoJSON and static API contract."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pandas as pd

from pipeline.common import ROOT


CONFIG = ROOT / "configs" / "day12_product_readiness.json"
TABLES = ROOT / "outputs" / "tables"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def gate_value(path: Path, gate: str = "overall", *, column: str | None = None) -> bool:
    frame = pd.read_csv(path)
    if column is not None:
        if len(frame) != 1 or column not in frame:
            raise ValueError(f"Expected one decision row with {column!r} in {path}")
        return bool(frame.iloc[0][column])
    rows = frame.loc[frame["gate"] == gate, "passed"]
    if len(rows) != 1:
        raise ValueError(f"Expected one {gate!r} gate in {path}")
    return bool(rows.iloc[0])


def claim_registry() -> pd.DataFrame:
    day9 = TABLES / "day9_independent_transfer_decision.csv"
    day10 = TABLES / "day10_external_decision.csv"
    day11 = TABLES / "day11_decision.csv"
    claims = [
        {
            "claim_id": "full_swath_missingness",
            "claim": "Fyrora distinguishes clear sampling, fire, obscured/non-land and not-observed cells for the audited day.",
            "status": "supported" if gate_value(day11) else "not_supported",
            "evidence_grade": "A",
            "scope": "Western Iberia; 2023-08-06; four Aqua MODIS and four S-NPP VIIRS acquisitions",
            "limitation": "One-day observation-support audit; not probability of detection or global completeness",
            "artifact": "outputs/tables/day11_decision.csv",
        },
        {
            "claim_id": "independent_transfer",
            "claim": "The frozen harmonization method passed its precommitted 2024 three-region transfer gate.",
            "status": "supported" if gate_value(day9, column="external_transfer_gate_passed") else "not_supported",
            "evidence_grade": "B",
            "scope": "Three unseen 2024 study windows; fixed model and thresholds",
            "limitation": "Two regions still have WAPE above 1; this does not establish global accuracy",
            "artifact": "outputs/tables/day9_independent_transfer_decision.csv",
        },
        {
            "claim_id": "external_outcome",
            "claim": "Harmonized activity is strongly associated with EFFIS mapped burned area.",
            "status": "supported" if gate_value(day10, column="external_outcome_gate_passed") else "failed_gate",
            "evidence_grade": "C",
            "scope": "201 eligible Western Iberia EFFIS events in 2023",
            "limitation": "Precommitted association threshold and bootstrap lower-bound gates failed",
            "artifact": "outputs/tables/day10_external_decision.csv",
        },
        {
            "claim_id": "operational_readiness",
            "claim": "Fyrora is ready for live operational incident alerting.",
            "status": "not_supported",
            "evidence_grade": "C",
            "scope": "Current research prototype",
            "limitation": "No live latency/SLA test, multi-season swath validation or passed external-outcome gate",
            "artifact": "configs/day12_product_readiness.json",
        },
    ]
    frame = pd.DataFrame(claims)
    frame["artifact_sha256"] = frame["artifact"].map(lambda value: digest(ROOT / value))
    return frame


def evidence_geojson(daily: pd.DataFrame) -> dict[str, object]:
    index = ["cell_x", "cell_y", "center_lon", "center_lat"]
    if set(daily["sensor"]) != {"MODIS", "VIIRS"}:
        raise ValueError("Day-11 daily evidence must contain MODIS and VIIRS")
    properties = ["not_processed", "water", "cloud", "clear_nonfire_land", "unknown", "fire", "evidence_state"]
    wide = daily.pivot(index=index, columns="sensor", values=properties).reset_index()
    wide.columns = [
        column if isinstance(column, str) else
        (column[0] if not column[1] else f"{column[1].lower()}_{column[0]}")
        for column in wide.columns
    ]
    features = []
    for row in wide.to_dict(orient="records"):
        lon = round(float(row.pop("center_lon")), 6)
        lat = round(float(row.pop("center_lat")), 6)
        clean: dict[str, object] = {}
        for key, value in row.items():
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            clean[key] = value
        features.append({
            "type": "Feature",
            "id": f"{clean['cell_x']}:{clean['cell_y']}",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": clean,
        })
    return {
        "type": "FeatureCollection",
        "name": "Fyrora Day-11 dual-sensor observation evidence",
        "metadata": {
            "date": "2023-08-06", "region": "western_iberia", "gridKm": 10,
            "geometryMeaning": "Equal-area cell center; not a fire perimeter",
        },
        "features": features,
    }


def openapi_contract() -> dict[str, object]:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Fyrora Evidence API", "version": "0.12.0",
            "description": "Static, versioned research evidence endpoints. Not a live incident API.",
        },
        "servers": [{"url": ".", "description": "Dashboard-relative static files"}],
        "paths": {
            "/data/evidence-passport.json": {"get": {"summary": "Product readiness and claim provenance", "responses": {"200": {"description": "Evidence Passport JSON"}}}},
            "/data/day12_observation_evidence.geojson": {"get": {"summary": "Dual-sensor daily observation states", "responses": {"200": {"description": "GeoJSON FeatureCollection"}}}},
            "/data/day12_claim_registry.csv": {"get": {"summary": "Auditable claim registry", "responses": {"200": {"description": "UTF-8 CSV"}}}},
        },
    }


def build() -> tuple[pd.DataFrame, dict[str, object], dict[str, object], dict[str, object]]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    claims = claim_registry()
    daily = pd.read_csv(TABLES / "day11_daily_sensor_evidence.csv")
    geojson = evidence_geojson(daily)
    blockers = claims[(claims["status"] != "supported") & claims["claim_id"].isin([
        "external_outcome", "operational_readiness"
    ])]
    readiness = {
        "product": config["product"],
        "releaseStage": config["release_stage"],
        "operationalReady": False if len(blockers) else True,
        "supportedClaims": int((claims["status"] == "supported").sum()),
        "failedOrUnsupportedClaims": int((claims["status"] != "supported").sum()),
        "blockingGates": config["blocking_gates"],
        "decision": "research_preview_only" if len(blockers) else "candidate_operational_pilot",
        "claims": claims.to_dict(orient="records"),
        "safetyBoundary": "Research and planning evidence; not a live alert, burned-area product or emergency-service replacement.",
    }
    decision = {
        "operational_ready": readiness["operationalReady"],
        "release_stage": readiness["releaseStage"],
        "blocking_claims": blockers["claim_id"].tolist(),
        "all_claims_have_hash": bool(claims["artifact_sha256"].str.len().eq(64).all()),
        "geojson_features": len(geojson["features"]),
        "passed": bool(
            not readiness["operationalReady"]
            and claims["artifact_sha256"].str.len().eq(64).all()
            and len(geojson["features"]) == 2340
        ),
    }
    return claims, geojson, openapi_contract(), {"passport": readiness, "decision": decision}


def main() -> None:
    claims, geojson, openapi, bundle = build()
    claims.to_csv(TABLES / "day12_claim_registry.csv", index=False)
    (TABLES / "day12_readiness_decision.json").write_text(
        json.dumps(bundle["decision"], indent=2), encoding="utf-8"
    )
    (TABLES / "day12_evidence_passport.json").write_text(
        json.dumps(bundle["passport"], indent=2), encoding="utf-8"
    )
    (TABLES / "day12_observation_evidence.geojson").write_text(
        json.dumps(geojson, separators=(",", ":")), encoding="utf-8"
    )
    (TABLES / "day12_openapi.json").write_text(
        json.dumps(openapi, indent=2), encoding="utf-8"
    )
    dist = ROOT / "dist" / "data"
    dist.mkdir(parents=True, exist_ok=True)
    claims.to_csv(dist / "day12_claim_registry.csv", index=False)
    (dist / "day12_observation_evidence.geojson").write_bytes((TABLES / "day12_observation_evidence.geojson").read_bytes())
    (dist / "evidence-passport.json").write_bytes((TABLES / "day12_evidence_passport.json").read_bytes())
    (dist / "openapi.json").write_bytes((TABLES / "day12_openapi.json").read_bytes())
    print(json.dumps(bundle["decision"], indent=2))


if __name__ == "__main__":
    main()
