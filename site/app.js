"use strict";

const translations = {
  en: {
    navExplore: "Explore", navSensorLab: "Sensor lab", navAoi: "Build an AOI", navEurope: "Europe pilot", navEvidence: "Evidence", navMethod: "Method", navGuide: "Guide", navTeam: "Team",
    guideEyebrow: "Application guide", guideTitle: "How to inspect Fyrora",
    guideIntro: "Use this route for a quick review, or start Judge mode for a guided 90-second tour.",
    guideOneTitle: "Start with the activity calendar", guideOneCopy: "Choose a region, year and overpass. Hatched dates lack matched-pass support and remain unknown.", guideOpenCalendar: "Open calendar",
    guideTwoTitle: "Inspect the Victoria sensor record", guideTwoCopy: "Filter real 2024 FIRMS records by date, day or night, and satellite product. These records are descriptive, not unique-fire counts.", guideOpenVictoria: "Open sensor lab",
    guideThreeTitle: "Run a bounded area analysis", guideThreeCopy: "Select a Western Iberia bounding box and UTC date range, then export the coverage-aware daily series.", guideOpenAoi: "Open AOI builder",
    guideFourTitle: "Check validation before interpretation", guideFourCopy: "Read the later-year, unseen-region, EFFIS and full-swath results together with their stated limits.", guideOpenEvidence: "Open evidence",
    guideFiveTitle: "Audit the deployed inputs", guideFiveCopy: "The manifest, JSON endpoint and Evidence Passport link published claims to versioned artifacts and hashes.", guideOpenMethod: "Open method",
    guideBoundary: "Fyrora is a historical research prototype. It does not provide live incident alerts, burned-area estimates or safety guidance.",
    teamEyebrow: "About the developers", teamTitle: "QORVEX team contributors", teamIntro: "Fyrora combines the harmonization pipeline and web product with the Victoria 2024 FIRMS and H3 analysis.",
    taraRole: "Creator and technical lead", taraContribution: "Harmonization pipeline, validation design, evidence product and web application.",
    ariaRole: "Team lead · FIRMS and spatial analysis", ariaContribution: "Victoria 2024 multi-sensor summaries, H3 concentration and cell-day overlap analysis.",
    memberRole: "QORVEX team member", officialMember: "Official NASA Space Apps team member.",
    teamNote: "The roster matches the official QORVEX team page. Detailed release contributions remain recorded in the repository.", footerTeam: "Developed by the QORVEX team",
    sensorLabEyebrow: "Victoria 2024 · NASA FIRMS records", sensorLabTitle: "Victoria multi-sensor comparison",
    sensorLabIntro: "A filtered 2024 Victoria pilot compares MODIS, S-NPP VIIRS and NOAA-20 VIIRS records, then maps the 100 most active H3 cells. It adds multi-sensor context without pretending that co-occurrence proves the same fire.",
    recordedDetections: "Recorded detections", activeH3: "Active H3 cells · res 7", peakH3: "Peak records in one cell",
    spatialConcentration: "Spatial concentration", victoriaMap: "Victoria · top 100 H3 cells", realData: "REAL DATA", mapCellHint: "Point to a hexagon to inspect its exact H3 cell and record count.",
    sensorContribution: "Sensor contribution", productMix: "Filtered product mix", sensorResolutionNote: "The higher VIIRS share is expected from its finer spatial resolution and detection capability; it is not direct evidence of more fire.",
    seasonalSignal: "Seasonal signal", monthlyBySensor: "Monthly records by sensor", cellDayAgreement: "Cell-day agreement", pairwiseOverlap: "Pairwise H3 overlap",
    interpretationBoundary: "Interpretation boundary.", sensorBoundary: "Descriptive filtered FIRMS records only—not Fyrora harmonized output, a full coverage mask, anomaly score or unique-fire count. Missing observations are never filled with zero.",
    downloadMonthly: "Monthly CSV", downloadH3: "H3 CSV", downloadOverlap: "Overlap CSV",
    pointExplorerEyebrow: "Interactive point explorer · 2024", pointExplorerTitle: "Victoria detections by UTC date", nasaStandardData: "NASA STANDARD DATA",
    mapDate: "UTC date", allOverpasses: "All", products: "Products", playDates: "Play", pauseDates: "Pause",
    visiblePoints: "Visible records", visibleFrp: "Recorded FRP", utcWindow: "UTC acquisition window", mapLoading: "Loading the validated point archive…",
    pointMapBoundary: "The map uses the rectangular Victoria study window, not a political boundary. Each dot is one FIRMS detection record; overlapping dots and repeat satellite visits are not unique fires.",
    challenge: "NASA Space Apps 2026 · Research prototype",
    heroTitle: "MODIS–VIIRS<br>hotspot harmonization.",
    heroLede: "A reproducible method for comparing historical Aqua MODIS and S-NPP VIIRS hotspot counts—with unsupported days left explicitly unknown.",
    exploreData: "Open activity explorer", downloadDataset: "Download calendar CSV",
    judgeMode: "Judge mode", startTour: "Start 90-second judge tour",
    darkMode: "Dark mode", lightMode: "Light mode", activeWindow: "Active window", temporalSlice: "Temporal slice",
    mapNote: "Real study bounding boxes · not political boundaries", observations: "source observations",
    passes: "matched satellite passes", years: "years", studyWindows: "study windows",
    improvement: "lower count WAPE on 2020 holdout", coverageFirst: "Coverage-aware activity record",
    explorerTitle: "Compare hotspot activity without treating missing support as zero.",
    explorerIntro: "History uses Aqua MODIS counts; each 2017–2019 anomaly is scored against the other historical years only. The held-out 2020 view uses VIIRS harmonized to MODIS-equivalent counts and is scored against all 2017–2019 history. Hatched cells mean no matched detection-derived pass.",
    region: "Region", year: "Year", overpass: "Overpass", day: "Day", night: "Night",
    exportView: "Export this view", coverage: "Matched-pass support", observedDays: "Supported days",
    peakDay: "Peak observed day", source: "Series source", low: "Low", high: "High",
    historicalCount: "No leakage-safe anomaly reference",
    noCoverage: "No matched pass", cellHint: "Focus or point to a day to inspect its evidence.",
    aoiEyebrow: "Interactive area of interest", aoiTitle: "Analyze a place and time within Western Iberia.",
    aoiIntro: "Enter a bounding box inside the Western Iberia evidence window, choose a UTC date range and compare harmonized activity with the median of matching calendar days in other available years.",
    aoiFull: "Western Iberia", aoiPortugal: "Portugal focus", aoiGalicia: "Galicia focus",
    aoiWest: "West longitude", aoiEast: "East longitude", aoiSouth: "South latitude", aoiNorth: "North latitude",
    aoiStart: "Start date · UTC", aoiEnd: "End date · UTC", aoiRun: "Analyze this area", aoiExport: "Download AOI CSV",
    aoiBoundary: "Evidence scope: 2017–2020 and the displayed Western Iberia rectangle. Coordinates outside this window are rejected. This prototype never sends your NASA key to the browser.",
    aoiMapNote: "The bright rectangle is your selected AOI; the outer frame is the available evidence window.",
    aoiActivity: "Harmonized activity", aoiSupported: "Supported days", aoiMedian: "Historical median expectation", aoiAnomaly: "Anomaly vs median",
    aoiSeries: "Daily activity in the selected AOI", aoiHint: "Run the analysis to create a coverage-aware daily series.",
    aoiObserved: "Supported cell-days", aoiUnknown: "No matched-pass support", aoiInvalid: "Enter a valid box inside Western Iberia and a valid date range.",
    aoiResultSummary: "matched-pass evidence days; missing days stay unknown", aoiNoHistory: "No comparable historical days", aoiCsvReady: "AOI CSV downloaded.",
    europeEyebrow: "European field pilot", europeTitle: "Western Iberia validation record.",
    europeIntro: "A rectangular study window across Portugal and western Spain tests the historical bridge in a European fire regime. The 2021 check was specified before its data was scored, with no retraining or selection on 2020–21.",
    europeHoldout: "2020 European holdout", europeWape: "Count WAPE, shared cell-passes",
    europeTransfer: "Europe entirely absent from training", europeTransferTitle: "Unseen-region transfer",
    europeIndependent: "Independent 2021 year check", europeIndependentTitle: "Frozen method, later European year",
    downloadIndependent: "Download 2021 test metrics", matchedPasses: "matched passes",
    europeLocked2022: "Precommitted 2022 check", europeLocked2022Title: "The incumbent remains best on a later year",
    downloadLocked2022: "Download all 2022 candidate results",
    noPromotion2022: "VIIRS-only candidates did not earn promotion",
    europeLocked2023: "Locked 2023 geometry check", europeLocked2023Title: "A small model gain did not pass the uncertainty gate",
    downloadLocked2023: "Download 2023 model metrics", downloadIntervals2023: "Download interval coverage",
    geometryNotPromoted: "geometry-aware WAPE", intervalCoverage2023: "90% interval observed coverage",
    noPromotion2023: "not promoted; MAE difference CI crosses zero",
    supportGap2022: "2022 sensor support gap", supportGapTitle: "A VIIRS-positive-cell map misses some MODIS-positive cells",
    supportGapNote: "MODIS-positive cell-passes without a VIIRS detection in the same cell; this is conditional on matched detection-derived passes, not an all-overpass recall estimate.",
    downloadSupportAudit: "Download seven-year support audit",
    day9Eyebrow: "Locked 2024 external transfer", day9Title: "Locked 2024 transfer test.",
    day9Intro: "The 2017–19 model was frozen before opening 2024 data from Southern African savanna, Eastern Siberian boreal forest and Southeast Australia.",
    day9Pooled: "Pooled count WAPE", day9PooledTitle: "Independent spatial-temporal transfer",
    day9Africa: "Southern African savanna", day9Siberia: "Eastern Siberian boreal", day9Australia: "Southeast Australia",
    day9Passed: "locked gate passed", day9Failed: "locked gate did not pass", day9Dates: "UTC dates",
    day9Download: "Download complete 2024 metrics",
    day9Boundary: "The locked gate passed, but WAPE remains above 1 in two regions. This supports transfer beyond the original windows; it does not establish global or operational accuracy.",
    day10Eyebrow: "Frozen 2023 EFFIS outcome check", day10Title: "EFFIS outcome test: the gate did not pass.",
    day10Intro: "The already locked Western Iberia output was linked to EFFIS mapped burned-area events without refitting or choosing a better-looking method.",
    day10Association: "Event area association · Spearman ρ", day10AssociationTitle: "Harmonized activity versus mapped burned area",
    day10Events: "Eligible EFFIS events", day10NullTitle: "Calendar-shift null test", day10SemiIndependent: "Semi-independent",
    day10BoundaryTitle: "Not ground truth", day10Boundary: "The temporal signal beat the shifted-calendar null, but ρ missed the frozen 0.30 gate and its bootstrap interval crossed zero. EFFIS also uses satellite evidence, so this is not independent field validation.",
    day10Download: "Download EFFIS association metrics", day10Failed: "locked gate did not pass", day10Passed: "locked gate passed", day10Ci: "95% event-bootstrap CI for harmonized Spearman",
    day10RawViirs: "Raw VIIRS", day10Harmonized: "Harmonized", day10Threshold: "Frozen threshold", day10Permutation: "one-sided calendar-shift p-value",
    passportEyebrow: "Evidence Passport", passportTitle: "Claim registry and evidence boundaries.",
    passportIntro: "A machine-readable claim registry links each statement to scope, limitation, source artifact and SHA-256. Grades describe provenance, not an invented probability.",
    passportSwath: "Full-swath audit", passportSwathTitle: "Direct observation support", passportPassed: "passed",
    passportSwathNote: "audited MODIS/VIIRS acquisitions across two sensor families",
    passportClaims: "Audited claims", passportClaimsTitle: "Supported, failed and bounded", passportSupported: "supported", passportUnsupported: "failed or unsupported",
    passportStage: "Release stage", passportStageTitle: "Research preview—not an emergency alert", passportResearch: "research preview",
    passportBoundary: "The external-outcome gate failed, so operational readiness is deliberately false. This honesty is enforced in code and tests.",
    passportDownload: "Download Evidence Passport", passportGeojson: "Download observation GeoJSON", passportOpenapi: "OpenAPI contract",
    modisDetections: "MODIS detections",
    openEurope: "Explore Western Iberia calendar", downloadEurope: "Download Europe pilot CSV", openEffis: "Open Copernicus EFFIS ↗",
    europeBoundary: "Historical hotspot activity for planning and research; not burned area, live incident detection, or a safety alert. EFFIS remains the European operational reference.",
    testCells: "test cells", coveredSlots: "matched slots",
    untouchedTest: "2020 temporal holdout", evidenceTitle: "Temporal and spatial validation.",
    evidenceIntro: "The original four-region score excludes 2020 from fitting and selection; the separately specified 2021 European check excludes both 2020 and 2021. Spatial transfer holds out one entire region at a time.",
    primaryMetric: "Primary metric · count WAPE", temporalHoldout: "Temporal holdout",
    rankPreservation: "Rank preservation", spearmanTitle: "Spearman correlation",
    spearmanCopy: "Higher means the model better preserves where activity is relatively greater across shared grid cells.",
    unseenGeography: "Entirely unseen geography", transferTitle: "Leave-one-region-out transfer",
    honestBoundary: "Honest boundary", experimental: "Experimental", frpTitle: "FRP is not operational",
    frpCopy: "Overall FRP error improved, but subgroup failures remain. Fyrora does not present FRP as a deployable harmonized product.",
    traceable: "Traceable by design", methodTitle: "Processing and validation method.",
    methodOneTitle: "Match detection passes", methodOneCopy: "Pair Aqua MODIS and S-NPP VIIRS detection-derived passes by region, date, day/night and time tolerance.",
    methodTwoTitle: "Share the ground", methodTwoCopy: "Aggregate both sensors to the same 10 km equal-area cells before comparison.",
    methodThreeTitle: "Guard the future", methodThreeCopy: "Fit on 2017–18 and select on 2019; exclude 2020 from both steps and report iteration history.",
    methodFourTitle: "Show uncertainty", methodFourCopy: "Bootstrap by date, report subgroups, preserve null coverage, and publish machine-readable evidence.",
    provenanceTitle: "Audit the exact dashboard inputs", provenanceCopy: "Every deployed number is generated from committed tables. SHA-256 hashes make the data handoff verifiable.",
    openManifest: "Open manifest", openApi: "Open JSON data endpoint",
    architectureEyebrow: "Reproducible architecture", architectureTitle: "Data and processing trace",
    architectureOne: "NASA FIRMS standard data", architectureOneDetail: "Aqua MODIS + S-NPP VIIRS",
    architectureTwo: "Detection-pass match", architectureTwoDetail: "UTC, day/night, ≤60 min",
    architectureThree: "Shared 10 km ground grid", architectureThreeDetail: "Equal-area cell-pass pairs",
    architectureFour: "Guarded harmonization", architectureFourDetail: "Fit 2017–18 · select 2019 · test 2020",
    architectureFive: "Coverage-aware product", architectureFiveDetail: "Calendar · CSV · hashes",
    judgeEyebrow: "Project evidence index", judgeTitle: "Evidence index for judges",
    judgeIntro: "Each judging criterion links to evidence in the application.",
    impactTitle: "Impact", impactCopy: "A consistent historical view helps land managers recognize seasonal patterns and unusual periods without confusing sensor change for fire change.",
    creativityTitle: "Creativity", creativityCopy: "The calendar marks unsupported matched-detection days explicitly instead of silently converting them into “no fire.”",
    validityTitle: "Validity", validityCopy: "Leakage-safe year holdout, date-block bootstrap and leave-one-region-out transfer make the claim falsifiable.",
    relevanceTitle: "Relevance", relevanceCopy: "A user can enter coordinates and a UTC date range, compare activity with a historical median and export the result without exposing an API key.",
    presentationTitle: "Presentation", presentationCopy: "Bilingual storytelling, keyboard access, color-plus-pattern encoding and an auditable data endpoint keep the science legible.",
    seeCalendar: "See calendar →", seeNoData: "Inspect no-data →", seeEvidence: "See evidence →", seeMethod: "See method →", seeAoi: "Try the AOI builder →",
    startTourShort: "Run judge tour →", officialSources: "Official sources", challengeBrief: "Challenge brief ↗",
    visibleProof: "Visible proof:", closeTour: "Close", back: "Back", next: "Next", finish: "Finish",
    footerCopy: "Open-data prototype · Not an emergency alerting system",
    modisObserved: "Aqua MODIS observed", viirsHarmonized: "VIIRS harmonized holdout", baseline: "Fixed-ratio baseline",
    model: "Selected model", bootstrap: "500 date-block bootstrap replicates",
    ci: "95% CI for model − baseline MAE", probability: "Probability model is better",
    activity: "activity count", passesShort: "matched passes", percentile: "historical percentile",
    robustZ: "robust z-score", missingDetail: "No paired detection-derived pass. Satellite coverage cannot be inferred; activity remains unknown in this sample.",
    coverageOf: "of calendar days", improvementShort: "improvement", fileReady: "Filtered CSV downloaded.",
  },
  tr: window.FYRORA_TR,
};

