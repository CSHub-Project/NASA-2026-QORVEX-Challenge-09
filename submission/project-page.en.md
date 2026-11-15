# Fyrora — project-page copy

## Title

Fyrora — One Fire Record Across Two Satellite Generations

## Tagline

A matched-pass-aware burning-activity calendar that harmonizes VIIRS into a MODIS-equivalent historical signal, with a tested European pilot.

## Short summary

MODIS and VIIRS have observed active fires across two satellite generations, but differences in resolution, sensitivity, and observation opportunity mean their hotspot counts cannot be compared directly. Fyrora creates a reproducible bridge between Aqua MODIS and S-NPP VIIRS, then turns that bridge into a bilingual, accessible burning-activity calendar. The model is fitted on 2017–2018 and selected on 2019; 2020 is excluded from both steps and used for temporal evaluation. Count WAPE improves by 32.0% over a fixed-ratio baseline. A locked 2024 test, opened only after its three new regions and gates were committed, improves pooled WAPE from 1.369 to 1.084 across Southern African savanna, Eastern Siberian boreal forest and Southeast Australia. Unsupported matched-detection days remain null and visibly hatched.

## The problem

Fire managers, land managers, and scientists need a continuous historical view of burning activity. A sensor transition can look like a change in fire activity even when it is only a change in spatial resolution, sensitivity, or acquisition opportunity. Simply concatenating MODIS and VIIRS detections therefore risks manufacturing a false trend.

## Our solution

Fyrora pairs contemporaneous detection-derived Aqua MODIS and S-NPP VIIRS passes, aggregates both sensors onto the same 10 km equal-area grid, and learns a guarded count mapping from VIIRS context to MODIS-equivalent activity. The web application lets a user choose a pilot region, year, and day/night overpass; inspect a 2020 historical-percentile calendar; distinguish an unsupported matched pass from a zero on a supported pass; inspect validation evidence; and export the selected view as CSV. An interactive AOI builder additionally accepts a validated bounding box inside Western Iberia, a UTC date range, and day/night selection, then calculates a coverage-aware daily series, compares it with the same-calendar-day median in other available years, and exports the AOI result without exposing the FIRMS key.

The prototype includes four contrasting study windows: the Hyrcanian Forests, Northern California, the Amazon Arc of Deforestation, and Western Iberia across Portugal and western Spain. The European window can be explored directly and downloaded as a separate CSV.

## How we built it

- NASA FIRMS standard-processing Aqua MODIS and S-NPP VIIRS data;
- 2,587,488 source observations from 2017–2020;
- pass matching by region, UTC date, day/night, and a maximum 60-minute separation;
- a shared 10 km Lambert equal-area grid and cell-pass analysis unit;
- a Poisson-loss gradient-boosting count model using a 3×3 VIIRS neighborhood, scan footprint, season, latitude, day/night, and pass-time difference;
- time-separated protocol: fit on 2017–2018, select on 2019, evaluate on 2020 outside those steps;
- 500-replicate date-block bootstrap and four leave-one-region-out spatial transfer tests;
- a later-year Western Iberia test specified before scoring, with the 2019 selection frozen and no 2020–2021 fitting;
- a locked 2024 spatial-temporal transfer test across three new regimes, with no region identity in the model and no retuning after opening the test;
- a frozen 2023 Western Iberia outcome check against 201 EFFIS mapped burned-area events, including event bootstrap, calendar-shift permutation and an overlap sensitivity;
- an eight-pair full-swath audit using four Aqua MODIS and four S-NPP VIIRS acquisitions, separating clear non-fire, fire, water, cloud, unprocessed and not-observed evidence;
- a dependency-free bilingual web application with an AOI/date-range workflow, historical-median comparison, Evidence Passport, GeoJSON, OpenAPI contract, auditable JSON and SHA-256 provenance.

## Evidence

