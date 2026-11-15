# Frozen 2023 geometry-aware count and uncertainty experiment

Recorded before downloading or scoring 2023 Western Iberia data. Results for 2020, 2021, and 2022 are already known, so none will be called a fresh model-selection test. The 2023 source and test outcome are untouched at protocol time.

## Hypothesis and frozen methods

The accepted 10 km Poisson histogram gradient boosting model already uses VIIRS mean scan and track widths as separate features. A geometry-aware candidate adds their product as approximate detection-pixel area, average VIIRS FRP per detection, and FRP per approximate pixel area. For cells without a VIIRS detection, all derived inputs are zero. This is a feature engineering hypothesis motivated by instrument geometry and the published dependence of detection limits on pixel area; it is **not** the published swath-level observation operator or a cloud correction. Model loss, hyperparameters, seed, pass matching, feature source, and grid remain the existing frozen values.

1. Fit incumbent and candidate on 2017–2018 across four regions.
2. Select the lowest Western Iberia 2019 count WAPE; exact ties keep the incumbent. Report 2019 all-region and Western Iberia day/night metrics.
3. Refit both on 2017–2019 only. Use 2020 Western Iberia **solely** to estimate separate day/night 90% absolute-residual quantiles for the validation-selected method. The 2020 result is already known, and no 2020–2022 row enters model fitting or candidate selection. No 2021–2022 row enters calibration.
4. Download and normalize complete 2023 Western Iberia MODIS_SP/VIIRS_SNPP_SP partitions, hash raw files, and score both methods once on all detection-derived matched cell-passes. Report fixed ratio, incumbent, candidate count WAPE/MAE/bias overall and day/night; report 90% interval empirical coverage and mean width overall and by day/night. Bootstrap candidate-minus-incumbent MAE by observation date (500 resamples).
5. Promote the candidate only if it won 2019 validation, beats incumbent and fixed ratio on 2023 overall WAPE, does not worsen either day/night WAPE, and its date-block bootstrap 95% MAE-difference upper bound is below zero. Otherwise retain incumbent. An empirical interval coverage below 90% is reported as a failure of the nominal interval; do not hide it or tune on 2023.

The matched union-cell sample and accepted model still require a MODIS detection-derived pass and matching-time information. Neither this experiment nor an interval estimate turns the product into an independent VIIRS-only live system. Full swath/geolocation/cloud masks and external reference checks are separate gates for worldwide operation.

Scientific motivation: [Sofiev and Kouznetsov 2026, *Geoscientific Model Development*](https://gmd.copernicus.org/articles/19/10123/2026/). Their actual observation operator requires pixel-level/granule information absent from the current FIRMS point export; its reported coefficients are not transferred here.