const judgeSteps = {
  en: [
    { target: "#top", kicker: "01 · Problem", title: "Two satellite generations do not make one fire record by themselves.", copy: "MODIS and VIIRS differ in resolution, sensitivity and observation opportunity. A raw concatenation can manufacture a false trend.", proof: "NASA FIRMS source inventory spans four years and four study windows." },
    { target: "#explorer", kicker: "02 · Product", title: "Unsupported days stay visible.", copy: "The calendar separates a zero on a matched pass from a day with no detection-derived pair, then exposes region, year and day/night controls plus CSV export.", proof: "Hatched unsupported cells, dynamic source label and machine-readable calendar rows." },
    { target: "#aoi-builder", kicker: "03 · Relevance", title: "Coordinates and dates become a decision question.", copy: "A user enters a bounded AOI and UTC range, compares harmonized activity with a historical median, and exports the exact daily series.", proof: "The workflow is real, browser-side and key-safe; unsupported days remain unknown." },
    { target: "#evidence", kicker: "04 · Validity", title: "The result is tested after the model is frozen.", copy: "We fit on 2017–18, select on 2019 and exclude 2020 from both. We then remove each region entirely to test transfer to unseen geography.", proof: "2020 count WAPE and every unseen-region result are published below." },
    { target: "#architecture", kicker: "05 · Reproducibility", title: "The path from source to claim is explicit.", copy: "Pass matching, a shared equal-area grid, guarded modeling, null semantics and SHA-256 provenance form one auditable pipeline.", proof: "Open JSON, CSV, model card, source code and hashed manifest." },
    { target: "#europe", kicker: "06 · European use", title: "Western Iberia validation", copy: "Western Iberia is visible in the calendar. Its holdout and unseen-region scores are published alongside the boundary of a historical research product.", proof: "The European pilot uses real NASA FIRMS observations and links to the operational EFFIS reference." },
  ],
  tr: [
    { target: "#top", kicker: "01 · Problem", title: "İki uydu nesli kendiliğinden tek bir yangın kaydı oluşturmaz.", copy: "MODIS ve VIIRS çözünürlük, duyarlılık ve gözlem olanağı bakımından farklıdır. Ham birleştirme sahte bir eğilim üretebilir.", proof: "NASA FIRMS kaynak envanteri dört yılı ve dört çalışma penceresini kapsar." },
    { target: "#explorer", kicker: "02 · Ürün", title: "Desteklenmeyen günler görünür kalır.", copy: "Takvim, eşleşmiş geçişteki sıfırı tespit-türevli eşleşmenin olmadığı günden ayırır; bölge, yıl, gündüz/gece kontrolleri ve CSV sağlar.", proof: "Taranmış desteklenmeyen hücreler, dinamik kaynak etiketi ve makinece okunabilir takvim satırları." },
    { target: "#aoi-builder", kicker: "03 · İlgililik", title: "Koordinatlar ve tarihler bir karar sorusuna dönüşür.", copy: "Kullanıcı sınırlı bir AOI ve UTC aralığı girer, uyumlaştırılmış etkinliği tarihsel medyanla karşılaştırır ve kesin günlük seriyi dışa aktarır.", proof: "İş akışı tarayıcıda gerçektir, anahtarı korur ve desteklenmeyen günleri bilinmiyor bırakır." },
    { target: "#evidence", kicker: "04 · Geçerlilik", title: "Sonuç, model dondurulduktan sonra sınanır.", copy: "2017–18'de uyumlar, 2019'da seçer ve 2020'yi iki adımdan da çıkarırız. Ardından görülmemiş coğrafyaya aktarımı ölçmek için her bölgeyi bütünüyle dışarıda tutarız.", proof: "2020 sayım WAPE ve tüm görülmemiş bölge sonuçları aşağıda yayımlanır." },
    { target: "#architecture", kicker: "05 · Yeniden üretilebilirlik", title: "Kaynaktan iddiaya giden yol açıktır.", copy: "Geçiş eşleştirme, ortak eş-alan ızgarası, korumalı modelleme, null semantiği ve SHA-256 kökeni denetlenebilir bir hat oluşturur.", proof: "JSON, CSV, model kartı, kaynak kodu ve özetli manifest açıktır." },
    { target: "#europe", kicker: "06 · Avrupa kullanımı", title: "Batı İberya doğrulaması", copy: "Batı İberya takvimde incelenebilir. Ayrılmış test ve görülmemiş bölge puanları, tarihsel araştırma ürününün sınırlarıyla birlikte yayımlanır.", proof: "Avrupa pilotu gerçek NASA FIRMS gözlemlerini kullanır ve operasyonel EFFIS referansına bağlanır." },
  ],
};

