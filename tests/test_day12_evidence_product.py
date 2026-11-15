import hashlib
import json

from pipeline.common import ROOT
from pipeline.day12_evidence_product import build


def test_failed_external_gate_blocks_operational_claim() -> None:
    claims, _, _, bundle = build()
    external = claims.set_index("claim_id").loc["external_outcome"]
    assert external["status"] == "failed_gate"
    assert not bundle["passport"]["operationalReady"]
    assert bundle["decision"]["passed"]


def test_every_claim_hash_matches_real_artifact() -> None:
    claims, _, _, _ = build()
    for claim in claims.itertuples(index=False):
        content = (ROOT / claim.artifact).read_bytes()
        assert hashlib.sha256(content).hexdigest() == claim.artifact_sha256
        assert claim.scope and claim.limitation


def test_geojson_has_both_sensor_states_for_every_cell() -> None:
    _, geojson, _, _ = build()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2340
    for feature in geojson["features"]:
        properties = feature["properties"]
        assert properties["modis_evidence_state"]
        assert properties["viirs_evidence_state"]
        assert feature["geometry"]["type"] == "Point"


def test_openapi_is_static_and_has_no_secret_material() -> None:
    _, _, contract, bundle = build()
    encoded = json.dumps({"contract": contract, "bundle": bundle}).lower()
    assert contract["openapi"] == "3.1.0"
    assert "password" not in encoded
    assert "earthdata_username" not in encoded
    assert set(contract["paths"]) == {
        "/data/evidence-passport.json",
        "/data/day12_observation_evidence.geojson",
        "/data/day12_claim_registry.csv",
    }
