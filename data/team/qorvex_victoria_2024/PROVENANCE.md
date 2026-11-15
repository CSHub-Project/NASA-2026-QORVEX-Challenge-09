# QORVEX Victoria 2024 pilot — provenance

These six compact report tables came from the QORVEX team repository, branch
`feat/firms-pipeline-migration`, commit `4829811c19de`, retrieved 2026-11-15.
The upstream analysis was authored by Aria Fazlollah and is MIT-licensed.

Repository: https://github.com/CSHub-Project/NASA-2026-QORVEX-Challenge-09

Only descriptive, internally consistent outputs are integrated here: filtered
product contribution, monthly detections, H3 resolution-7 concentration, FRP
summaries and pairwise cell-day overlap. They are not treated as Fyrora's
harmonized output, a coverage mask, unique-fire counts or anomaly labels.

`victoria_2024_bbox_points.parquet` is a separate browser-map artifact built
from the frozen 222-partition NASA FIRMS Standard Processing archive in this
project. Its rectangular study window reproduces the upstream raw totals:
10,582 MODIS, 39,314 NOAA-20 VIIRS and 41,369 S-NPP VIIRS records. It is not the
political-boundary-filtered 57,305-record analytical subset used by the H3
summary above.