const monthNames = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  tr: ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
};

function savedTheme() {
  try {
    const value = localStorage.getItem("fyrora-theme");
    if (value === "light" || value === "dark") return value;
  } catch (_) { /* Storage may be unavailable in a restricted browser. */ }
  return "light";
}

const state = { data: null, aoiData: null, landData: null, aoiSeries: null, lang: "en", theme: savedTheme(), regionId: null, year: null, daynight: null, judgeStep: 0, judgeTrigger: null };
const globeRuntime = { longitude: -18, latitude: 12, phase: 0, frame: 0, lastTime: 0, dragging: false, pointerX: 0, visible: true, focusedRegion: null };
const sensorRuntime = { points: [] };
const victoriaRuntime = { data: null, map: null, layer: null, renderer: null, timer: null, loading: false };
const $ = (selector) => document.querySelector(selector);
const t = (key) => translations[state.lang][key] || translations.en[key] || key;
const number = (value, digits = 0) => new Intl.NumberFormat(state.lang === "tr" ? "tr-TR" : "en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);

function regionName(regionId) {
  const region = state.data.regions.find((item) => item.id === regionId);
  if (region) return region.name_en;
  return regionId;
}

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  const dark = state.theme === "dark";
  const toggle = $("#theme-toggle");
  toggle.setAttribute("aria-pressed", String(dark));
  toggle.textContent = t(dark ? "lightMode" : "darkMode");
  document.querySelector('meta[name="theme-color"]').content = dark ? "#06110e" : "#f4f2ec";
}

function applyLanguage() {
  document.documentElement.lang = state.lang;
  document.documentElement.dir = "ltr";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const value = t(node.dataset.i18n);
    if (value.includes("<")) node.innerHTML = value;
    else node.textContent = value;
  });
  $("#language-toggle").textContent = state.lang === "en" ? "Türkçe" : "English";
  applyTheme();
  $("#study-scope-label").textContent = `${t("years")} · ${number(state.data.meta.studyRegions)} ${t("studyWindows")}`;
  renderSelectors();
  renderCalendar();
  renderEvidence();
  renderEurope();
  renderDay9();
  renderDay10();
  renderPassport();
  renderTeamSensorLab();
  renderVictoriaPoints();
  renderMap();
  renderAoiMap();
  if (state.aoiSeries) renderAoiResult(state.aoiSeries);
  if (!$("#judge-tour").hidden) renderJudgeStep(false);
}

function productLabel(code) {
  return ({ MODIS_SP: "MODIS", VIIRS_SNPP_SP: "S-NPP VIIRS", VIIRS_NOAA20_SP: "NOAA-20 VIIRS" })[code] || code;
}

function drawSensorMap() {
  const pilot = state.data?.teamSpatialPilot;
  const canvas = $("#sensor-map");
  if (!pilot || !canvas) return;
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(320, Math.round(rect.width));
  const height = Math.max(280, Math.round(rect.height || 360));
  canvas.width = width * ratio; canvas.height = height * ratio;
  const ctx = canvas.getContext("2d"); ctx.scale(ratio, ratio);
  const coords = pilot.topCells.flatMap((cell) => cell.boundary);
  const xs = coords.map((p) => p[0]); const ys = coords.map((p) => p[1]);
  const bounds = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const pad = 24;
  const project = ([lon, lat]) => [pad + (lon - bounds[0]) / (bounds[1] - bounds[0]) * (width - pad * 2), height - pad - (lat - bounds[2]) / (bounds[3] - bounds[2]) * (height - pad * 2)];
  const dark = state.theme === "dark";
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, dark ? "#0e2b24" : "#dbe7df"); gradient.addColorStop(1, dark ? "#071713" : "#edf1e7");
  ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height);
  sensorRuntime.points = [];
  const maxLog = Math.log1p(Math.max(...pilot.topCells.map((cell) => cell.count)));
  pilot.topCells.slice().reverse().forEach((cell) => {
    const polygon = cell.boundary.map(project); const intensity = Math.log1p(cell.count) / maxLog;
    ctx.beginPath(); polygon.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath();
    ctx.fillStyle = `rgba(255, ${Math.round(164 - intensity * 84)}, 55, ${0.2 + intensity * 0.75})`;
    ctx.strokeStyle = dark ? "rgba(255,220,145,.35)" : "rgba(86,56,15,.28)"; ctx.lineWidth = intensity > .75 ? 1.3 : .7; ctx.fill(); ctx.stroke();
    const [cx, cy] = project(cell.center); sensorRuntime.points.push({ x: cx, y: cy, cell });
  });
  ctx.fillStyle = dark ? "rgba(238,248,238,.68)" : "rgba(24,42,35,.68)"; ctx.font = "600 11px system-ui";
  ctx.fillText("H3 r7 · log color scale", 18, 20);
}

function renderTeamSensorLab() {
  const pilot = state.data?.teamSpatialPilot;
  if (!pilot) return;
  $("#sensor-total").textContent = number(pilot.totalRecordedDetections);
  $("#sensor-cells").textContent = number(pilot.activeH3Cells);
  $("#sensor-peak").textContent = number(pilot.topCells[0].count);
  const colors = { MODIS_SP: "#e85d3f", VIIRS_SNPP_SP: "#1e9e8c", VIIRS_NOAA20_SP: "#e3a127" };
  $("#sensor-products").innerHTML = pilot.products.map((row) => `<div class="sensor-product"><div><span>${productLabel(row.source_product)}</span><strong>${number(row.detection_count)}</strong></div><div class="sensor-product-track"><i style="width:${row.percentage}%;background:${colors[row.source_product]}"></i></div><small>${number(row.percentage, 1)}%</small></div>`).join("");
  const maxMonth = Math.max(...pilot.monthly.map((row) => row.MODIS_SP + row.VIIRS_NOAA20_SP + row.VIIRS_SNPP_SP));
  $("#sensor-monthly").innerHTML = pilot.monthly.map((row) => {
    let base = 0;
    const segments = ["MODIS_SP", "VIIRS_NOAA20_SP", "VIIRS_SNPP_SP"].map((key) => {
      const height = row[key] / maxMonth * 100; const bottom = base; base += height;
      return `<i style="height:${height}%;bottom:${bottom}%;background:${colors[key]}" title="${productLabel(key)}: ${row[key]}"></i>`;
    }).join("");
    return `<div class="sensor-month"><div class="sensor-month-bar">${segments}</div><span>${number(row.month)}</span></div>`;
  }).join("");
  $("#sensor-overlap").innerHTML = pilot.pairwiseOverlap.map((row) => `<div><span>${productLabel(row.product_a)} ↔ ${productLabel(row.product_b)}</span><strong>${number(row.jaccard_similarity * 100, 1)}%</strong><small>${number(row.shared_cell_days)} ${state.lang === "tr" ? "ortak hücre-gün" : "shared cell-days"}</small></div>`).join("");
  requestAnimationFrame(drawSensorMap);
}

