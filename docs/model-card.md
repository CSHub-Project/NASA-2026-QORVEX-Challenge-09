# Harmonized count model card

## Status

Validated research candidate for the MVP calendar. FRP output is experimental and excluded from operational interpretation.

## Intended use

Convert S-NPP VIIRS active-fire detections to an Aqua MODIS-equivalent count scale on shared equal-area cells and matched satellite passes. The output supports historical pattern comparison and a coverage-aware burning-activity calendar.

It is not burned area, a unique fire-event count, a wildfire classifier, a spread forecast, or a life-safety alert.

## Evidence

- 2,587,488 normalized observations from 2017–2020 across four study windows.
- 5,314 contemporaneous Aqua MODIS / S-NPP VIIRS detection-pass pairs.
- Fit on 2017–2018 and method selection on 2019; 2020 is excluded from both. Project iteration reused this holdout, so a separately specified 2021 Western Iberia test was run with 2020–2021 excluded from training and selection.
- Count MAE reduction: 32.0% on 130,368 test cell-passes.
- Count Spearman: 0.045 baseline to 0.635 model.
- Date-block bootstrap MAE-difference interval: [-0.269, -0.229].
- Positive count WAPE improvement in all eight region/day-night subgroups.
- Positive transfer improvement when each region is entirely absent from training.
- In the independent 2021 Western Iberia test, count WAPE is 1.160 baseline versus 0.735 selected on 1,253 cell-passes; day and night both improve. Date-block bootstrap 95% MAE-difference interval is [-0.285, -0.227].
- In the precommitted 2022 Western Iberia check, the incumbent count model has WAPE 0.665 versus 0.925 fixed ratio on 1,722 cell-passes (28.1% lower). VIIRS-only and monotone VIIRS-only candidates score 0.682 and 0.683, so neither is promoted. The 500-date-block bootstrap 95% MAE-difference intervals for candidate minus incumbent both cross zero. The 2020/2021 results were known before this protocol; only 2022 was locked for this comparison.
- A post-test support audit finds 245/739 MODIS-positive Western Iberia 2022 cell-passes with no VIIRS detection in that same cell; 401/1,948 MODIS detections lie in these cells. This is conditional on detection-derived pass matches and is not an all-overpass omission rate. A map restricted to VIIRS-positive cells cannot reproduce those exact cells.
- A frozen 2023 Western Iberia test on 879 cell-passes finds 0.704 WAPE incumbent versus 1.015 fixed ratio. A geometry-aware candidate reaches 0.701 WAPE, but its date-block bootstrap candidate-minus-incumbent MAE 95% interval [-0.0147, 0.0059] includes zero; it is not promoted. A nominal 90% residual interval covered 89.5% of the locked test and is not shipped as calibrated uncertainty.

## Features and algorithm

Histogram gradient boosting with Poisson loss and fixed regularization. Inputs include VIIRS count/FRP, same-pass 3×3 neighborhood, scan/track footprint, pass-time difference, latitude, seasonal cycle, and day/night. Region is used by the region-aware model but removed from spatial-transfer experiments.

## Guardrail

For each region/day-night/metric, the nonlinear model is selected only when it beats the fixed-ratio baseline on the validation year with at least 100 rows. The choice is frozen before the 2020 test.

## Known limits

- Four pilot study windows and three later European year checks do not establish pan-European or global performance.
- FIRMS point exports do not contain complete cloud masks, observation opportunities, view angles, or granule polygons. The matched-pass catalog is derived from positive-detection timestamps, so a missing calendar pair does not establish a missed satellite overpass, zero fire activity, or a true no-observation day.
- The accepted historical model uses the MODIS/VIIRS pass-time separation. It cannot be represented as an independent VIIRS-only live inference service. A union of MODIS- and VIIRS-positive cells is also not a deployable VIIRS-only prediction grid.
- Calendar baseline length is currently three historical years.
- A match window up to 60 minutes permits real fire evolution.
- FRP still has subgroup failures and is not accepted.

## Required before operational deployment

More years and European fire regimes, full granule/swath and cloud/opportunity masks, land-cover covariates, event clustering, independent EFFIS burned-area/incident checks, spatial-temporal uncertainty calibration, and stakeholder validation.
