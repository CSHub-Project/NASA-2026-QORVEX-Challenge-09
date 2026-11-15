# Day-three model card

## Intended use

Research candidate for converting S-NPP VIIRS active-fire detections into an Aqua MODIS-equivalent count scale on a shared equal-area grid. It supports a future historical burning-activity calendar. It is not a wildfire classifier, burned-area product, forecast, dispatch tool, or life-safety alert system.

## Data

- NASA FIRMS Standard Processing exports for 2019.
- Three pilot regions: Hyrcanian Forests, Northern California, and the Amazon Arc of Deforestation.
- Aqua MODIS and S-NPP VIIRS passes matched one-to-one within 60 minutes.
- Raw one-sided non-detections are retained as zeros; synthetic observations are never inserted.

## Temporal protocol

- Fit: January–June 2019.
- Method selection: July–September 2019.
- Final untouched test: October–December 2019.

The final candidate is refit on January–September only after method selection. Test data do not choose hyperparameters, features, or per-stratum fallback.

## Model

Histogram gradient boosting with Poisson loss, fixed regularization and deterministic random seed. Features include VIIRS count/FRP, a same-pass 3×3 spatial neighborhood, VIIRS scan/track footprint, matched-pass time difference, latitude, seasonal cycle, region, and day/night.

## Accepted result

The count candidate reduces overall holdout MAE by 35.3% and changes Spearman rank correlation from -0.159 to +0.572 versus the fixed-ratio baseline. Date-block bootstrap with 500 replicates yields an MAE-difference interval of [-0.227, -0.193]. Count improvement persists at 5, 10, and 25 km.

## Rejected or provisional result

FRP improves overall but fails stability checks in some region/day-night strata and at 25 km. It is experimental and must not drive operational interpretation.

## Known limitations

- Single-year evidence cannot establish interannual or global generalization.
- Three regions do not cover all fire regimes, land covers, latitudes, or industrial thermal anomalies.
- FIRMS point exports do not provide the complete observation opportunity, cloud mask, granule overlap, or view-angle information needed for a full detection-probability model.
- A 60-minute match window permits real fire evolution between observations.
- A hotspot count is neither burned area nor a unique fire-event count.

## Required before deployment

Multi-year and spatial holdouts, event construction, land-cover and observation-opportunity covariates, external burned-area consistency checks, calibrated uncertainty, and stakeholder validation.