function victoriaDayIndex(dateText) {
  return Math.round((new Date(`${dateText}T00:00:00Z`) - new Date("2024-01-01T00:00:00Z")) / 86400000);
}

function victoriaDateFromIndex(dayIndex) {
  const date = new Date(Date.UTC(2024, 0, 1 + Number(dayIndex)));
  return date.toISOString().slice(0, 10);
}

function renderVictoriaPoints() {
  if (!victoriaRuntime.data || !victoriaRuntime.map) return;
  const dateText = $("#victoria-date").value;
  const selectedDay = victoriaDayIndex(dateText);
  const daynight = $("#victoria-daynight").value;
  const products = new Set([...document.querySelectorAll('input[name="victoria-product"]:checked')].map((input) => input.value));
  const rows = victoriaRuntime.data.rows.filter((row) => row[0] === selectedDay && products.has(row[4]) && (daynight === "all" || row[5] === daynight));
  victoriaRuntime.layer.clearLayers();
  const colors = { M: "#e85d3f", N: "#e3a127", S: "#1e9e8c" };
  for (const row of rows) {
    const marker = L.circleMarker([row[2], row[3]], {
      renderer: victoriaRuntime.renderer, radius: 3.2, weight: .7, color: "#fff", opacity: .7,
      fillColor: colors[row[4]], fillOpacity: .78,
    });
    const hour = String(Math.floor(row[1] / 60)).padStart(2, "0");
    const minute = String(row[1] % 60).padStart(2, "0");
    const product = victoriaRuntime.data.products[row[4]].label;
    marker.bindTooltip(`${product} · ${hour}:${minute} UTC · FRP ${row[6] ?? "—"} MW`);
    marker.addTo(victoriaRuntime.layer);
  }
  const frp = rows.reduce((sum, row) => sum + (Number(row[6]) || 0), 0);
  const minutes = rows.map((row) => row[1]);
  const formatMinute = (value) => `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
  $("#victoria-visible").textContent = number(rows.length);
  $("#victoria-frp").textContent = rows.length ? `${number(frp, 1)} MW` : "—";
  $("#victoria-time").textContent = minutes.length ? `${formatMinute(Math.min(...minutes))}–${formatMinute(Math.max(...minutes))}` : "—";
  $("#victoria-map-status").textContent = rows.length
    ? `${dateText} · ${number(rows.length)} ${state.lang === "tr" ? "tespit kaydı" : "detection records"}`
    : `${dateText} · ${state.lang === "tr" ? "seçilen filtre için kayıt yok" : "no records for the selected filter"}`;
  $("#victoria-date-range").value = selectedDay;
}

function setVictoriaDate(dayIndex) {
  const bounded = Math.max(0, Math.min(365, Number(dayIndex)));
  $("#victoria-date").value = victoriaDateFromIndex(bounded);
  $("#victoria-date-range").value = bounded;
  renderVictoriaPoints();
}

function stepVictoriaDate(direction) {
  const dates = victoriaRuntime.data.daily.map((row) => row[0]);
  const current = $("#victoria-date").value;
  let index = dates.indexOf(current);
  if (index < 0) index = 0;
  index = (index + direction + dates.length) % dates.length;
  $("#victoria-date").value = dates[index];
  $("#victoria-date-range").value = victoriaDayIndex(dates[index]);
  renderVictoriaPoints();
}

function toggleVictoriaPlayback() {
  if (victoriaRuntime.timer) {
    clearInterval(victoriaRuntime.timer); victoriaRuntime.timer = null;
    $("#victoria-play").textContent = t("playDates");
    return;
  }
  $("#victoria-play").textContent = t("pauseDates");
  victoriaRuntime.timer = setInterval(() => stepVictoriaDate(1), 850);
}

async function loadVictoriaExplorer() {
  if (victoriaRuntime.loading || victoriaRuntime.data) return;
  victoriaRuntime.loading = true;
  try {
    const response = await fetch("data/victoria-2024-points.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    victoriaRuntime.data = await response.json();
    victoriaRuntime.map = L.map("victoria-map", { preferCanvas: true, minZoom: 5, maxZoom: 13, zoomControl: true });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).addTo(victoriaRuntime.map);
    L.geoJSON(state.landData, {
      style: { color: "#54756a", weight: 1, fillColor: "#dfe9e3", fillOpacity: .18, interactive: false },
    }).addTo(victoriaRuntime.map);
    victoriaRuntime.renderer = L.canvas({ padding: .5 });
    victoriaRuntime.layer = L.layerGroup().addTo(victoriaRuntime.map);
    const bbox = victoriaRuntime.data.scope.bbox;
    victoriaRuntime.map.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], { padding: [12, 12] });
    renderVictoriaPoints();
  } catch (error) {
    $("#victoria-map-status").textContent = `${state.lang === "tr" ? "Harita yüklenemedi" : "Map loading failed"}: ${error.message}`;
  } finally {
    victoriaRuntime.loading = false;
  }
}

async function sha256Text(textValue) {
  const bytes = new TextEncoder().encode(textValue);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function enableLiveReload() {
  if (["127.0.0.1", "localhost"].includes(location.hostname) || !window.WebSocket || !crypto.subtle) return;
  let pageBuild;
  try {
    const manifestText = await fetch("data/manifest.json").then((response) => response.text());
    pageBuild = await sha256Text(manifestText);
  } catch (_) { return; }
  const checkBuild = async () => {
    try {
      const latestText = await fetch(`data/manifest.json?check=${Date.now()}`).then((response) => response.text());
      if (await sha256Text(latestText) !== pageBuild) location.reload();
    } catch (_) { /* The next WebSocket message or poll will retry. */ }
  };
  setInterval(checkBuild, 5000);
  const connect = () => {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${location.host}/live-reload`);
    socket.addEventListener("message", (event) => {
      if (event.data.startsWith("build:") && event.data.slice(6) !== pageBuild) location.reload();
    });
    socket.addEventListener("close", () => setTimeout(connect, 1200));
  };
  connect();
}

function calendarRows() {
  return state.data.calendar
    .filter((row) => row[0] === state.regionId && Number(row[1].slice(0, 4)) === state.year && row[2] === state.daynight)
    .map((row) => ({ regionId: row[0], date: row[1], daynight: row[2], count: row[3], passes: row[4], coverage: row[5], percentile: row[6], z: row[7], source: row[8] }));
}

function renderSelectors() {
  const regionSelect = $("#region-select");
  regionSelect.innerHTML = state.data.regions.map((region) => `<option value="${region.id}"${region.id === state.regionId ? " selected" : ""}>${region.name_en}</option>`).join("");
  const yearSelect = $("#year-select");
  yearSelect.innerHTML = state.data.meta.years.map((year) => `<option value="${year}"${year === state.year ? " selected" : ""}>${number(year)}</option>`).join("");
  document.querySelector(`input[name="daynight"][value="${state.daynight}"]`).checked = true;
}

function percentileClass(value) {
  if (value === null || value === undefined) return "unscored";
  if (value >= 90) return "q5";
  if (value >= 70) return "q4";
  if (value >= 40) return "q3";
  if (value >= 15) return "q2";
  return "q1";
}

function sourceDisplay(source) {
  if (source === "Aqua MODIS observed") return t("modisObserved");
  if (source === "VIIRS harmonized holdout") return t("viirsHarmonized");
  return source || "—";
}

function showDayDetail(row) {
  const detail = $("#day-detail");
  if (!row.coverage) {
    detail.innerHTML = `<p><strong>${row.date}</strong> · ${t("missingDetail")}</p>`;
    return;
  }
  const percentile = row.percentile === null ? "—" : `${number(row.percentile)}%`;
  const robustZ = row.z === null ? "—" : number(row.z, 2);
  detail.innerHTML = `<p><strong>${row.date}</strong> · ${t("activity")}: <strong>${number(row.count)}</strong> · ${t("passesShort")}: <strong>${number(row.passes)}</strong> · ${t("percentile")}: <strong>${percentile}</strong> · ${t("robustZ")}: <strong>${robustZ}</strong></p>`;
}

