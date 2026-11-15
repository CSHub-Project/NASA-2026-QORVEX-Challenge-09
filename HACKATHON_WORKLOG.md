# NASA Space Apps 2026 hackathon worklog

## 2026-11-14 — official event work

- Started the official-event work from the disclosed research prototype without
  rewriting its earlier history.
- Re-read the published challenge statement and the newly published official
  NASA Earthdata FIRMS resource.
- Converted the challenge-to-product gap into an executable product scope.
- Added an interactive Western Iberia AOI builder with validated bounding-box
  coordinates, UTC date range, day/night selection, coverage-aware daily
  activity, a same-calendar-day historical-median comparison, anomaly output,
  and filtered CSV export.
- Kept the FIRMS MAP key server-side/offline; the static web application uses a
  compact, preprocessed and hashed evidence artifact.
- Preserved honest product boundaries: AOI support is currently limited to the
  Western Iberia evidence window and 2017–2020; missing matched-pass support is
  unknown rather than zero; the product is not a live emergency alert.
- Updated official-resource links, relevance copy, automated tests, build
  manifest, and provenance documentation.
- Corrected the historical comparison to use only days where the selected year
  and the historical reference both have matched-pass support, preventing
  sparse coverage from becoming a false negative anomaly.
- Browser-tested preset changes, invalid coordinate order, English/Persian RTL,
  the final default state, horizontal layout, and console errors.

## 2026-11-15 — submission integration

- Added the Victoria 2024 MODIS, S-NPP VIIRS and NOAA-20 VIIRS comparison to
  the public application, including an exact 91,265-record study-window point
  archive and date, overpass and product filters.
- Added a self-hosted Leaflet map using OpenStreetMap tiles with the required
  attribution and a local Natural Earth fallback.
- Added build-aware browser refresh through WebSocket with manifest polling as
  a fallback for networks that block HTTP Upgrade.
- Removed internal integration identifiers from the public HTML and JSON while
  retaining contributor and license records in the repository.
- Replaced promotional headings with direct scientific labels and changed the
  public source link to the QORVEX team repository.
- Rebuilt the seven-slide judge deck with simpler titles, QORVEX metadata and
  portable embedded chart workbooks. Reviewed all seven rendered pages.
- Ran the complete site build and test suite. All 44 automated tests passed.

## Remaining event priorities

1. Run the complete test suite and rebuild `dist/` after the final brand and copy review.
2. Record the exact commit and push it to the private personal repository.
3. Rehearse the updated three-minute script on a narrow/mobile screen.
4. Review the live Project tab and copy each verified field into the official form.
5. Before final judging, make only the approved submission repository and demo
   publicly accessible and verify every link in a signed-out browser.
6. Create `space-apps-2026-submission` only after the demo, video, and project
   page are final.
