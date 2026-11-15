# Day 9: locked independent-region transfer protocol

Protocol frozen before downloading or scoring any 2024 observations for the three new regions. Date: 8 November 2026 (Asia/Tehran).

## Question

Does the previously accepted count harmonization relationship transfer, without tuning, to three new fire regimes and a year absent from all fitting and method selection?

## Sealed test set

The machine-readable boxes are in `configs/day9_independent_regions.json`:

1. Southern African Savanna: `[20, -25, 32, -15]`.
2. Eastern Siberian Boreal: `[105, 55, 120, 65]`.
3. Southeast Australia: `[140, -39, 151, -32]`.

These are rectangular study windows chosen before outcome inspection to add savanna, high-latitude boreal, and Southern Hemisphere temperate/Mediterranean-type conditions. They are not official ecological or political boundaries. The test period is the complete 2024 UTC calendar year. Both `MODIS_SP` and `VIIRS_SNPP_SP` FIRMS Standard Processing sources must have every expected five-day partition. Empty valid responses remain part of the manifest.

## Frozen pipeline

- Training observations: the existing 2017–2019 corpus from Hyrcanian Forests, Northern California, Amazon Arc, and Western Iberia only.
- Pair Aqua MODIS and S-NPP VIIRS positive-detection-derived passes by region, UTC date, day/night, and at most 60 minutes, using the existing greedy closest-time rule.
- Aggregate to the existing 10 km Lambert cylindrical equal-area grid and add the existing 3×3 VIIRS neighborhood.
- Count model: Poisson `HistGradientBoostingRegressor` with `learning_rate=0.05`, `max_iter=180`, `max_leaf_nodes=15`, `min_samples_leaf=30`, `l2_regularization=1`, seed 42.
- Features: existing VIIRS count/FRP, 3×3 neighborhood, pass-time difference, scan/track, latitude, season and day/night. **Region identity is excluded**, so unseen-region dummy columns cannot leak into the test.
- Baseline: one fixed MODIS/VIIRS count ratio for each day/night group, estimated only from the 2017–2019 training corpus across all four existing regions.
- No 2020–2024 observation may alter features, hyperparameters, baseline ratios, regions, thresholds, or fitting.

## Outcomes and gates

Primary outcome is count WAPE on the union of positive-detection cell-passes. Also publish MAE, signed bias, Spearman correlation, cell-pass count, MODIS count, and model/baseline WAPE by region and day/night.

The external-transfer claim passes only if all of these hold:

1. Data completeness: all expected raw partitions for both sensors are present and hashed for every region.
2. Minimum support: each region has at least 50 matched pass pairs and 500 scored cell-passes. A region below support is reported as underpowered and cannot count as a pass.
3. Pooled model count WAPE is lower than the global fixed-ratio baseline.
4. Model count WAPE is lower than baseline in at least two of three regions; no region is more than 10% relatively worse than baseline.
5. A 500-replicate UTC-date block bootstrap for pooled `model MAE − baseline MAE` has a 95% interval entirely below zero.

Day/night results are mandatory diagnostics. Failure in a subgroup is disclosed but is not silently removed. FRP is descriptive only and cannot be promoted by this test. Regardless of outcome, 2024 remains test data and is not added to fitting.

## Claim boundary

This is a difficult spatial-temporal transfer test, but it still conditions on passes inferred from positive detections. It does not estimate all-overpass recall, burned area, incident detection, cloud-free coverage, or emergency-alert performance. The full-swath opportunity work begun on day 8 remains a separate required gate. No commercial/global-readiness claim follows from one passing test.
