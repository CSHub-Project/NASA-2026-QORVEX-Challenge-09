# Changelog

## Day 12 — Evidence Passport and product boundary

- Added a hashed claim registry with categorical evidence grades A/B/C.
- Added a 2,340-cell dual-sensor GeoJSON and an OpenAPI 3.1 static contract.
- Enforced `operationalReady=false` while the external-outcome gate is failed.
- Added a bilingual Evidence Passport dashboard section and machine-readable downloads.

## Day 11 — dual-sensor full-swath evidence

- Froze and passed an eight-pair Aqua MODIS / S-NPP VIIRS observation audit.
- Added HDF4 MODIS support through `pyhdf` and retained HDF5 VIIRS support.
- Exported explicit fire, clear-sampled, obscured/non-land and not-observed states.
- Added SHA-256 provenance for all 16 protected NASA granules and semantic tests.

All notable project changes are recorded here. Versions follow Semantic Versioning while the prototype is under active development.

## [Unreleased]

### Added

- Official-event AOI workflow for a user-entered Western Iberia bounding box, UTC date range, and day/night overpass, with a coverage-aware daily chart and downloadable CSV.
- Compact browser-side cell-day evidence artifact generated from historical Aqua MODIS observations and frozen 2020 VIIRS-to-MODIS-equivalent predictions.
- Coverage-matched historical-median comparison that excludes unsupported selected-year days instead of treating missing support as zero activity.
- Transparent pre-existing-work boundary and an official-event worklog without rewriting Git history.
- Frozen semi-independent EFFIS outcome validation for 201 Western Iberian 2023 burned-area events. The preregistered overall gate failed: harmonized event-area Spearman was 0.130 (2,000-event bootstrap 95% interval [-0.019, 0.272]), below the frozen 0.30 threshold, while a shared circular-calendar null test passed (p=0.006) and association loss versus raw VIIRS stayed within tolerance. A fractional-overlap sensitivity produced the same conclusion. The failed gate is exposed in the dashboard and submission copy rather than tuned away.
- Locked 2024 independent-region transfer test across Southern African savanna, Eastern Siberian boreal forest and Southeast Australia: 444 hashed FIRMS partitions, 798,901 observations, 1,175 matched passes and 126,989 scored cell-passes. All preregistered gates passed; pooled count WAPE improved from 1.369 to 1.084 and date-block model-minus-baseline MAE CI was [-0.187, -0.144]. The dashboard and report preserve the high absolute error boundary.
- Day-eight full-swath VIIRS observation pilot for Western Iberia: CMR inventory for VNP14IMG/VNP03IMG and MYD14/MYD03, authenticated range-checked download with SHA-256 manifest, pixel-class aggregation on the shared 10 km grid, and a four-pixel FIRMS cross-check (maximum geolocation separation 0.53 m). The 982 clear-sampled no-detection cells are explicitly limited to one observed pass, not a fire-free-area claim.
- A frozen 2023 Western Iberia geometry-aware count experiment and day/night 90% empirical intervals, with 146 newly hashed FIRMS partitions, 128 matched passes, 879 test cell-passes, downloadable metrics/intervals/cell predictions, and a dashboard evidence card. The candidate's small WAPE gain failed the preregistered bootstrap promotion gate; empirical interval coverage was 89.5%, below nominal 90%.
- Extended the sensor-support audit through 2023, including the 145/362 MODIS-positive matched cells with no VIIRS detection in the same cell.
- Six-year matched-pass sensor-support audit with a downloadable CSV and dashboard evidence card. In Western Iberia 2022, 245/739 MODIS-positive cell-passes have no VIIRS detection in the same cell, exposing a deployment gap hidden by union-cell WAPE. Added a global-readiness gate document grounded in recent observation-operator research.
- A preregistered 2022 Western Iberia comparison of fixed ratio, incumbent, VIIRS-only and monotone VIIRS-only Poisson count models; 146 hashed raw partitions, 182 matched passes, 1,722 cell-passes, day/night metrics and descriptive date-block bootstrap. The incumbent remains accepted; no candidate promoted. A fourth dashboard evidence card and downloadable complete result table expose the outcome.
- A predeclared, independently scored 2021 Western Iberia year test, with 146 raw FIRMS partition hashes, 161 matched detection-derived passes, CSV metrics and a dashboard evidence card.
- Western Iberia as a fourth, genuinely European NASA FIRMS study window with four years of observations, dashboard calendar, separate CSV, and explicit 2020/leave-one-region-out evidence.
- SHA-256 inventory for 2,344 raw FIRMS partitions, a committed source-observation inventory, and dynamically derived dashboard scale figures.
- European customer-discovery strategy and an English partner one-pager with scientific and commercial acceptance gates.
- A day-seven results report documenting the new European scores, percentile rendering correction, and pre-hackathon eligibility question.
- Complete 2019 scientific-overlap acquisition: 438 five-day FIRMS partitions covering three regions and two Standard Processing sources.
- Six versioned evidence figures for monthly raw hotspot count and FRP sum.
- Quality-control results for 534,703 observations, with complete sensor and day/night coverage.
- Day-two 10 km Lambert equal-area grid pairing for Aqua MODIS and S-NPP VIIRS.
- Leakage-safe fixed-ratio count and FRP baselines with an Oct–Dec temporal holdout.
- Holdout metrics for MAE, median absolute error, signed bias, and Spearman correlation.
- Contemporaneous Aqua MODIS / S-NPP VIIRS pass matching with a maximum 60-minute separation.
- Nonlinear Poisson-loss harmonization candidates using a 3×3 VIIRS neighborhood, scan footprint, season, latitude, region, day/night, and pass-time difference.
- Three-way temporal protocol: Jan–Jun fit, Jul–Sep method selection, and untouched Oct–Dec test.
- Date-block bootstrap intervals with 500 replicates and 5/10/25 km grid sensitivity.
- Complete 2017–2020 overlap corpus with 2,523,257 observations and exact raw-partition coverage.
- Full-year 2020 holdout after fitting on 2017–2018 and method selection on 2019.
- Strict leave-one-region-out transfer tests with the region feature removed.
- Coverage-aware calendar output with robust monthly percentiles and MAD-based anomaly scores.
- FIRMS downloader transaction-budget guard, sanitized failures, and resumable sequential acquisition.
- Fyrora bilingual (English/Persian) dashboard with RTL support, coverage-aware anomaly calendar, validation comparisons, spatial-transfer evidence, and filtered CSV export.
- Reproducible static-site builder with schema guards, SHA-256 provenance manifest, and machine-readable JSON endpoint.
- A dependency-free, offline-capable static build output.
- A bilingual five-step Judge Mode, in-product architecture lineage, and five-criterion decision brief.
- A complete submission kit with English project-page copy, timed English/Persian demo scripts, architecture, judge scorecard, and final Persian checklist.

