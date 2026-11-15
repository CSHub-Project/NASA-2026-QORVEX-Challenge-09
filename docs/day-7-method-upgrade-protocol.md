# Day 7 method upgrade: preregistered 2022 European check

Written before opening or scoring the 2022 Western Iberia observations. The 2020 and 2021 outcomes have already been viewed and are excluded from method selection, fitting, and baseline-ratio estimation here.

## Scientific question

Can a simpler VIIRS-feature-only count estimator match or improve the existing count model on an unseen later year, while avoiding the feature `time_difference_minutes` that requires knowledge of an Aqua MODIS detection-derived pass?

## Frozen candidates

All use the existing 10 km equal-area matched cell-pass sample and Poisson-loss histogram gradient boosting with the same fixed hyperparameters (`learning_rate=0.05`, `max_iter=180`, `max_leaf_nodes=15`, `min_samples_leaf=30`, `l2_regularization=1`, seed 42).

1. **Legacy:** existing feature set, including MODIS/VIIRS pass-time separation.
2. **VIIRS only:** remove pass-time separation; retain VIIRS counts, FRP, 3×3 neighborhood, scan/track, location, season, region and day/night.
3. **Monotone VIIRS only:** candidate 2 with non-decreasing constraints on VIIRS count, log-count, neighborhood count, neighborhood log-count, and the VIIRS FRP log features. All other features unconstrained.

The fixed-ratio method is a separate non-ML baseline. These are count models only; no FRP operational claim is considered.

## Selection and locked test

- Fit candidates on 2017–2018 across all four regions, compare Western Iberia and all-region 2019 count WAPE, MAE, signed bias, and day/night WAPE. Select the lowest **Western Iberia 2019 WAPE**; ties go to the simpler candidate in order VIIRS only, monotone VIIRS only, legacy. Record every candidate's result.
- Refit each candidate on 2017–2019 only, with the same features and hyperparameters. No 2020–2022 data enters model fitting or ratio estimation.
- Test **all** candidates once on complete 2022 Western Iberia data after selection is frozen. Publish all 2022 results, including failures. The selected candidate is promoted only if its 2022 overall count WAPE is lower than both the fixed-ratio baseline and legacy model, with no day/night subgroup WAPE worse than the legacy model. Otherwise retain the previous accepted count method.
- Use date-block bootstrap with 500 resamples for selected-minus-legacy MAE; report a 95% interval. An interval spanning zero is described as inconclusive, even if point WAPE improves.

This test remains conditional on positive-detection-derived matched passes. A VIIRS-only feature vector does **not** make the FIRMS point export an all-overpass production system; a granule/swath and cloud opportunity mask is still required before operational use.