function renderCalendar() {
  const rows = calendarRows();
  const hasPercentiles = rows.some((row) => row.coverage && row.percentile !== null);
  document.querySelectorAll("[data-percentile-legend]").forEach((node) => { node.hidden = !hasPercentiles; });
  document.querySelectorAll("[data-history-legend]").forEach((node) => { node.hidden = hasPercentiles; });
  const byDate = new Map(rows.map((row) => [row.date, row]));
  const grid = $("#calendar-grid");
  grid.innerHTML = `<span></span>${Array.from({ length: 31 }, (_, index) => `<span class="day-number">${number(index + 1)}</span>`).join("")}`;

  for (let month = 1; month <= 12; month += 1) {
    grid.insertAdjacentHTML("beforeend", `<span class="month-label">${monthNames[state.lang][month - 1]}</span>`);
    const daysInMonth = new Date(Date.UTC(state.year, month, 0)).getUTCDate();
    for (let day = 1; day <= 31; day += 1) {
      if (day > daysInMonth) {
        grid.insertAdjacentHTML("beforeend", '<span class="day-cell outside"></span>');
        continue;
      }
      const date = `${state.year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const row = byDate.get(date) || { date, coverage: false };
      const classes = row.coverage ? percentileClass(row.percentile) : "missing";
      const extreme = row.coverage && row.percentile !== null && row.percentile >= 95 ? " extreme" : "";
      const label = row.coverage ? `${date}: ${row.count} ${t("activity")}` : `${date}: ${t("noCoverage")}`;
      const button = document.createElement("button");
      button.type = "button";
      button.className = `day-cell ${classes}${extreme}`;
      button.setAttribute("aria-label", label);
      button.addEventListener("mouseenter", () => showDayDetail(row));
      button.addEventListener("focus", () => showDayDetail(row));
      button.addEventListener("click", () => showDayDetail(row));
      grid.appendChild(button);
    }
  }

  const covered = rows.filter((row) => row.coverage);
  const peak = covered.reduce((winner, row) => (!winner || row.count > winner.count ? row : winner), null);
  const coveragePct = rows.length ? covered.length / rows.length * 100 : 0;
  $("#coverage-value").textContent = `${number(coveragePct, 1)}%`;
  $("#observed-value").textContent = `${number(covered.length)} / ${number(rows.length)}`;
  $("#peak-value").textContent = peak ? `${peak.date} · ${number(peak.count)}` : "—";
  const sources = [...new Set(covered.map((row) => row.source).filter(Boolean))];
  $("#source-value").textContent = sources.map(sourceDisplay).join(" + ") || "—";
  $("#calendar-title").textContent = `${regionName(state.regionId)} · ${number(state.year)} · ${state.daynight === "D" ? t("day") : t("night")}`;
  $("#calendar-subtitle").textContent = `${number(coveragePct, 1)}% ${t("coverageOf")}`;
  $("#day-detail").innerHTML = `<p>${t("cellHint")}</p>`;
}

function overallMetric(model, metric = "count") {
  return state.data.metrics.find((row) => row.model === model && row.region_id === "all" && row.daynight === "all" && row.metric === metric);
}

function renderPairBars(target, baseline, selected) {
  const maximum = Math.max(baseline, selected);
  $(target).innerHTML = [
    [t("baseline"), baseline, ""],
    [t("model"), selected, "model"],
  ].map(([label, value, className]) => `<div class="bar-row"><span>${label}</span><div class="bar-track"><div class="bar-fill ${className}" style="width:${value / maximum * 100}%"></div></div><strong>${number(value, 3)}</strong></div>`).join("");
}

function renderEurope() {
  const pilot = state.data.europePilot;
  const independent = pilot.independent2021;
  const locked = pilot.locked2022;
  const locked2023 = pilot.locked2023;
  $("#europe-test-cells").textContent = `${number(pilot.testCellPasses)} ${t("testCells")}`;
  $("#europe-coverage").textContent = `${number(pilot.coveredSlots)} / ${number(pilot.calendarSlots)} ${t("coveredSlots")}`;
  $("#europe-2021-cells").textContent = `${number(independent.testCellPasses)} ${t("testCells")}`;
  renderPairBars("#europe-holdout-bars", pilot.baselineWape, pilot.selectedWape);
  renderPairBars("#europe-transfer-bars", pilot.transferBaselineWape, pilot.transferModelWape);
  renderPairBars("#europe-2021-bars", independent.baselineWape, independent.selectedWape);
  $("#europe-2021-note").textContent = `${number(independent.matchedPasses)} ${t("matchedPasses")} · ${t("ci")}: [${number(independent.maeDifferenceCi[0], 3)}, ${number(independent.maeDifferenceCi[1], 3)}]`;
  $("#europe-2022-cells").textContent = `${number(locked.testCellPasses)} ${t("testCells")}`;
  renderPairBars("#europe-2022-bars", locked.baselineWape, locked.selectedWape);
  $("#europe-2022-note").textContent = `${number(locked.matchedPasses)} ${t("matchedPasses")} · ${t("noPromotion2022")}`;
  $("#europe-2023-cells").textContent = `${number(locked2023.testCellPasses)} ${t("testCells")}`;
  renderPairBars("#europe-2023-bars", locked2023.baselineWape, locked2023.incumbentWape);
  $("#europe-2023-note").textContent = `${t("geometryNotPromoted")}: ${number(locked2023.geometryWape, 3)} · ${t("intervalCoverage2023")}: ${number(locked2023.empiricalIntervalCoverage * 100, 1)}% · ${t("noPromotion2023")}`;
  $("#europe-support-gap").textContent = `${number(locked.modisOnlyCellPasses)} / ${number(locked.modisPositiveCellPasses)}`;
  $("#europe-support-note").textContent = `${number(locked.modisDetectionsWithoutViirsCell)} / ${number(locked.modisDetections)} ${t("modisDetections")} · ${t("supportGapNote")}`;
}

function renderDay9() {
  const result = state.data.independentTransfer2024;
  const find = (region, method) => result.metrics.find((row) => row.region_id === region && row.daynight === "all" && row.method === method);
  const overallBaseline = find("all", "baseline");
  const overallModel = find("all", "model");
  renderPairBars("#day9-overall-bars", overallBaseline.wape, overallModel.wape);
  $("#day9-gate").textContent = t(result.gatePassed ? "day9Passed" : "day9Failed");
  const bootstrap = result.bootstrap[0];
  $("#day9-bootstrap").textContent = `${number(result.matchedPasses)} ${t("matchedPasses")} · ${number(bootstrap.utc_dates)} ${t("day9Dates")} · ${t("ci")}: [${number(bootstrap.ci_2_5, 3)}, ${number(bootstrap.ci_97_5, 3)}]`;
  [
    ["southern_africa_savanna", "#day9-africa-bars", "#day9-africa-cells"],
    ["eastern_siberia_boreal", "#day9-siberia-bars", "#day9-siberia-cells"],
    ["southeast_australia", "#day9-australia-bars", "#day9-australia-cells"],
  ].forEach(([region, bars, cells]) => {
    const baseline = find(region, "baseline");
    const model = find(region, "model");
    renderPairBars(bars, baseline.wape, model.wape);
    $(cells).textContent = `${number(model.cell_passes)} ${t("testCells")}`;
  });
}

function renderDay10() {
  const result = state.data.externalOutcome2023;
  const primary = result.metrics.filter((row) => row.analysis === "primary_many_to_many");
  const viirs = primary.find((row) => row.method === "viirs_count");
  const harmonized = primary.find((row) => row.method === result.selectedMethod);
  const threshold = 0.3;
  const maximum = threshold;
  $("#day10-bars").innerHTML = [
    [t("day10RawViirs"), viirs.spearman, ""],
    [t("day10Harmonized"), harmonized.spearman, "model"],
    [t("day10Threshold"), threshold, ""],
  ].map(([label, value, className]) => `<div class="bar-row"><span>${label}</span><div class="bar-track"><div class="bar-fill ${className}" style="width:${Math.max(0, value) / maximum * 100}%"></div></div><strong>${number(value, 3)}</strong></div>`).join("");
  $("#day10-gate").textContent = t(result.gatePassed ? "day10Passed" : "day10Failed");
  $("#day10-events").textContent = number(result.eligibleEvents);
  const interval = result.bootstrap.find((row) => row.comparison === "harmonized_spearman");
  $("#day10-bootstrap").textContent = `${t("day10Ci")}: [${number(interval.ci_2_5, 3)}, ${number(interval.ci_97_5, 3)}]`;
  $("#day10-permutation").textContent = `${t("day10Permutation")}: ${number(result.permutationP, 4)}`;
}

function renderPassport() {
  const product = state.data.evidenceProduct;
  $("#passport-swath-gate").textContent = product.fullSwathGatePassed ? t("passportPassed") : t("day9Failed");
  $("#passport-swath-note").textContent = `${number(product.auditedPairs)} ${t("passportSwathNote")}`;
  $("#passport-claims").textContent = `${number(product.supportedClaims)} / ${number(product.supportedClaims + product.failedOrUnsupportedClaims)}`;
  $("#passport-claims-note").textContent = `${number(product.supportedClaims)} ${t("passportSupported")} · ${number(product.failedOrUnsupportedClaims)} ${t("passportUnsupported")}`;
  $("#passport-stage").textContent = t("passportResearch");
}

function renderEvidence() {
  const baseline = overallMetric("baseline");
  const model = overallMetric("selected");
  const improvement = (baseline.wape - model.wape) / baseline.wape * 100;
  $("#metric-improvement").textContent = `−${number(improvement, 1)}%`;
  $("#spearman-value").textContent = number(model.spearman, 3);
  renderPairBars("#overall-bars", baseline.wape, model.wape);

  const bootstrap = state.data.bootstrap.find((row) => row.metric === "count");
  $("#bootstrap-note").textContent = `${t("bootstrap")} · ${t("ci")}: [${number(bootstrap.ci_2_5, 3)}, ${number(bootstrap.ci_97_5, 3)}] · ${t("probability")}: ${number(bootstrap.probability_model_better * 100)}%`;

  const regions = [...new Set(state.data.spatialTransfer.map((row) => row.heldout_region))];
  const improved = regions.filter((regionId) => {
    const base = state.data.spatialTransfer.find((row) => row.heldout_region === regionId && row.method === "baseline");
    const selected = state.data.spatialTransfer.find((row) => row.heldout_region === regionId && row.method === "model");
    return selected.wape < base.wape;
  }).length;
  $("#transfer-summary").textContent = `${number(improved)} / ${number(regions.length)}`;
  const maximumTransfer = Math.max(...state.data.spatialTransfer.map((row) => row.wape));
  $("#transfer-bars").innerHTML = regions.map((regionId) => {
    const base = state.data.spatialTransfer.find((row) => row.heldout_region === regionId && row.method === "baseline");
    const selected = state.data.spatialTransfer.find((row) => row.heldout_region === regionId && row.method === "model");
    const gain = (base.wape - selected.wape) / base.wape * 100;
    const sign = gain >= 0 ? "−" : "+";
    return `<div class="transfer-item"><span>${regionName(regionId)}</span><div class="pair" aria-label="${t("baseline")} ${base.wape}; ${t("model")} ${selected.wape}"><div class="mini-track"><i style="width:${base.wape / maximumTransfer * 100}%"></i></div><div class="mini-track"><i class="model" style="width:${selected.wape / maximumTransfer * 100}%"></i></div></div><strong>${sign}${number(Math.abs(gain), 1)}%</strong></div>`;
  }).join("");
}

function projectGlobe(longitude, latitude, width, height) {
  const radians = Math.PI / 180;
  const lambda = (longitude - globeRuntime.longitude) * radians;
  const phi = latitude * radians;
  const phi0 = globeRuntime.latitude * radians;
  const cosPhi = Math.cos(phi);
  const z = Math.sin(phi0) * Math.sin(phi) + Math.cos(phi0) * cosPhi * Math.cos(lambda);
  const radius = Math.min(width, height) * .365;
  return {
    x: width / 2 + radius * cosPhi * Math.sin(lambda),
    y: height / 2 - radius * (Math.cos(phi0) * Math.sin(phi) - Math.sin(phi0) * cosPhi * Math.cos(lambda)),
    z,
    radius,
  };
}

function drawProjectedLine(context, points, width, height, close = false) {
  let drawing = false;
  context.beginPath();
  points.forEach(([longitude, latitude]) => {
    const point = projectGlobe(longitude, latitude, width, height);
    if (point.z <= 0) { drawing = false; return; }
    if (!drawing) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
    drawing = true;
  });
  if (close && drawing) context.closePath();
}

function geoRings() {
  if (!state.landData) return [];
  return state.landData.features.flatMap((feature) => {
    const coordinates = feature.geometry.coordinates;
    return feature.geometry.type === "Polygon" ? coordinates : coordinates.flat();
  });
}

function bboxRing([west, south, east, north]) {
  const points = [];
  for (let step = 0; step <= 16; step += 1) points.push([west + (east - west) * step / 16, north]);
  for (let step = 1; step <= 16; step += 1) points.push([east, north - (north - south) * step / 16]);
  for (let step = 1; step <= 16; step += 1) points.push([east - (east - west) * step / 16, south]);
  for (let step = 1; step <= 16; step += 1) points.push([west, south + (north - south) * step / 16]);
  return points;
}

function drawOrbit(context, cx, cy, radius, phase, tilt, label, color) {
  context.save();
  context.translate(cx, cy);
  context.rotate(tilt);
  context.strokeStyle = "rgba(126, 213, 201, .22)";
  context.lineWidth = 1;
  context.setLineDash([4, 7]);
  context.beginPath();
  context.ellipse(0, 0, radius * 1.31, radius * .5, 0, 0, Math.PI * 2);
  context.stroke();
  context.setLineDash([]);
  const x = Math.cos(phase) * radius * 1.31;
  const y = Math.sin(phase) * radius * .5;
  context.shadowColor = color;
  context.shadowBlur = 14;
  context.fillStyle = color;
  context.beginPath();
  context.arc(x, y, 3.2, 0, Math.PI * 2);
  context.fill();
  context.shadowBlur = 0;
  context.fillStyle = "rgba(211, 235, 229, .78)";
  context.font = "600 9px ui-monospace, monospace";
  context.fillText(label, x + 7, y - 6);
  context.restore();
}

function drawGlobe(time = performance.now()) {
  const canvas = $("#study-map");
  if (!canvas || !state.data || !state.landData) return;
  const box = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.round(box.width));
  const height = Math.max(1, Math.round(box.height));
  if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
    canvas.width = width * ratio;
    canvas.height = height * ratio;
  }
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * .365;
  const elapsed = globeRuntime.lastTime ? Math.min(40, time - globeRuntime.lastTime) : 16;
  globeRuntime.lastTime = time;
  if (!globeRuntime.dragging && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    globeRuntime.longitude = ((globeRuntime.longitude + elapsed * .0025 + 540) % 360) - 180;
    globeRuntime.phase += elapsed * .00038;
  }

  context.save();
  context.shadowColor = "rgba(0, 0, 0, .7)";
  context.shadowBlur = 30;
  context.fillStyle = "rgba(0, 0, 0, .34)";
  context.beginPath();
  context.ellipse(centerX, centerY + radius * 1.08, radius * .78, radius * .12, 0, 0, Math.PI * 2);
  context.fill();
  context.restore();

  const ocean = context.createRadialGradient(centerX - radius * .35, centerY - radius * .4, radius * .05, centerX, centerY, radius * 1.08);
  ocean.addColorStop(0, "#1b6b72");
  ocean.addColorStop(.48, "#0a3c46");
  ocean.addColorStop(.82, "#041c25");
  ocean.addColorStop(1, "#01070b");
  context.fillStyle = ocean;
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, Math.PI * 2);
  context.fill();
  context.save();
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, Math.PI * 2);
  context.clip();

  context.strokeStyle = "rgba(177, 220, 219, .10)";
  context.lineWidth = .7;
  [-60, -30, 0, 30, 60].forEach((latitude) => {
    const line = [];
    for (let longitude = -180; longitude <= 180; longitude += 3) line.push([longitude, latitude]);
    drawProjectedLine(context, line, width, height);
    context.stroke();
  });
  for (let longitude = -180; longitude < 180; longitude += 30) {
    const line = [];
    for (let latitude = -89; latitude <= 89; latitude += 3) line.push([longitude, latitude]);
    drawProjectedLine(context, line, width, height);
    context.stroke();
  }

  context.fillStyle = "rgba(48, 112, 82, .94)";
  context.strokeStyle = "rgba(147, 205, 169, .55)";
  context.lineWidth = .75;
  geoRings().forEach((ring) => {
    drawProjectedLine(context, ring, width, height, true);
    context.fill();
    context.stroke();
  });

  const night = context.createLinearGradient(centerX - radius, centerY, centerX + radius, centerY);
  night.addColorStop(0, "rgba(0, 2, 7, .02)");
  night.addColorStop(.48, "rgba(0, 3, 8, .10)");
  night.addColorStop(1, "rgba(0, 2, 7, .78)");
  context.fillStyle = night;
  context.fillRect(centerX - radius, centerY - radius, radius * 2, radius * 2);

  state.data.regions.forEach((region) => {
    const active = region.id === state.regionId;
    context.strokeStyle = active ? "#86f1d9" : "rgba(242, 144, 101, .82)";
    context.lineWidth = active ? 2.2 : 1.15;
    context.shadowColor = active ? "#4ee6c7" : "transparent";
    context.shadowBlur = active ? 14 : 0;
    drawProjectedLine(context, bboxRing(region.bbox), width, height, true);
    context.stroke();
    const [west, south, east, north] = region.bbox;
    const center = projectGlobe((west + east) / 2, (south + north) / 2, width, height);
    if (center.z > 0) {
      context.fillStyle = active ? "#c1fff2" : "#f3a27c";
      context.beginPath();
      context.arc(center.x, center.y, active ? 3.2 : 2, 0, Math.PI * 2);
      context.fill();
      if (active) {
        const pulse = 7 + Math.sin(globeRuntime.phase * 4) * 1.5;
        context.strokeStyle = "rgba(134, 241, 217, .72)";
        context.lineWidth = 1;
        context.beginPath();
        context.arc(center.x, center.y, pulse, 0, Math.PI * 2);
        context.stroke();
        context.shadowBlur = 0;
        context.fillStyle = "rgba(231, 255, 249, .92)";
        context.font = state.lang === "tr" ? "650 11px Inter, system-ui, sans-serif" : "600 10px ui-monospace, monospace";
        context.textAlign = "left";
        context.fillText(regionName(region.id), center.x + 10, center.y - 8);
      }
    }
  });
  context.restore();

  context.strokeStyle = "rgba(125, 235, 220, .52)";
  context.lineWidth = 1.3;
  context.shadowColor = "rgba(81, 224, 204, .6)";
  context.shadowBlur = 16;
  context.beginPath();
  context.arc(centerX, centerY, radius + 1, 0, Math.PI * 2);
  context.stroke();
  context.shadowBlur = 0;
  drawOrbit(context, centerX, centerY, radius, globeRuntime.phase, -.23, "AQUA", "#8ef3df");
  drawOrbit(context, centerX, centerY, radius, globeRuntime.phase * .78 + 2.2, .86, "S-NPP", "#ff9a70");

  if (globeRuntime.visible && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    globeRuntime.frame = requestAnimationFrame(drawGlobe);
  }
}

function renderMap() {
  const activeRegion = state.data.regions.find((region) => region.id === state.regionId);
  if (globeRuntime.focusedRegion !== activeRegion.id) {
    const [west, south, east, north] = activeRegion.bbox;
    globeRuntime.longitude = (west + east) / 2;
    globeRuntime.latitude = Math.max(-55, Math.min(55, (south + north) / 2));
    globeRuntime.focusedRegion = activeRegion.id;
  }
  $("#map-active-name").textContent = regionName(activeRegion.id);
  $("#map-active-bbox").textContent = `[${activeRegion.bbox.join(", ")}]`;
  $("#map-time-slice").textContent = `${state.year} · ${state.daynight === "D" ? t("day") : t("night")}`;
  $("#map-time-rail").style.setProperty("--time-index", String(Math.max(0, Math.min(3, state.year - 2017))));
  $("#study-map").setAttribute("aria-label", `${regionName(activeRegion.id)}: ${activeRegion.bbox.join(", ")}`);
  cancelAnimationFrame(globeRuntime.frame);
  globeRuntime.lastTime = 0;
  drawGlobe();
}

function aoiInputs() {
  return {
    west: Number($("#aoi-west").value), east: Number($("#aoi-east").value),
    south: Number($("#aoi-south").value), north: Number($("#aoi-north").value),
    start: $("#aoi-start").value, end: $("#aoi-end").value,
    daynight: $("#aoi-daynight").value,
  };
}

function validAoi(query) {
  const scope = state.aoiData.scope;
  const [west, south, east, north] = scope.bbox;
  return Number.isFinite(query.west) && Number.isFinite(query.east)
    && Number.isFinite(query.south) && Number.isFinite(query.north)
    && query.west >= west && query.east <= east && query.south >= south && query.north <= north
    && query.west < query.east && query.south < query.north
    && query.start >= scope.startDate && query.end <= scope.endDate && query.start <= query.end;
}

function renderAoiMap() {
  if (!state.aoiData) return;
  const query = aoiInputs();
  const [scopeWest, scopeSouth, scopeEast, scopeNorth] = state.aoiData.scope.bbox;
  const x = (lon) => 8 + (lon - scopeWest) / (scopeEast - scopeWest) * 84;
  const y = (lat) => 92 - (lat - scopeSouth) / (scopeNorth - scopeSouth) * 84;
  const selected = validAoi(query)
    ? `<rect class="aoi-selection" x="${x(query.west)}" y="${y(query.north)}" width="${x(query.east) - x(query.west)}" height="${y(query.south) - y(query.north)}" rx="2"></rect>`
    : "";
  $("#aoi-map").innerHTML = `<svg viewBox="0 0 100 100" aria-hidden="true"><defs><pattern id="aoi-grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(238,248,238,.08)" stroke-width=".5"/></pattern></defs><rect class="aoi-scope" x="8" y="8" width="84" height="84" rx="3"></rect><rect x="8" y="8" width="84" height="84" fill="url(#aoi-grid)"></rect>${selected}<text x="10" y="6">43°N</text><text x="10" y="98">37°N</text><text x="7" y="96" text-anchor="end">9.5°W</text><text x="93" y="96">5.5°W</text></svg>`;
}

function aggregateAoi(query) {
  const filtered = state.aoiData.rows.filter((row) => row[1] === query.daynight
    && row[2] >= query.west && row[2] <= query.east
    && row[3] >= query.south && row[3] <= query.north);
  const daily = new Map();
  filtered.forEach((row) => {
    const entry = daily.get(row[0]) || { date: row[0], count: 0, passes: 0, sources: new Set() };
    entry.count += Number(row[4]);
    entry.passes += Number(row[5]);
    entry.sources.add(row[6]);
    daily.set(row[0], entry);
  });

  const start = new Date(`${query.start}T00:00:00Z`);
  const end = new Date(`${query.end}T00:00:00Z`);
  const selected = [];
  for (let cursor = new Date(start); cursor <= end; cursor.setUTCDate(cursor.getUTCDate() + 1)) {
    const date = cursor.toISOString().slice(0, 10);
    const row = daily.get(date);
    selected.push(row ? { ...row, coverage: true } : { date, count: null, passes: 0, sources: new Set(), coverage: false });
  }

  const medians = selected.map((row) => {
    const monthDay = row.date.slice(5);
    const selectedYear = row.date.slice(0, 4);
    const peers = [...daily.values()]
      .filter((item) => item.date.slice(5) === monthDay && item.date.slice(0, 4) !== selectedYear)
      .map((item) => item.count)
      .sort((a, b) => a - b);
    if (!peers.length) return null;
    const middle = Math.floor(peers.length / 2);
    return peers.length % 2 ? peers[middle] : (peers[middle - 1] + peers[middle]) / 2;
  });
  selected.forEach((row, index) => { row.historicalMedian = medians[index]; });
  return { query, selected };
}

function renderAoiResult(result) {
  const covered = result.selected.filter((row) => row.coverage);
  const total = covered.reduce((sum, row) => sum + row.count, 0);
  // Compare like with like: an expected value is only meaningful on days where
  // the selected year also has matched-pass support. Otherwise sparse coverage
  // would be misreported as a negative activity anomaly.
  const comparable = result.selected.filter((row) => row.coverage && row.historicalMedian !== null);
  const expected = comparable.reduce((sum, row) => sum + row.historicalMedian, 0);
  const actualComparable = comparable.filter((row) => row.coverage).reduce((sum, row) => sum + row.count, 0);
  const anomaly = expected > 0 ? (actualComparable - expected) / expected * 100 : null;
  $("#aoi-total").textContent = number(total, 1);
  $("#aoi-supported").textContent = `${number(covered.length)} / ${number(result.selected.length)}`;
  $("#aoi-median").textContent = comparable.length ? number(expected, 1) : "—";
  $("#aoi-anomaly").textContent = anomaly === null ? "—" : `${anomaly >= 0 ? "+" : ""}${number(anomaly, 1)}%`;
  $("#aoi-anomaly").className = anomaly !== null && anomaly > 0 ? "positive-anomaly" : "";
  $("#aoi-summary").textContent = `${number(covered.length)} ${t("aoiResultSummary")}`;
  $("#aoi-download").disabled = false;

  const maximum = Math.max(1, ...covered.map((row) => row.count));
  $("#aoi-chart").innerHTML = result.selected.map((row) => {
    const height = row.coverage ? Math.max(4, row.count / maximum * 100) : 100;
    const label = row.coverage ? `${row.date}: ${number(row.count, 1)}` : `${row.date}: ${t("aoiUnknown")}`;
    return `<button type="button" class="aoi-bar${row.coverage ? "" : " missing"}" style="--bar-height:${height}%" aria-label="${label}" title="${label}"><i></i></button>`;
  }).join("");
}

async function runAoi(event) {
  event?.preventDefault();
  const query = aoiInputs();
  const runButton = $("#aoi-run");
  runButton.disabled = true;
  runButton.textContent = t("aoiRunning");
  $("#aoi-status").textContent = "";
  renderAoiMap();
  if (!validAoi(query)) {
    $("#aoi-error").textContent = t("aoiInvalid");
    runButton.disabled = false;
    runButton.textContent = t("aoiRun");
    return;
  }
  $("#aoi-error").textContent = "";
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  try {
    state.aoiSeries = aggregateAoi(query);
    renderAoiResult(state.aoiSeries);
    $("#aoi-status").textContent = t("aoiComplete");
    $("#aoi-results").focus({ preventScroll: true });
    $("#aoi-results").scrollIntoView({ behavior: "smooth", block: "center" });
  } finally {
    runButton.disabled = false;
    runButton.textContent = t("aoiRun");
  }
}

function downloadAoi() {
  if (!state.aoiSeries) return;
  const header = ["observation_date", "daynight", "activity_count", "matched_passes", "has_matched_pass_support", "historical_median_same_calendar_day"];
  const lines = state.aoiSeries.selected.map((row) => [row.date, state.aoiSeries.query.daynight, row.count ?? "", row.passes, row.coverage, row.historicalMedian ?? ""].join(","));
  const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `fyrora_aoi_${state.aoiSeries.query.start}_${state.aoiSeries.query.end}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
  $("#aoi-summary").textContent = t("aoiCsvReady");
}

function downloadFiltered() {
  const rows = calendarRows();
  const header = ["region_id", "observation_date", "daynight", "activity_count", "matched_passes", "has_matched_coverage", "percentile_vs_history", "robust_z_vs_history", "series_source"];
  const csv = [header.join(","), ...rows.map((row) => [row.regionId, row.date, row.daynight, row.count ?? "", row.passes ?? "", row.coverage, row.percentile ?? "", row.z ?? "", JSON.stringify(row.source || "")].join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `fyrora_${state.regionId}_${state.year}_${state.daynight}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
  $("#day-detail").innerHTML = `<p>${t("fileReady")}</p>`;
}

function clearJudgeFocus() {
  document.querySelectorAll(".judge-focus").forEach((node) => node.classList.remove("judge-focus"));
}

function renderJudgeStep(shouldScroll = true) {
  const steps = judgeSteps[state.lang];
  const step = steps[state.judgeStep];
  const target = $(step.target);
  clearJudgeFocus();
  target.classList.add("judge-focus");
  if (shouldScroll) target.scrollIntoView({ behavior: "smooth", block: "center" });

  $("#tour-progress-label").textContent = `${number(state.judgeStep + 1)} / ${number(steps.length)}`;
  $("#tour-progress-dots").innerHTML = steps.map((_, index) => `<i class="${index === state.judgeStep ? "active" : ""}"></i>`).join("");
  $("#judge-tour-kicker").textContent = step.kicker;
  $("#judge-tour-title").textContent = step.title;
  $("#judge-tour-copy").textContent = step.copy;
  $("#judge-tour-proof").textContent = step.proof;
  if (state.judgeStep === 0) $("#judge-tour-proof").textContent = `${number(state.data.meta.observations)} ${t("observations")} · ${number(state.data.meta.studyRegions)} ${t("studyWindows")}.`;
  if (state.judgeStep === 1) $("#judge-tour-proof").textContent = `${number(state.data.meta.calendarRows)} ${state.lang === "tr" ? "kapsamı gözeten makinece okunabilir takvim satırı" : "coverage-aware machine-readable calendar rows"}.`;
  $("#tour-back").disabled = state.judgeStep === 0;
  $("#tour-next").textContent = state.judgeStep === steps.length - 1 ? t("finish") : t("next");
}

function startJudgeTour(event) {
  state.judgeTrigger = event?.currentTarget || document.activeElement;
  state.judgeStep = 0;
  $("#judge-tour").hidden = false;
  document.body.classList.add("tour-active");
  renderJudgeStep();
  $("#tour-next").focus({ preventScroll: true });
}

function closeJudgeTour() {
  $("#judge-tour").hidden = true;
  document.body.classList.remove("tour-active");
  clearJudgeFocus();
  state.judgeTrigger?.focus({ preventScroll: true });
}

function nextJudgeStep() {
  if (state.judgeStep >= judgeSteps[state.lang].length - 1) {
    closeJudgeTour();
    return;
  }
  state.judgeStep += 1;
  renderJudgeStep();
}

function previousJudgeStep() {
  if (state.judgeStep === 0) return;
  state.judgeStep -= 1;
  renderJudgeStep();
}

function bindStudyMapMotion() {
  const stage = $("#study-map-stage");
  const canvas = $("#study-map");
  canvas.addEventListener("pointerdown", (event) => {
    globeRuntime.dragging = true;
    globeRuntime.pointerX = event.clientX;
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!globeRuntime.dragging) return;
    globeRuntime.longitude -= (event.clientX - globeRuntime.pointerX) * .45;
    globeRuntime.pointerX = event.clientX;
    cancelAnimationFrame(globeRuntime.frame);
    drawGlobe();
  });
  const stopDragging = () => { globeRuntime.dragging = false; };
  canvas.addEventListener("pointerup", stopDragging);
  canvas.addEventListener("pointercancel", stopDragging);
  new ResizeObserver(() => { cancelAnimationFrame(globeRuntime.frame); drawGlobe(); }).observe(canvas);
  new IntersectionObserver(([entry]) => {
    globeRuntime.visible = entry.isIntersecting;
    if (globeRuntime.visible) renderMap();
    else cancelAnimationFrame(globeRuntime.frame);
  }, { threshold: .05 }).observe(stage);
}

function bindEvents() {
  $("#language-toggle").addEventListener("click", () => { state.lang = state.lang === "en" ? "tr" : "en"; applyLanguage(); });
  $("#theme-toggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("fyrora-theme", state.theme); } catch (_) { /* Keep the in-memory theme. */ }
    applyTheme();
    drawSensorMap();
  });
  $("#region-select").addEventListener("change", (event) => { state.regionId = event.target.value; renderCalendar(); renderEvidence(); renderMap(); });
  $("#year-select").addEventListener("change", (event) => { state.year = Number(event.target.value); renderCalendar(); renderMap(); });
  document.querySelectorAll('input[name="daynight"]').forEach((input) => input.addEventListener("change", (event) => { state.daynight = event.target.value; renderCalendar(); renderMap(); }));
  $("#download-filtered").addEventListener("click", downloadFiltered);
  $("#aoi-form").addEventListener("submit", runAoi);
  $("#aoi-download").addEventListener("click", downloadAoi);
  ["#aoi-west", "#aoi-east", "#aoi-south", "#aoi-north"].forEach((selector) => $(selector).addEventListener("input", renderAoiMap));
  const presets = {
    full: [-9.5, 37.0, -5.5, 43.0],
    portugal: [-9.5, 37.0, -6.0, 42.2],
    galicia: [-9.3, 41.8, -6.8, 43.0],
  };
  document.querySelectorAll("[data-aoi-preset]").forEach((button) => button.addEventListener("click", () => {
    const [west, south, east, north] = presets[button.dataset.aoiPreset];
    $("#aoi-west").value = west; $("#aoi-east").value = east;
    $("#aoi-south").value = south; $("#aoi-north").value = north;
    renderAoiMap();
  }));
  $("#open-europe").addEventListener("click", () => {
    state.regionId = state.data.europePilot.regionId;
    state.year = state.data.europePilot.year;
    state.daynight = "D";
    renderSelectors();
    renderCalendar();
    renderMap();
    $("#explorer").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  ["#judge-trigger", "#hero-judge-trigger", "#brief-judge-trigger"].forEach((selector) => $(selector).addEventListener("click", startJudgeTour));
  $("#tour-close").addEventListener("click", closeJudgeTour);
  $("#tour-back").addEventListener("click", previousJudgeStep);
  $("#tour-next").addEventListener("click", nextJudgeStep);
  const sensorCanvas = $("#sensor-map");
  sensorCanvas.addEventListener("pointermove", (event) => {
    const rect = sensorCanvas.getBoundingClientRect();
    const x = event.clientX - rect.left; const y = event.clientY - rect.top;
    const closest = sensorRuntime.points.reduce((best, point) => {
      const distance = (point.x - x) ** 2 + (point.y - y) ** 2;
      return !best || distance < best.distance ? { point, distance } : best;
    }, null);
    if (closest && closest.distance < 900) {
      const cell = closest.point.cell;
      $("#sensor-cell-detail").textContent = `${cell.h3} · ${number(cell.count)} ${state.lang === "tr" ? "kayıt" : "records"}`;
    }
  });
  sensorCanvas.addEventListener("pointerleave", () => { $("#sensor-cell-detail").textContent = t("mapCellHint"); });
  new ResizeObserver(drawSensorMap).observe(sensorCanvas);
  $("#victoria-date").addEventListener("change", renderVictoriaPoints);
  $("#victoria-daynight").addEventListener("change", renderVictoriaPoints);
  document.querySelectorAll('input[name="victoria-product"]').forEach((input) => input.addEventListener("change", renderVictoriaPoints));
  $("#victoria-date-range").addEventListener("input", (event) => setVictoriaDate(event.target.value));
  $("#victoria-prev").addEventListener("click", () => stepVictoriaDate(-1));
  $("#victoria-next").addEventListener("click", () => stepVictoriaDate(1));
  $("#victoria-play").addEventListener("click", toggleVictoriaPlayback);
  new IntersectionObserver(([entry], observer) => {
    if (entry.isIntersecting) { loadVictoriaExplorer(); observer.disconnect(); }
  }, { rootMargin: "400px" }).observe($("#victoria-map"));
  document.addEventListener("keydown", (event) => {
    if ($("#judge-tour").hidden) return;
    if (event.key === "Escape") closeJudgeTour();
    if (event.key === "ArrowRight") nextJudgeStep();
    if (event.key === "ArrowLeft") previousJudgeStep();
  });
  bindStudyMapMotion();
}

async function initialize() {
  try {
    applyTheme();
    const [response, aoiResponse, landResponse] = await Promise.all([
      fetch("data/dashboard.json"),
      fetch("data/western_iberia_aoi.json"),
      fetch("data/ne_110m_land.geojson"),
    ]);
    if (!response.ok || !aoiResponse.ok || !landResponse.ok) throw new Error(`Data request failed: ${response.status}/${aoiResponse.status}/${landResponse.status}`);
    [state.data, state.aoiData, state.landData] = await Promise.all([response.json(), aoiResponse.json(), landResponse.json()]);
    Object.assign(state, state.data.meta.defaultView);
    $("#stat-observations").textContent = number(state.data.meta.observations);
    $("#stat-passes").textContent = number(state.data.meta.matchedPasses);
    $("#stat-years").textContent = number(state.data.meta.years.length);
    $("#stat-improvement").textContent = `${number(state.data.meta.countWapeImprovementPct, 1)}%`;
    renderSelectors();
    bindEvents();
    applyLanguage();
    enableLiveReload();
  } catch (error) {
    document.body.innerHTML = `<main class="section-shell"><h1>Fyrora</h1><p>Dashboard data could not be loaded.</p><pre>${String(error)}</pre></main>`;
  }
}

initialize();
