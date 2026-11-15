# Day-one normalized schema

## Observation-level fields

| Field | Type | Meaning |
|---|---|---|
| `latitude` | float | Detection centroid latitude, WGS84 |
| `longitude` | float | Detection centroid longitude, WGS84 |
| `acq_date` | string/date | Source acquisition date |
| `acq_time` | source value | HHMM acquisition time from FIRMS |
| `acq_time_hhmm` | string | Zero-padded four-character HHMM |
| `acquired_at_utc` | datetime | Parsed UTC acquisition timestamp |
| `month` | datetime | UTC calendar-month bucket |
| `satellite` | string | Terra, Aqua, S-NPP, etc. when supplied |
| `instrument` | string | MODIS or VIIRS when supplied |
| `source` | string | Exact FIRMS source, e.g. `MODIS_SP` |
| `sensor_family` | enum | Harmonized family label: MODIS/VIIRS |
| `daynight` | enum | `D` or `N`; not inferred from clock time |
| `frp` | float | Source fire radiative power in MW |
| `confidence` | source value | Preserved raw confidence; scales differ by product |
| `scan` / `track` | float | Actual pixel footprint dimensions where supplied |
| `region_id` | string | Stable pilot-region identifier |

## Monthly raw summary

Grouping key: `region_id × month × sensor_family × daynight`.

Metrics: `raw_count`, `frp_sum_mw`, `frp_median_mw`.

## Provenance rules

- Raw downloads are immutable and partitioned by year/region/source/date.
- Standard processing (`*_SP`) is used for the 2019 scientific overlap.
- No MODIS numeric confidence is mapped directly to VIIRS categorical confidence.
- All timestamps retain UTC. Local/solar time will be added as a derived field later.
- Hotspot count is not interpreted as burned area or unique fire-event count.

