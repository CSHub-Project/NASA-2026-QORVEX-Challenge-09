# Sealed 2021 Western Iberia test protocol

Recorded before inspecting or scoring the 2021 pilot observations on 2026-11-07.

## Question

Does the count harmonization selected on 2019 and previously evaluated on 2020 still beat the fixed ratio baseline in a later, unseen year in the European pilot region?

## Data and boundaries

- FIRMS Standard Processing MODIS and VIIRS SNPP active fire point exports for the fixed Western Iberia rectangle `[-9.5, 37.0, -5.5, 43.0]`, 2021-01-01 through 2021-12-31.
- Training: the existing four-region 2017–2019 observations only. No 2020 or 2021 observations enter fitting, baseline ratios, or selection.
- Validation: 2019. The per-region/day-night count and FRP model-versus-baseline choices must exactly match the committed `day4_validation_selection.csv`; the program aborts otherwise.
- Test: all 2021 Western Iberia detection-derived Aqua MODIS / VIIRS passes matched within 60 minutes, on the existing 10 km grid. No 2021-based tuning.

## Frozen method and success rule

Run `pipeline.evaluate_2021` once after the full 2021 raw partition set has been downloaded and normalized. Preserve the model parameters, 30-minute pass clustering, 60-minute match tolerance, 10 km grid, and feature set already committed before this test. Count WAPE is the primary metric. Success requires selected count WAPE below fixed ratio WAPE overall and separately for day and night. Report absolute MAE, signed bias, sample sizes, Spearman correlation, and date-block bootstrap CI (500 resamples) even if the success rule fails. FRP is secondary and experimental.

This is still an evaluation conditional on detection-derived matched passes, not a test of all satellite observation opportunities, fire incidents, burned area, or an operational alert system. A second geography and independent incident/burned-area reference remain necessary for commercial claims.
