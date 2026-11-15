import h3

from pipeline.team_spatial import SOURCE_COMMIT, build_qorvex_spatial_payload, build_victoria_point_payload


def test_team_spatial_pilot_is_consistent_and_explicitly_descriptive():
    payload = build_qorvex_spatial_payload()

    assert payload["source"]["commit"] == SOURCE_COMMIT == "4829811c19de"
    assert payload["totalRecordedDetections"] == 57_305
    assert payload["activeH3Cells"] == 7_889
    assert sum(row["detection_count"] for row in payload["products"]) == 57_305
    assert sum(
        row["MODIS_SP"] + row["VIIRS_NOAA20_SP"] + row["VIIRS_SNPP_SP"]
        for row in payload["monthly"]
    ) == 57_305
    assert len(payload["monthly"]) == 12
    assert len(payload["topCells"]) == 100
    assert payload["topCells"][0]["count"] == 995
    assert all(h3.is_valid_cell(row["h3"]) for row in payload["topCells"])
    assert all(row["boundary"][0] == row["boundary"][-1] for row in payload["topCells"])
    assert len(payload["pairwiseOverlap"]) == 3
    assert payload["calendarSemantics"]["allowsMissingAsZero"] is False
    assert payload["calendarSemantics"]["anomalyReady"] is False


def test_victoria_point_archive_matches_the_reviewed_three_product_raw_total():
    payload = build_victoria_point_payload()

    assert payload["totalRecords"] == 91_265
    assert payload["sourcePartitions"] == 222
    assert payload["contributingPartitions"] == 221
    assert {key: value["records"] for key, value in payload["products"].items()} == {
        "M": 10_582,
        "N": 39_314,
        "S": 41_369,
    }
    assert len(payload["rows"]) == 91_265
    assert all(0 <= row[0] <= 365 for row in payload["rows"])
    assert all(row[4] in {"M", "N", "S"} and row[5] in {"D", "N"} for row in payload["rows"])
    assert payload["semantics"]["allowsMissingAsZero"] is False
    assert payload["semantics"]["uniqueFireCount"] is False

