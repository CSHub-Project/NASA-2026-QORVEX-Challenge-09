# Fyrora three-minute demo — English

## Operating rules

- Target duration: 2:45–2:55. Never use the final seconds for a critical claim.
- One speaker narrates; one operator controls the browser.
- Use the built-in Judge Mode for navigation. Do not improvise filter paths live.
- Start with Western Iberia · 2020 · Day. Keep a local `dist/` fallback ready.

## 00:00–00:20 — Hook

**Screen:** Hero.

> The same fire looks different to different satellite sensors. MODIS gave us a long historical record; VIIRS gives us finer detail. But if we simply join their hotspot counts, a sensor change can masquerade as a fire trend. Fyrora builds a tested bridge between them.

## 00:20–00:45 — Scale and user

**Screen:** Hero statistics, then Judge Mode step 1.

> We processed 2.59 million NASA FIRMS observations across four years and four different study windows. One is Western Iberia, spanning Portugal and western Spain. The goal is a defensible historical comparison for land managers and scientists.

## 00:45–01:25 — Product proof

**Screen:** Judge Mode step 2, calendar.

> Choose a region, year, and day or night overpass. History is Aqua MODIS; the held-out 2020 view is VIIRS harmonized to a MODIS-equivalent count. A hatched cell means no matched detection-derived pass—not zero fire. Then a user can draw a bounded Western Iberia area, choose UTC dates, compare only supported days with the same calendar days in other years, and export that exact series.

**Operator:** Focus one orange cell and one hatched cell, then use Judge Mode's AOI step. Do not open the download dialog during the live pitch.

## 01:25–02:05 — Scientific proof

**Screen:** Judge Mode step 3, evidence cards.

> We fit on 2017 and 2018, selected the method on 2019, and excluded 2020 from both steps. Against a fixed-ratio baseline, count WAPE improves from 1.224 to 0.832—a 32 percent reduction—and Spearman rises from 0.045 to 0.635. A 500-replicate date-block bootstrap keeps the improvement interval entirely below zero. All four unseen-region tests improve.

## 02:05–02:28 — Engineering proof

**Screen:** Judge Mode step 4, architecture.

> The pipeline is auditable: standard-quality FIRMS data, detection-pass matching, a shared equal-area grid and guarded time splits. We publish JSON, CSV, code and SHA-256 hashes for 2,344 raw partitions.

## 02:28–02:52 — Limits and impact

**Screen:** Judge Mode step 5, European pilot.

> In Western Iberia, the 2020 count WAPE falls from 1.071 to 0.708. A separately specified 2021 check, with no 2020–21 fitting, falls from 1.160 to 0.735. EFFIS remains Europe's operational reference; Fyrora adds an auditable historical bridge. FRP and the true observation mask need more work.

## 02:52–03:00 — Close

> One fire record. Two satellite generations. Evidence you can inspect.

## Recovery lines

- **If the calendar does not load:** “The interface is static and the same reviewed output is available in the committed CSV and JSON; I’ll continue with the evidence view.”
- **If asked why not use raw counts:** “VIIRS has finer resolution and different sensitivity; raw count discontinuity is the problem, not the solution.”
- **If asked whether this predicts fires:** “No. It creates comparable historical context; forecasting is a separate, future validation problem.”
- **If asked about FRP:** “We rejected operational FRP because one subgroup degrades. The count claim passed every predefined subgroup.”
- **If asked whether the newer geometry model was adopted:** “No. Its 2023 WAPE was slightly better, but the preregistered bootstrap interval for improvement included zero, so we kept the incumbent.”
- **If asked about uncertainty:** “A nominal 90% interval covered 89.5% of 2023 matched cell-passes; we report that shortfall and do not market the interval as calibrated.”
- **If asked about EFFIS:** “EFFIS already provides Europe’s operational fire information. We focus on an auditable historical sensor bridge and use EFFIS as a reference for future independent checks.”
- **If asked about the hatched days:** “They have no matched positive-detection pass in this sample; we cannot infer satellite non-coverage or no fire.”
- **If asked whether the AOI tool is global:** “Not yet. The usable workflow is deliberately bounded to Western Iberia and 2017–2020; global arbitrary-area processing is the next backend milestone.”
