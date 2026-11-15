# Day 10 — frozen external-outcome validation protocol

Frozen on 2026-11-11 **before downloading or opening the EFFIS reference file**.

## Question

For the already locked Western Iberia 2023 test output, does the harmonized
MODIS-equivalent activity retain a meaningful relationship with independently
mapped burned-area events, rather than merely reproducing the MODIS target?

This is an external-*outcome* test, not a claim of ground truth. EFFIS is only
semi-independent: its Rapid Damage Assessment uses MODIS imagery and active-fire
information, is refined with Sentinel-2 since 2018, and is visually checked. That
dependency will remain visible in every report.

## Frozen inputs

- Region: the existing Western Iberia rectangle `[-9.5, 37.0, -5.5, 43.0]`.
- Year: 2023 only.
- Prediction table: the already committed
  `geometry_2023_cell_pass_predictions.csv`; no model refit or threshold tuning.
- Selected harmonizer: the selection recorded before this validation. Results
  will also show observed Aqua MODIS and raw S-NPP VIIRS counts as comparators.
- Reference: EFFIS Rapid Damage Assessment burnt-area perimeters under CC BY 4.0.
- Eligible events: reported area at least 30 ha, intersecting the frozen rectangle,
  with a 2023 start date and valid geometry.

## Event linkage

Each equal-area cell centre is linked to an EFFIS event when it falls inside the
event geometry or its 10 km geodesic buffer and its observation date falls from
3 days before the reported start through 3 days after the reported end. EFFIS
warns that start/end fields need not equal ignition/extinction, so the buffer is
fixed in advance. Overlapping events may share observations; this limitation is
reported and a deduplicated sensitivity check will be included if overlap is
material.

For each event we sum four quantities: observed Aqua MODIS count, raw VIIRS
count, incumbent harmonized count, and geometry-aware harmonized count. The
primary harmonized series is the previously selected method, not whichever looks
best against EFFIS.

## Metrics and uncertainty

- Primary: Spearman rank correlation between `log1p(event area ha)` and
  `log1p(event activity)`.
- Secondary: Kendall tau, zero-activity event fraction, event count, area range,
  and day/night composition.
- Uncertainty: 2,000 event-level bootstrap resamples for the harmonized Spearman
  coefficient and its difference from raw VIIRS.
- Null test: 2,000 shared circular day-of-year shifts of the prediction calendar,
  preserving seasonality/spatial structure better than shuffling individual rows.
  The one-sided p-value is `(1 + null >= observed) / (R + 1)`.

## Locked success gates

All gates must pass:

1. At least 30 eligible EFFIS events.
2. Harmonized Spearman is at least 0.30.
3. Harmonized Spearman is no more than 0.05 below raw VIIRS (harmonization does
   not materially destroy external association).
4. The 95% event-bootstrap interval for harmonized Spearman is entirely above 0.
5. The circular-shift permutation p-value is at most 0.05.

Failure is a valid result and will not trigger model tuning on 2023 EFFIS data.

## Interpretation boundary

Passing supports outcome relevance for mapped Western Iberian events in 2023.
It does **not** establish causal prediction, small-fire recall, global validity,
or independence from all MODIS/VIIRS information. A genuinely independent
reference would require agency incident records or stratified high-resolution
validation imagery not used by EFFIS.

## Official references

- EFFIS Rapid Damage Assessment technical background:
  https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment
- EFFIS data and services:
  https://forest-fire.emergency.copernicus.eu/applications/data-and-services
- EFFIS data licence:
  https://forest-fire.emergency.copernicus.eu/about-effis/data-license
