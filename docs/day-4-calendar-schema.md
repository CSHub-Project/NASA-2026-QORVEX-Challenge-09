# Calendar-ready schema

One row represents `region × UTC date × day/night`.

| Field | Type | Meaning |
|---|---|---|
| `region_id` | string | Stable pilot-region identifier |
| `observation_date` | date | UTC calendar date |
| `daynight` | enum | NASA source flag `D` or `N` |
| `activity_count` | float/null | Aqua MODIS count or harmonized VIIRS MODIS-equivalent count |
| `matched_passes` | integer/null | Number of contemporaneous Aqua/VIIRS pass pairs contributing |
| `series_source` | string/null | `Aqua MODIS observed` or `VIIRS harmonized holdout` |
| `has_matched_coverage` | boolean | Whether a matched observation opportunity exists |
| `year`, `month`, `day` | integer | Calendar components for product queries |
| `percentile_vs_history` | float/null | Empirical percentile against covered days in the same historical month |
| `robust_z_vs_history` | float/null | `0.6745 × (value − median) / MAD` for the same historical month |

## Null semantics

`activity_count = null` means no matched coverage, not zero fire activity. A numeric zero is permitted only on a covered slot. Anomaly fields remain null outside the holdout period, without coverage, or when historical MAD is zero.

## Product rules

- Never color a null cell as low activity; render it with a separate no-data style.
- Display coverage and series source in tooltips and exports.
- Label percentiles as historical comparisons, not forecasts.
- Keep UTC explicit; local/solar time is a future derived field.