### Changed

- The calendar now applies the 0–100 percentile scale correctly and renders historical days without an anomaly score in a neutral class.
- Missing cells are described as lacking a matched detection-derived pass; full satellite observation coverage is not inferred from point exports.
- Normalization rejects incomplete raw partition sets, and the Windows console prints an ASCII summary rather than failing on a Unicode table.
- Acquisition timestamps are now stored as timezone-aware UTC datetimes.
- FIRMS downloads now retry transient network and HTTP failures with exponential backoff and a longer read timeout.

### Verified

Current four-region run:

- Independent 2021 Western Iberia count WAPE: 1.160 fixed ratio to 0.735 selected method (36.7% reduction) on 1,253 cell-passes; day and night both improve; date-block MAE-difference 95% interval [-0.285, -0.227].
- Four-region run: 2,587,488 observations, 5,314 matched passes, 476,937 cell-passes, and 11,688 calendar rows.
- 2020 count WAPE: 1.224 fixed ratio to 0.832 selected model (32.0% reduction); all eight region/day-night subgroups improve.
- Western Iberia 2020 count WAPE: 1.071 to 0.708; strict unseen-Europe transfer: 1.009 to 0.719 (28.7% reduction).
- The 500-replicate date-block MAE difference interval is [-0.269, -0.229]; FRP remains experimental because the Western Iberia night subgroup worsens.

Earlier three-region development run (retained as history):

- Observation dates span 2019-01-01 through 2019-12-31, with zero null acquisition datetimes.
- All six region/source partitions contain the expected 73 request files.
- Day-two pairing preserves one-sided non-detections instead of dropping them: 124,794 cell-days total, of which 17.92% contain detections from both sensors.
- The fixed ratio approximately follows regional monthly totals but fails spatial-temporal ranking on holdout count data (overall Spearman -0.119), establishing a meaningful baseline to beat.
- 1,069 contemporaneous passes were matched; median separation is 25 minutes and the maximum is 58 minutes.
- On the untouched day-three holdout, count MAE fell 35.3% (0.596 to 0.385) and Spearman rose from -0.159 to 0.572.
- The 500-replicate date-block bootstrap interval for count MAE improvement is [-0.227, -0.193], entirely below zero.
- Count improvement persists at 5, 10, and 25 km. FRP is not yet accepted for operational use because subgroup and 25 km sensitivity are unstable.
- On the untouched 2020 year holdout, count MAE fell 32.0% and Spearman increased from 0.045 to 0.635.
- Count WAPE improved for every unseen-region transfer: Amazon 37.0%, Northern California 11.0%, and Hyrcanian 44.9%.
- All count region/day-night subgroups improved on 2020; FRP remains experimental because Northern California night still degrades.
- Calendar gaps remain null with an explicit no-coverage flag; they are never converted to zero activity.
- Dashboard build contract, JavaScript syntax, English/Persian interaction, RTL layout, and browser rendering were verified; the automated suite now contains 14 passing tests.

### Next

- Publish only the reviewed judge-facing build after the final demo, video, and project page are ready.
- Record and caption the final three-minute demo, then complete the official project page during the submission window.

## [0.1.0] - 2026-11-05

### Added

- Reproducible Python project configuration and isolated-environment instructions.
- Three versioned pilot regions: Hyrcanian Forests, Northern California, and the Amazon Arc of Deforestation.
- FIRMS Standard Processing downloader with five-day request chunking and resumable files.
- Normalization of acquisition date/time into a UTC datetime.
- Explicit MODIS/VIIRS and day/night grouping.
- Monthly raw hotspot-count and FRP aggregation and plotting pipeline.
- Observation and monthly-summary schema documentation.
- Quantitative day-one completion and future model-success criteria.
- Automated tests for bounding boxes and full-year chunk coverage.
- Research and judging strategy in Persian.

### Verified

- `pytest`: 2 tests passed on Python 3.12.
- Python source compilation completed without syntax errors.

### Known environment issue

- A local `.venv` was created, but dependency installation from PyPI was blocked by network timeout. The system Python already contains the minimum day-one packages (`httpx`, `polars`, `pandas`, `matplotlib`, `seaborn`, `pytest`, and `python-dotenv`), so access and data work can continue while the isolated environment is retried later.