- 2020 temporal-holdout count WAPE: 1.224 baseline → 0.832 selected model (32.0% improvement); this holdout was reused during project iteration.
- 2020 count Spearman: 0.045 baseline → 0.635 selected model.
- Date-block bootstrap 95% interval for selected-minus-baseline MAE: [-0.269, -0.229]; probability the model is better: 100% in 500 replicates.
- Leave-one-region-out WAPE improvement: Amazon 37.5%, Northern California 14.6%, Hyrcanian 45.2%, Western Iberia 28.7%.
- All eight region × day/night count subgroups improve on the 2020 holdout.
- Western Iberia 2020 count WAPE: 1.071 baseline → 0.708 selected model on 1,517 shared cell-passes; entirely unseen Western Iberia: 1.009 → 0.719.
- Independently specified Western Iberia 2021 count WAPE: 1.160 baseline → 0.735 selected on 1,253 cell-passes (36.7% improvement); day and night both improve. Date-block bootstrap 95% MAE-difference interval: [-0.285, -0.227].
- Precommitted Western Iberia 2022 comparison: 0.925 fixed-ratio WAPE → 0.665 incumbent model on 1,722 matched cell-passes (28.1% reduction). Two VIIRS-only candidates scored 0.682 and 0.683; neither met the frozen promotion rule. This is conditional on detection-derived matched passes, and 2020/2021 outcomes were known before the 2022 protocol.
- Sensor-support audit: in 2022 Western Iberia, 245/739 MODIS-positive matched cell-passes had no VIIRS detection in the same cell. This is a conditional sensor-support gap, not an all-overpass miss rate; it limits what a VIIRS-positive-cell-only map can show.
- Frozen 2023 Western Iberia test: incumbent WAPE 0.704 versus 1.015 fixed ratio on 879 cell-passes. A geometry-aware candidate reached 0.701, but its 95% date-block MAE-difference interval [-0.0147, 0.0059] crosses zero, so it was not promoted. A nominal 90% residual interval covered 89.5% of this later-year sample and is not claimed as calibrated.
- Locked 2024 new-region test: 798,901 observations, 1,175 matched passes and 126,989 cell-passes. Pooled count WAPE improved from 1.369 to 1.084; all three regions and all six region × day/night subgroups improved. The 500-replicate UTC-date bootstrap interval for model-minus-baseline MAE was [-0.187, -0.144]. The frozen transfer gate passed, but WAPE remained above 1 in Africa and Siberia, so this is evidence of transfer beyond the original windows rather than operational/global accuracy.
- Frozen EFFIS outcome check: across 201 Western Iberian events in 2023, harmonized activity retained raw-VIIRS association within the locked 0.05 tolerance (Spearman 0.130 versus 0.156) and beat the circular-calendar null (one-sided p=0.006). The overall gate nevertheless failed because 0.130 was below the preregistered 0.30 threshold and the 2,000-event bootstrap interval [-0.019, 0.272] crossed zero. Fractional allocation of overlapping links gave 0.134. EFFIS is a semi-independent satellite-informed reference, not field ground truth.
- Dual-sensor full-swath audit: eight Western Iberia acquisitions (two day and two night for each sensor) passed the frozen integrity gate. Across cell-passes, MODIS supplied 4,088 clear sampled negatives and six fire cells; VIIRS supplied 4,377 and 15. Every acquisition retained explicit not-observed cells. This validates observation-state bookkeeping for one day, not global completeness or probability of detection.

## NASA data and open science

Fyrora uses the challenge's official NASA Earthdata FIRMS resource and standard-quality active-fire observations. Every dashboard artifact is generated from committed tables. Raw-partition hash inventories and `dist/data/manifest.json` record provenance without publishing the private MAP key. Source availability for judges will be set when the final submission is ready.

## Impact

Fyrora is designed as historical decision context for scientists, land managers, and organizations reviewing fire exposure. It helps users examine seasonal patterns and unusual periods without confusing a sensor transition with a real change in burning activity. In Europe it complements, rather than replaces, the operational Copernicus EFFIS service. The method can be extended to more years, regions, and VIIRS platforms after independent validation.

## Honest limitations

Fyrora is not an emergency alerting system and must not be used to protect life or property. The general calendar covers four preprocessed study windows; interactive coordinate filtering is currently bounded to Western Iberia and 2017–2020, not arbitrary global areas or the full early-2000s-to-present record. Harmonization scores use contemporaneous pairs derived from positive detections. A missing pair does not prove lack of satellite coverage or absence of fire. Day 11 demonstrates full-swath observation states for both sensors across one day; multi-season and multi-region opportunity validation remains required. The accepted model uses matched MODIS/VIIRS pass-time separation, so it is not a standalone VIIRS-only live service. The 2024 three-region transfer gate passed, but WAPE remained above 1 in two regions. The EFFIS outcome gate failed; the Evidence Passport therefore enforces `operationalReady=false`. Operational claims still require independent agency/field incident records, latency/SLA testing and calibrated uncertainty. The accepted claim is historical hotspot count harmonization. FRP remains experimental. S-NPP observations affected by the March 2026 mission anomaly are outside the evaluation corpus.

## Links

- Source code: https://github.com/CSHub-Project/NASA-2026-QORVEX-Challenge-09
- Official challenge: https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/
- NASA Earthdata FIRMS: https://www.earthdata.nasa.gov/data/tools/firms

- Copernicus EFFIS: https://forest-fire.emergency.copernicus.eu/
- NASA VIIRS active-fire product: https://viirsland.gsfc.nasa.gov/Products/NASA/FireESDR.html

## Suggested Global Award positioning

Primary: **Best Use of Science** and **Best Use of Data**. Supporting strengths: **Local Impact** through the Hyrcanian pilot and **Best Use of Storytelling** through the bilingual, coverage-aware calendar. These are award categories, not the five local scoring criteria.
