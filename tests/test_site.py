import hashlib
import json

from pipeline.build_site import build, build_aoi_payload, build_payload


def test_aoi_payload_is_real_bounded_and_coverage_aware():
    payload = build_aoi_payload()

    assert payload["scope"]["bbox"] == [-9.5, 37.0, -5.5, 43.0]
    assert payload["scope"]["startDate"] == "2017-01-01"
    assert payload["scope"]["endDate"] == "2020-12-31"
    assert len(payload["rows"]) > 8_000
    assert {row[1] for row in payload["rows"]} == {"D", "N"}
    assert {row[6] for row in payload["rows"]} == {"M", "H"}
    assert all(-9.5 <= row[2] <= -5.5 and 37 <= row[3] <= 43 for row in payload["rows"])
    assert all(row[4] >= 0 and row[5] >= 1 for row in payload["rows"])


def test_dashboard_payload_preserves_coverage_semantics():
    payload = build_payload()

    assert payload["meta"]["calendarRows"] == 11688
    assert payload["meta"]["years"] == [2017, 2018, 2019, 2020]
    assert {region["id"] for region in payload["regions"]} == {
        "amazon_arc",
        "california_north",
        "hyrcanian",
        "western_iberia",
    }

    rows = payload["calendar"]
    missing_rows = [row for row in rows if not row[5]]
    covered_rows = [row for row in rows if row[5]]
    assert missing_rows
    assert all(row[3] is None for row in missing_rows)
    assert all(row[3] is not None and row[3] >= 0 for row in covered_rows)
    team = payload["teamSpatialPilot"]
    assert team["totalRecordedDetections"] == 57_305
    assert team["calendarSemantics"]["allowsMissingAsZero"] is False


def test_dashboard_reports_reviewed_holdout_evidence():
    payload = build_payload()
    metrics = payload["metrics"]
    baseline = next(
        row
        for row in metrics
        if row["model"] == "baseline"
        and row["region_id"] == "all"
        and row["daynight"] == "all"
        and row["metric"] == "count"
    )
    selected = next(
        row
        for row in metrics
        if row["model"] == "selected"
        and row["region_id"] == "all"
        and row["daynight"] == "all"
        and row["metric"] == "count"
    )

    assert selected["wape"] < baseline["wape"]
    expected_gain = round((baseline["wape"] - selected["wape"]) / baseline["wape"] * 100, 1)
    assert payload["meta"]["countWapeImprovementPct"] == expected_gain
    assert len(payload["spatialTransfer"]) == 8
    assert payload["meta"]["observations"] == sum(row["observations"] for row in payload["sourceInventory"])
    europe = payload["europePilot"]
    assert europe["regionId"] == "western_iberia"
    assert europe["calendarSlots"] == 732
    assert europe["testCellPasses"] > 0
    independent = europe["independent2021"]
    assert independent["testCellPasses"] == 1253
    assert independent["baselineWape"] > independent["selectedWape"]
    assert independent["maeDifferenceCi"][1] < 0
    locked = europe["locked2022"]
    assert locked["testCellPasses"] == 1722
    assert locked["baselineWape"] > locked["selectedWape"]
    assert locked["viirsOnlyWape"] > locked["selectedWape"]
    assert locked["monotoneViirsOnlyWape"] > locked["selectedWape"]
    assert locked["promoted"] is False
    assert locked["modisOnlyCellPasses"] == 245
    assert locked["modisPositiveCellPasses"] == 739
    assert locked["modisDetectionsWithoutViirsCell"] == 401
    assert locked["modisDetections"] == 1948
    locked2023 = europe["locked2023"]
    assert locked2023["testCellPasses"] == 879
    assert locked2023["baselineWape"] > locked2023["incumbentWape"]
    assert locked2023["geometryWape"] < locked2023["incumbentWape"]
    assert locked2023["geometryMinusIncumbentMaeCi"][1] > 0
    assert locked2023["empiricalIntervalCoverage"] < locked2023["nominalIntervalCoverage"]
    assert locked2023["promoted"] is False
    day9 = payload["independentTransfer2024"]
    assert day9["gatePassed"] is True
    assert day9["matchedPasses"] == 1175
    overall_day9 = {
        row["method"]: row for row in day9["metrics"]
        if row["region_id"] == "all" and row["daynight"] == "all"
    }
    assert overall_day9["model"]["wape"] < overall_day9["baseline"]["wape"]
    assert day9["bootstrap"][0]["ci_97_5"] < 0
    day10 = payload["externalOutcome2023"]
    assert day10["eligibleEvents"] == 201
    assert day10["gatePassed"] is False
    assert day10["permutationP"] <= 0.05
    primary_day10 = {
        row["method"]: row for row in day10["metrics"]
        if row["analysis"] == "primary_many_to_many"
    }
    assert primary_day10[day10["selectedMethod"]]["spearman"] < 0.3


