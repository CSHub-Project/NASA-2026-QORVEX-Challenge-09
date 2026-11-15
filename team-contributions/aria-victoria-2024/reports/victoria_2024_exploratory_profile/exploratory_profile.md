# QORVEX — Victoria 2024 Exploratory Profile

## 1. Dataset scope

- Geographic scope: Victoria, Australia
- First recorded detection: 2024-01-01
- Last recorded detection: 2024-12-31
- Spatially indexed detection records: 91,265
- Daily H3 resolution-7 activity groups: 25,779
- Active H3 resolution-7 cells: 14,199

This report describes recorded FIRMS hotspot detections. It does not
represent a complete record of all fire activity or satellite observation
coverage.

## 2. Satellite product contribution

- VIIRS SNPP: 41,369 (45.33%)
- VIIRS NOAA-20: 39,314 (43.08%)
- MODIS: 10,582 (11.59%)

## 3. Temporal distribution

- Month with the highest recorded detection count: 2024-04
- Season with the highest recorded detection count: Autumn
- Dates with at least one recorded detection: 363
- Mean detections per date with recorded detections:
  251.42
- Median detections per date with recorded detections:
  62.00

Monthly and seasonal values are based on UTC acquisition dates.

The seasonal grouping uses Southern Hemisphere seasons:
Summer (December–February), Autumn (March–May),
Winter (June–August), and Spring (September–November).

Dates without a detection record are not treated as confirmed
zero-activity or observed-zero days.

## 4. Spatial distribution

- Active H3 resolution-7 cells: 14,199
- Mean detections per active cell: 6.43
- Median detections per active cell: 3.00
- Maximum detections in one cell: 995
- H3 cell with the highest recorded count: 87be630a2ffffff

Spatial counts describe the distribution of recorded detections,
not the number of unique fires.

## 5. Fire Radiative Power (FRP)

- MODIS: mean 63.89 MW, median 24.20 MW, maximum 3086.30 MW
- VIIRS NOAA-20: mean 16.22 MW, median 5.91 MW, maximum 1318.69 MW
- VIIRS SNPP: mean 16.22 MW, median 6.31 MW, maximum 1232.79 MW

FRP is reported in MW. These statistics are product-specific.
MODIS and VIIRS FRP values should not be assumed to be directly
equivalent merely because they share the same unit.

A sum of recorded FRP values is not a measurement of total energy
released by a unique fire.

## 6. Cross-product spatial-temporal co-occurrence

- VIIRS NOAA-20: 6,611 cell-days (25.64%)
- VIIRS SNPP: 6,521 cell-days (25.30%)
- VIIRS NOAA-20 + VIIRS SNPP: 5,202 cell-days (20.18%)
- MODIS: 3,355 cell-days (13.01%)
- MODIS + VIIRS NOAA-20 + VIIRS SNPP: 2,194 cell-days (8.51%)
- MODIS + VIIRS SNPP: 955 cell-days (3.70%)
- MODIS + VIIRS NOAA-20: 941 cell-days (3.65%)

A cell-day combination means that one or more products recorded
detections within the same H3 resolution-7 cell on the same UTC date.

Co-occurrence does not establish that different satellites observed
the same physical fire.

## 7. Methodological limitations

1. FIRMS hotspot records are detections, not unique fire events.
2. Absence of a detection record does not establish zero fire activity.
3. This dataset does not independently describe valid observation
   coverage for every cell and date.
4. Sensor spatial resolution, overpass timing, detection algorithms,
   and measurement characteristics differ.
5. FRP statistics are kept separate by product.
6. This one-year regional dataset is not sufficient for the planned
   five-year Historical Detection Anomaly baseline.
7. The results are descriptive and do not constitute fire probability,
   severity classification, prediction, or causal explanation.

## 8. Generated outputs

The accompanying CSV tables and interactive HTML charts provide
the detailed results behind this report.
