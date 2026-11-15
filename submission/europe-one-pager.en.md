# Fyrora Europe — pilot brief

**Current status:** research prototype and customer-discovery hypothesis; no operational certification or commercial traction is claimed.

**Problem.** A change from MODIS to VIIRS can change hotspot counts because the instruments differ in resolution, sensitivity and observation opportunity. Historical comparisons need a defensible bridge and a clear account of where the matched sample provides support.

**What works today.** Fyrora pairs Aqua MODIS and S-NPP VIIRS detections in time, aggregates them to a shared 10 km equal-area grid, and tests a count harmonization model with a frozen 2020 holdout and leave-one-region-out transfer. A Western Iberia study window makes the European pilot explorable through a calendar and CSV. The dashboard publishes region-specific scores and SHA-256 provenance.

**European positioning.** Copernicus EFFIS already provides free operational fire information. Fyrora addresses a narrower historical analysis workflow: reproducible, sensor-comparable hotspot activity with an auditable data handoff. It is a potential complement to EFFIS, not a replacement.

**Potential buyers to interview.** Forestry agencies, infrastructure operators, insurers and climate-research consultancies. The proposed service is custom-area processing, stable batch/API delivery, GIS integration and scientific quality support. Pricing and willingness to pay remain untested.

**Critical scientific boundary.** The current point-export pipeline identifies matched passes from positive detections. A missing pair does not prove that either satellite did not observe the area or that no fire occurred. Proper observation opportunity requires granule/swath and cloud information. The calendar is not an emergency alert, burned-area map, unique-fire count or forecast.

**Next acceptance gate.** Replicate across more European ecologies and years; add a true acquisition-opportunity mask; validate against independent European reference data; and run structured customer interviews before making a commercial claim.

Official context: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/), [Copernicus EFFIS](https://forest-fire.emergency.copernicus.eu/), [EFFIS active-fire method](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/active-fire-detection).