def test_static_build_is_self_contained_and_hashed(tmp_path):
    output = build(tmp_path / "dist")

    for relative in (
        "index.html",
        "favicon.svg",
        "styles.css",
        "app.js",
        "translations-tr.js",
        "data/dashboard.json",
        "data/western_iberia_aoi.json",
        "data/calendar.csv",
        "data/manifest.json",
        "data/western_iberia_calendar.csv",
        "data/western_iberia_pilot.json",
        "data/qorvex-victoria-2024.json",
        "data/qorvex-victoria-monthly.csv",
        "data/qorvex-victoria-top-h3.csv",
        "data/qorvex-victoria-sensor-overlap.csv",
        "data/victoria-2024-points.json",
        "vendor/leaflet/leaflet.js",
        "vendor/leaflet/leaflet.css",
        "vendor/leaflet/LICENSE",
        "data/independent_2021_metrics.csv",
        "data/day7_2022_locked_test.csv",
        "data/detection_support_audit.csv",
        "data/geometry_2023_locked_test.csv",
        "data/geometry_2023_interval_coverage.csv",
        "data/geometry_2023_cell_pass_predictions.csv",
        "data/day9_independent_transfer_metrics.csv",
        "data/day9_independent_transfer_bootstrap.csv",
        "data/day9_independent_transfer_decision.csv",
        "data/day10_external_metrics.csv",
        "data/day10_external_bootstrap.csv",
        "data/day10_external_permutation.csv",
        "data/day10_external_decision.csv",
        "demo/fyrora-space-apps-demo.pdf",
    ):
        assert (output / relative).is_file()

    manifest = json.loads((output / "data" / "manifest.json").read_text(encoding="utf-8"))
    dashboard_bytes = (output / "data" / "dashboard.json").read_bytes()
    assert manifest["artifacts"]["dashboard.json"] == hashlib.sha256(dashboard_bytes).hexdigest()
    aoi_bytes = (output / "data" / "western_iberia_aoi.json").read_bytes()
    assert manifest["artifacts"]["western_iberia_aoi.json"] == hashlib.sha256(aoi_bytes).hexdigest()
    europe_bytes = (output / "data" / "western_iberia_calendar.csv").read_bytes()
    assert manifest["artifacts"]["western_iberia_calendar.csv"] == hashlib.sha256(europe_bytes).hexdigest()
    demo_bytes = (output / "demo" / "fyrora-space-apps-demo.pdf").read_bytes()
    assert manifest["artifacts"]["demo/fyrora-space-apps-demo.pdf"] == hashlib.sha256(demo_bytes).hexdigest()
    team_bytes = (output / "data" / "qorvex-victoria-2024.json").read_bytes()
    assert manifest["artifacts"]["qorvex-victoria-2024.json"] == hashlib.sha256(team_bytes).hexdigest()
    points_bytes = (output / "data" / "victoria-2024-points.json").read_bytes()
    assert manifest["artifacts"]["victoria-2024-points.json"] == hashlib.sha256(points_bytes).hexdigest()
    assert any("firms_raw_manifest_2021_western_iberia.csv" in row["path"] for row in manifest["generatedFrom"])
    assert any("firms_raw_manifest_2022_western_iberia.csv" in row["path"] for row in manifest["generatedFrom"])
    assert any("firms_raw_manifest_2023_western_iberia.csv" in row["path"] for row in manifest["generatedFrom"])
    assert any("day9_firms_raw_manifest_2024.csv" in row["path"] for row in manifest["generatedFrom"])
    assert any("day10_effis_manifest.csv" in row["path"] for row in manifest["generatedFrom"])
    assert "https://" not in (output / "styles.css").read_text(encoding="utf-8")
    assert (output / "fonts" / "Vazirmatn.woff2").stat().st_size > 100_000
    assert (output / "fonts" / "OFL.txt").exists()
    styles = (output / "styles.css").read_text(encoding="utf-8")
    turkish = (output / "translations-tr.js").read_text(encoding="utf-8")
    assert 'html[lang="tr"] body' in styles
    assert 'dir="rtl"' not in styles
    assert "Türkçe" in (output / "index.html").read_text(encoding="utf-8")
    assert "Batı İberya" in turkish
    assert "FYRORA_TR" in turkish


