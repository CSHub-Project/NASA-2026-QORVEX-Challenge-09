# Day 12 — frozen evidence-product contract

Frozen after Day 11 completed and before generating the Day-12 product.

## Objective

Turn the research outputs into a judge- and startup-ready **evidence product**
without converting research success into an operational claim. The creative
unit is an Evidence Passport: every public claim carries a status, scope,
limitation, source artifact and SHA-256 fingerprint.

## Locked deliverables

1. A claim registry in CSV and JSON.
2. A GeoJSON feature collection of the Day-11 dual-sensor daily evidence.
3. An OpenAPI 3.1 contract documenting the static machine-readable endpoints.
4. A readiness decision that becomes false whenever any blocking scientific
   gate fails.
5. A bilingual dashboard section showing both passed and failed gates.
6. A concise deployment/startup boundary and next validation milestones.

## Evidence grades

- **A:** direct full-swath evidence with explicit missingness.
- **B:** locked out-of-sample quantitative evaluation.
- **C:** exploratory association, failed gate, or insufficiently independent
  evidence; useful for learning but not a decision-ready claim.

Grades are categorical provenance labels, not invented probabilities or a
weighted “AI confidence score.”

## Acceptance rules

Every claim must have a real artifact, SHA-256, scope and limitation. GeoJSON
and OpenAPI must be syntactically valid. The product must remain
`operationalReady=false` while the Day-10 external outcome gate is failed. Raw
protected granules, credentials and personal data must not be copied to `dist`.

The dashboard must make the negative result as visible as the positive ones.
