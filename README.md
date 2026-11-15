# Fyrora

An evidence-first **QORVEX** prototype for the NASA Space Apps 2026 challenge
**Harmonization of MODIS and VIIRS Hot Spots**.

Created and technically led by **Tara Ali Asgharzadeh**. See
[`CONTRIBUTORS.md`](CONTRIBUTORS.md) for the contribution record and
[`LICENSE`](LICENSE) for reuse terms.

The web product also includes a clearly separated, descriptive Victoria 2024
multi-sensor lab contributed by Aria Fazlollah. It compares filtered MODIS,
S-NPP VIIRS and NOAA-20 VIIRS records and maps the top H3 cells; it is not
presented as harmonized output, a coverage mask, anomaly score or fire count.
See [`docs/qorvex-integration-review.fa.md`](docs/qorvex-integration-review.fa.md).
The same section now includes a date-, overpass- and product-filterable
OpenStreetMap explorer backed by 91,265 frozen 2024 FIRMS Standard Processing
records. The raw rectangular-window map and the 57,305-record
political-boundary-filtered H3 analysis are labeled as different populations.

## Current objective

Build a reproducible scientific bridge between Aqua MODIS and S-NPP VIIRS. The count candidate is evaluated across 2017–2020 and four study windows, including Western Iberia and strict leave-one-region-out transfer tests. The web product now includes a browser-side AOI builder for bounding boxes inside the Western Iberia evidence window, UTC date-range selection, day/night filtering, a same-calendar-day historical-median comparison, and AOI CSV export without exposing the private FIRMS key. A separately specified 2021 Western Iberia check reduces count WAPE from 1.160 to 0.735 on 1,253 cell-passes. Precommitted 2022 and 2023 Western Iberia comparisons retain the incumbent model: geometry-aware features score slightly better in 2023 but fail the frozen uncertainty gate. A frozen 2023 EFFIS outcome check also remains visibly failed: harmonized event-area Spearman is 0.130 with a bootstrap interval crossing zero, despite a significant calendar-shift null test. An eight-pair dual-sensor full-swath audit now distinguishes clear sampling, fire, obscured/non-land and not-observed evidence. The bilingual dashboard exposes an Evidence Passport with scoped, hashed claims and keeps operational readiness false while a blocking gate fails.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Add `FIRMS_MAP_KEY` to `.env`. Never commit that file.

## Commands

```powershell
# Download 2019 MODIS + S-NPP VIIRS standard-processing data.
.\.venv\Scripts\python.exe -m pipeline.fetch_firms --year 2019

# Normalize, aggregate, and generate day-one figures.
.\.venv\Scripts\python.exe -m pipeline.analyze_overlap --year 2019

# For a fresh four-year build, download and normalize every configured region.
# The downloader resumes completed five-day partitions and respects the FIRMS
# 10-minute transaction budget; rerun after the budget resets if it stops.
foreach ($year in 2017..2020) {
  .\.venv\Scripts\python.exe -m pipeline.fetch_firms --year $year
  .\.venv\Scripts\python.exe -m pipeline.analyze_overlap --year $year
}

# Build 10 km Aqua MODIS / S-NPP VIIRS pairs and score the baseline.
.\.venv\Scripts\python.exe -m pipeline.day2_baseline --year 2019 --grid-km 10 --test-start 2019-10-01

# Train, validate, and test the guarded day-three harmonization candidate.
.\.venv\Scripts\python.exe -m pipeline.day3_harmonize --year 2019 --grid-km 10 --validation-start 2019-07-01 --test-start 2019-10-01 --bootstrap 500

# Verify sensitivity to the shared equal-area grid size.
.\.venv\Scripts\python.exe -m pipeline.day3_sensitivity --year 2019 --grids 5 10 25 --bootstrap 100

# Reproduce the four-year holdout, spatial transfer, and calendar-ready output.
.\.venv\Scripts\python.exe -m pipeline.raw_manifest
.\.venv\Scripts\python.exe -m pipeline.day4_multiyear --years 2017 2018 2019 2020 --grid-km 10 --validation-start 2019-01-01 --test-start 2020-01-01 --bootstrap 500

# Reproduce the separately specified 2021 Western Iberia year check.
.\.venv\Scripts\python.exe -m pipeline.fetch_firms --year 2021 --region western_iberia
.\.venv\Scripts\python.exe -m pipeline.analyze_overlap --year 2021 --region western_iberia
.\.venv\Scripts\python.exe -m pipeline.raw_manifest --year 2021 --region western_iberia --output outputs/tables/firms_raw_manifest_2021_western_iberia.csv
.\.venv\Scripts\python.exe -m pipeline.evaluate_2021

# Reproduce the preregistered 2022 candidate comparison after reading its protocol.
.\.venv\Scripts\python.exe -m pipeline.fetch_firms --year 2022 --region western_iberia
.\.venv\Scripts\python.exe -m pipeline.analyze_overlap --year 2022 --region western_iberia
.\.venv\Scripts\python.exe -m pipeline.raw_manifest --year 2022 --region western_iberia --output outputs/tables/firms_raw_manifest_2022_western_iberia.csv
.\.venv\Scripts\python.exe -m pipeline.day7_upgrade

# Reproduce the frozen 2023 geometry and interval test.
.\.venv\Scripts\python.exe -m pipeline.fetch_firms --year 2023 --region western_iberia
.\.venv\Scripts\python.exe -m pipeline.analyze_overlap --year 2023 --region western_iberia
.\.venv\Scripts\python.exe -m pipeline.raw_manifest --year 2023 --region western_iberia --output outputs/tables/firms_raw_manifest_2023_western_iberia.csv
.\.venv\Scripts\python.exe -m pipeline.evaluate_2023

# Audit which MODIS-positive matched cells have no VIIRS detection in the same cell.
.\.venv\Scripts\python.exe -m pipeline.observability_audit

# Reproduce the frozen semi-independent EFFIS event/outcome check after obtaining
# the official effis_layer.zip at data/raw/day10_effis/effis_layer.zip.
.\.venv\Scripts\python.exe -m pipeline.day10_external_validation

# Reproduce the eight-pair MODIS/VIIRS full-swath audit after authenticated
# granules listed in the frozen Day-11 config are present under data/raw/swaths/.
.\.venv\Scripts\python.exe -m pipeline.day11_multiswath_audit

# Build the claim registry, Evidence Passport, GeoJSON and OpenAPI contract.
.\.venv\Scripts\python.exe -m pipeline.day12_evidence_product

# Build the dependency-free Fyrora dashboard into dist/.
.\.venv\Scripts\python.exe -m pipeline.build_site

# Preview the dashboard locally.
.\.venv\Scripts\python.exe -m http.server 8000 --directory dist

# Run tests.
.\.venv\Scripts\python.exe -m pytest
```