def test_judge_mode_and_scientific_sources_ship_in_static_build(tmp_path):
    output = build(tmp_path / "dist")
    html = (output / "index.html").read_text(encoding="utf-8")
    script = (output / "app.js").read_text(encoding="utf-8")

    assert 'id="judge-trigger"' in html
    assert 'id="judge-tour"' in html
    assert 'id="architecture"' in html
    assert "spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots" in html
    assert "www.earthdata.nasa.gov/data/tools/firms" in html
    assert 'id="theme-toggle"' in html
    assert 'id="map-active-bbox"' in html
    assert 'id="map-time-slice"' in html
    assert "SPATIOTEMPORAL VIEW" in html
    assert "function applyTheme" in script
    assert 'localStorage.setItem("fyrora-theme"' in script
    assert "activeRegion.bbox.join" in script
    assert '<canvas class="globe"' in html
    assert 'fetch("data/ne_110m_land.geojson")' in script
    assert "function projectGlobe" in script
    assert "requestAnimationFrame(drawGlobe)" in script
    assert "state.year - 2017" in script
    assert "mockData" not in script
    assert "sampleData" not in script
    assert "applyLanguage();\n    runAoi();" not in script
    assert "firelens_" not in script
    assert "Fyrora" in html
    assert "FireLens" not in html
    assert "function startJudgeTour" in script
    assert 'id="sensor-lab"' in html
    assert "function renderTeamSensorLab" in script
    assert 'id="victoria-map"' in html
    assert "tile.openstreetmap.org/{z}/{x}/{y}.png" in script
    assert "OpenStreetMap contributors" in script
    assert "function loadVictoriaExplorer" in script
    assert "new WebSocket" in script
    assert "setInterval(checkBuild, 5000)" in script
    assert "Integrated from Aria" not in html
    assert "Integrated from Aria" not in script
    assert "4829811c19de" not in (output / "data" / "dashboard.json").read_text(encoding="utf-8")
    assert "4829811c19de" not in (output / "data" / "qorvex-victoria-2024.json").read_text(encoding="utf-8")
    assert "mockData" not in script
    assert "Western Iberia validation" in script
    assert 'id="independent-transfer"' in html
    assert "function renderDay9" in script
    assert 'id="external-outcome"' in html
    assert "function renderDay10" in script
    assert 'id="aoi-builder"' in html
    assert "function aggregateAoi" in script
    assert 'id="aoi-run"' in html
    assert 'id="aoi-status"' in html
    assert 'scrollIntoView({ behavior: "smooth", block: "center" })' in script
    assert 'state.lang === "en" ? "tr" : "en"' in script
    assert 'state.lang === "fa"' not in script
    assert "row.coverage && row.historicalMedian !== null" in script
    assert "www.earthdata.nasa.gov/data/tools/firms" in html
    assert 'id="guide"' in html
    assert 'id="team"' in html
    assert "How to inspect Fyrora" in html
    assert "QORVEX team contributors" in html
    assert "Tara Ali Asgharzadeh" in html
    assert "Aria Fazlollah" in html
    assert "Melika Ostad Jafari" in html
    assert "Mobina Amrollahi" in html
