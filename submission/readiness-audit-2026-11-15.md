# Fyrora submission readiness audit

Date: 2026-11-15

## Challenge fit

Fyrora provides the requested web application for comparing MODIS and VIIRS
active-fire records as a historical activity calendar. Users can inspect
region, year and day/night views, build a bounded Western Iberia area of
interest, export data, and explore Victoria 2024 FIRMS detections by date and
sensor.

The application uses NASA FIRMS data directly. It keeps unsupported
detection-derived pass days unknown instead of converting them to zero. The
accepted scientific claim is historical hotspot-count harmonization.

## Judging criteria

| Criterion | Evidence in the submission | Status |
|---|---|---|
| Impact | Historical continuity across the MODIS–VIIRS transition and a European AOI workflow | Ready as a research-use case |
| Creativity | Coverage-aware calendar, sensor transition marker, Evidence Passport and point explorer | Ready |
| Validity | Time-separated fitting, later-year checks, spatial transfer, bootstrap intervals and disclosed failed gates | Ready with stated limits |
| Relevance | Working web application, FIRMS data, date and area controls, downloadable results | Ready |
| Presentation | Seven-slide English deck, bilingual application and 90-second judge tour | Ready; video rehearsal remains |

## Data included

- Aqua MODIS and S-NPP VIIRS observations for the 2017–2020 harmonization
  corpus.
- Western Iberia checks for 2021, 2022 and 2023.
- Three independent 2024 transfer regions.
- Victoria 2024 MODIS, S-NPP VIIRS and NOAA-20 VIIRS reports.
- A 91,265-record Victoria study-window point archive used by the interactive
  map.
- EFFIS 2023 event associations used only as a semi-independent outcome check.
- Natural Earth geometry used only as an offline map fallback.

## Claims that must remain out of the submission

- Global operational accuracy.
- Emergency alerting or protection of life and property.
- Full satellite coverage inferred from positive-detection exports.
- Unique-fire counts from FIRMS detection records.
- Calibrated operational uncertainty.
- A passed EFFIS outcome gate.

## Technical verification

- Static build completed.
- JavaScript syntax check completed.
- 44 automated tests passed.
- The final deck contains seven slides.
- Native charts on slides 4 and 5 contain portable workbook snapshots.
- The server health endpoint returned HTTP 200 before the final deployment.

## Remaining submission blockers

1. Confirm in writing with the Van Local Lead whether the disclosed
   pre-existing research prototype is eligible. Do not rewrite timestamps or
   hide the earlier work.
2. Record and upload the final demonstration video, then test its public link in
   a signed-out browser.
3. Complete the official Project tab, cite all external data and tools, and
   disclose assisted-development tools in the SI/AI fields.
4. Verify the public source, application, PDF and video links from a second
   network.
5. Create `space-apps-2026-submission` only after the submitted text, video and
   deployed build match the same commit.

## AI/SI disclosure boundary

The public application does not display development-tool commentary. The
submission package retains a concise tool disclosure because Space Apps forms
and some Local Events explicitly request it. Removing or falsifying that record
would create an eligibility risk and would not change the scientific evidence.