The first full-swath observation pilot and its scientific limits are documented in [`docs/day-8-swath-observation.fa.md`](docs/day-8-swath-observation.fa.md).
The sealed three-region 2024 transfer protocol and outcome are in [`docs/day-9-independent-regions-protocol.md`](docs/day-9-independent-regions-protocol.md) and [`docs/day-9-independent-regions-results.fa.md`](docs/day-9-independent-regions-results.fa.md).
The frozen EFFIS protocol and its failed-but-informative outcome are in [`docs/day-10-external-validation-protocol.md`](docs/day-10-external-validation-protocol.md) and [`docs/day-10-external-validation-results.fa.md`](docs/day-10-external-validation-results.fa.md).
The dual-sensor swath audit is in [`docs/day-11-multiswath-protocol.md`](docs/day-11-multiswath-protocol.md) and [`docs/day-11-multiswath-results.fa.md`](docs/day-11-multiswath-results.fa.md). The evidence-product contract and outcome are in [`docs/day-12-product-readiness-protocol.md`](docs/day-12-product-readiness-protocol.md) and [`docs/day-12-evidence-product-results.fa.md`](docs/day-12-evidence-product-results.fa.md).

Research notes are in [`docs/research-and-winning-strategy.fa.md`](docs/research-and-winning-strategy.fa.md). The original three-region science is recorded in [`docs/day-4-results.fa.md`](docs/day-4-results.fa.md); the current four-region evidence and eligibility caveat are in [`docs/day-7-europe-results.fa.md`](docs/day-7-europe-results.fa.md). The 2021 protocol/outcome are in [`docs/independent-2021-protocol.md`](docs/independent-2021-protocol.md) and [`docs/independent-2021-results.fa.md`](docs/independent-2021-results.fa.md). The 2022 comparison is in [`docs/day-7-2022-results.fa.md`](docs/day-7-2022-results.fa.md); the frozen 2023 geometry and uncertainty test is in [`docs/2023-geometry-and-uncertainty-protocol.md`](docs/2023-geometry-and-uncertainty-protocol.md) and [`docs/2023-geometry-and-uncertainty-results.fa.md`](docs/2023-geometry-and-uncertainty-results.fa.md). The sensor-support audit and global readiness gates are in [`docs/global-readiness-and-sensor-support.fa.md`](docs/global-readiness-and-sensor-support.fa.md). The European product and startup validation gates are in [`docs/europe-product-strategy.fa.md`](docs/europe-product-strategy.fa.md). Copy-ready project text, timed demo scripts, architecture, scorecard, and the final checklist live in [`submission/`](submission/README.md). Deployment limits are summarized in [`docs/model-card.md`](docs/model-card.md).

The compact paired-cell and scored-holdout artifacts required by the site build
and core tests are tracked in `data/processed/`. Larger source and intermediate
partitions remain excluded; their hashes are recorded in the committed
manifests.

The official-event boundary is recorded in [`PREEXISTING_WORK.md`](PREEXISTING_WORK.md) and [`HACKATHON_WORKLOG.md`](HACKATHON_WORKLOG.md). These files distinguish the research prototype from work completed on the 2026 hackathon branch.

