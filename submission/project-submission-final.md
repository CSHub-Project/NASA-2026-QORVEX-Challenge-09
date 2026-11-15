# Fyrora project submission draft

Status: technically ready; Team Lead approval and Local Lead eligibility confirmation remain open.

## Title

Fyrora — One Fire Record Across Two Satellite Generations

## Team

QORVEX

Official team roster:

- Aria Fazlollah — Team Owner / Team Lead
- Melika Ostad Jafari — Team Member
- Tara Ali Asgharzadeh — Team Member
- Mobina Amrollahi — Team Member

Verified technical contributions are recorded in `CONTRIBUTORS.md`.

## Short summary

MODIS and VIIRS observe active fires at different spatial resolutions and with different detection opportunities, so their hotspot counts cannot be joined directly. Fyrora matches contemporaneous Aqua MODIS and S-NPP VIIRS passes on a shared 10 km equal-area grid, learns a guarded MODIS-equivalent count mapping, and presents the result as a coverage-aware historical activity calendar. Unsupported matched-detection days remain unknown instead of being converted to zero.

## Problem

A satellite transition can resemble a change in fire activity even when the difference comes from sensor resolution, sensitivity or observation opportunity. Directly concatenating MODIS and VIIRS detections can therefore create a false historical trend.

## Solution

Fyrora provides a bilingual web application for exploring harmonized historical hotspot activity by region, year and day or night overpass. It includes a bounded Western Iberia AOI workflow, downloadable results, later-year and unseen-region validation, an interactive Victoria 2024 multi-sensor explorer, and an Evidence Passport that links claims to versioned artifacts and hashes.

## NASA and external data

- NASA FIRMS Standard Processing Aqua MODIS and S-NPP VIIRS
- NASA FIRMS NOAA-20 VIIRS for the descriptive Victoria 2024 explorer
- NASA MODIS Collection 6.1 and VIIRS Collection 2 full-swath products for the observation-state audit
- Copernicus EFFIS 2023 mapped burned-area events for a semi-independent outcome check
- Natural Earth geometry for the offline map fallback

## Technology

- Python, pandas, NumPy, scikit-learn and PyArrow
- Poisson-loss histogram gradient boosting
- Equal-area 10 km grid and H3 resolution 7 for the separate Victoria spatial explorer
- Date-block bootstrap and leave-one-region-out transfer tests
- Static HTML, CSS and JavaScript application
- Leaflet and OpenStreetMap for the Victoria point explorer
- Parquet, CSV, JSON, GeoJSON, OpenAPI and SHA-256 manifests
- Docker and Nginx for the current preview deployment

## Evidence summary

- 2,587,488 normalized 2017–2020 source observations
- 5,314 matched Aqua MODIS and S-NPP VIIRS passes
- 2020 count WAPE: 1.224 fixed-ratio baseline and 0.832 selected model
- Western Iberia 2021 count WAPE: 1.160 baseline and 0.735 selected model
- Locked 2024 pooled transfer WAPE: 1.369 baseline and 1.084 selected model
- The EFFIS outcome gate failed and remains disclosed; `operationalReady=false`

## Limitations

Fyrora is a historical research prototype, not an emergency alerting system. FIRMS detection records do not establish complete satellite coverage or unique-fire counts. The accepted claim is historical hotspot-count harmonization. FRP remains experimental. Operational use requires broader full-swath validation, independent agency or field evidence, calibrated uncertainty, and latency testing.

## SI/AI disclosure

Use the disclosure required by the official form and the event rules. The current repository records assisted use in research support, coding and debugging, documentation editing, and interface iteration. Do not replace that record with a UI/UX-only statement unless it accurately describes the team's complete use and the Local Lead confirms that wording.

## Links

- Official project page: https://www.spaceappschallenge.org/2026/find-a-team/qorvex/?tab=project
- Source: https://github.com/CSHub-Project/NASA-2026-QORVEX-Challenge-09
- Challenge: https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/
- Seven-slide demonstration: `submission/demo/fyrora-space-apps-demo-submission.pdf`

## Final submission checks

- Obtain written eligibility guidance from the Van Local Lead.
- Verify the web application, source and seven-slide PDF from a signed-out mobile connection.
- Merge the approved release branch, create the submission tag, and submit the Project tab.
