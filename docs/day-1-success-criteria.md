# Day-one success criteria

The day-one milestone is complete only if all checks below pass.

## Access and reproducibility

- [x] Earthdata profile activated.
- [x] FIRMS MAP_KEY created, API-validated, and stored only in ignored `.env`.
- [x] Three pilot bounding boxes are versioned in `configs/regions.json`.
- [x] Downloader chunks FIRMS requests into the documented maximum five-day windows.
- [x] Raw data paths preserve year, region, source, and request date.

## Data integrity

- [x] 2019 contains both `MODIS_SP` and `VIIRS_SNPP_SP` for all three regions.
- [x] Acquisition time is parsed with leading zeros and stored as timezone-aware UTC datetime.
- [x] MODIS/VIIRS and day/night groups are both present where NASA reports observations.
- [x] No synthetic rows are introduced.
- [x] Empty API responses do not masquerade as observations.

## Scientific evidence

- [x] Monthly raw-count figures exist for all three regions.
- [x] Monthly FRP-sum figures exist for all three regions.
- [x] Figures visibly separate sensor family and day/night.
- [x] Monthly Parquet output can be reproduced from raw files with one command.

## Initial model targets for day three

The harmonized method must later beat a fixed-ratio baseline on held-out overlap data:

1. Lower median absolute error.
2. Lower signed bias.
3. Equal or higher Spearman rank correlation.
4. Reduced artificial discontinuity at the MODIS–VIIRS transition.
5. Bootstrap intervals with measured empirical coverage.

These criteria prevent selecting a visually attractive model that does not improve continuity.

