# Day 11 — frozen multi-swath observation audit

Protocol frozen before downloading or scoring the additional granules.

## Question

Can Fyrora distinguish **observed clear land with no detection** from cloud,
water, unprocessed pixels and cells not intersected by a swath, for every Aqua
MODIS and S-NPP VIIRS overpass intersecting Western Iberia on 2023-08-06?

This is an observation-support audit, not an accuracy estimate. The date is an
engineering stress test already used for the Day-8 single-pass proof; it is not
an independent model holdout.

## Locked sample and products

- AOI: `western_iberia` from `configs/regions.json`.
- UTC date: 2023-08-06.
- VIIRS Collection 2: four `VNP14IMG` + `VNP03IMG` pairs.
- Aqua MODIS Collection 6.1: four `MYD14` + `MYD03` pairs.
- Grid: the existing 10-km equal-area sinusoidal cell index.
- Fire-mask meanings are locked in `configs/day11_multiswath_audit.json`.

## Acceptance gates

The audit passes only if all eight fire/geolocation pairs are downloaded with
SHA-256 checksums; each sensor contributes two day and two night pairs; every
mask has valid codes and a same-shaped geolocation array; and the exported cell
state never converts cloud, water, unknown, unprocessed or not-observed into a
clear negative.

Every acquisition must retain all semantic pixel counts. A cell-acquisition is
`observed_clear_no_detection` only when at least one class-5 land pixel is
present and no class 7–9 fire pixel is present. A daily state is `clear_sampled`
only if that rule is satisfied in at least one intersecting acquisition and no
fire pixel was observed during the day. Cells outside all valid swath samples
remain `not_observed`.

## Scientific boundary

The exported counts show classified pixel samples, not an equal-area coverage
fraction. Passing this audit proves correct evidence bookkeeping for the chosen
day and AOI; it does not prove global completeness, probability of detection,
burned area, real-time readiness or incident safety.
