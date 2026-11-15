# Turkish interface, AOI feedback, and historical anomaly release

## Language interface

The former Persian option was replaced by Istanbul Turkish. Turkish remains left-to-right, uses `tr-TR` number formatting, and covers the application guide, explorer, Victoria sensor lab, AOI workflow, validation sections, judge tour, methods, and team page. English remains the default language.

## AOI workflow

The AOI calculation already produced a valid coverage-aware series, but the result appeared below the viewport with no visible transition. The submit action now:

1. shows an analysis-in-progress state;
2. rejects invalid bounds or dates without running;
3. updates the four result cards and daily chart;
4. confirms completion in a live status region;
5. moves focus and the viewport to the results; and
6. enables the exact AOI CSV export.

The calculation still compares only supported target days with supported historical peers. Unsupported days remain null and never become zero.

## Historical anomaly scores

The previous calendar scored only the held-out 2020 series against 2017–2019 history. The revised calendar adds leakage-safe scores to the historical years:

- 2017 is scored against covered 2018–2019 observations in the same region, overpass, and month;
- 2018 is scored against covered 2017 and 2019 observations;
- 2019 is scored against covered 2017–2018 observations; and
- 2020 remains scored against all covered 2017–2019 observations.

This leave-one-year-out design prevents the target year's observations from entering its own reference distribution. Percentiles remain null without a usable reference, robust z-scores remain null when the reference MAD is zero, and no-coverage cells remain null.

## Submission deck

The seven-slide submission deck now includes the Victoria 2024 multi-sensor laboratory on slide 6. The statement is bounded to 57,305 filtered descriptive FIRMS records across MODIS, S-NPP VIIRS, and NOAA-20 VIIRS; it does not call them unique fires or harmonized anomaly output. The two quantitative charts were rebuilt from committed literal metrics and packaged with editable workbook snapshots.

## Verification

- 45 automated tests pass.
- Browser checks confirmed Turkish `lang=tr`, left-to-right layout, anomaly scores for 2017–2020, AOI result feedback, enabled CSV export, and no console errors.
- All seven PDF pages were rendered and visually checked.
