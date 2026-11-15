# QORVEX
### Global Active-Fire Intelligence Platform

**NASA Space Apps Challenge 2026 — Challenge 09**

QORVEX is a data-driven platform designed to explore, harmonize, and analyze satellite-based active-fire detections. It brings together observations from NASA's MODIS and VIIRS instruments to support geographical exploration, spatial analysis, temporal analysis, and the investigation of fire-activity patterns.

The project aims to transform heterogeneous satellite observations into a structured analytical environment that makes fire-related information easier to explore and interpret.

---

## 1. Project Objectives

QORVEX aims to:

- Integrate active-fire detection records from multiple satellite products.
- Harmonize heterogeneous observations into a consistent data structure while preserving sensor-specific information.
- Explore the geographical distribution of recorded detections.
- Analyze spatial patterns using the H3 hierarchical hexagonal spatial indexing system.
- Investigate temporal variations and unusual detection patterns.
- Provide interactive visualizations to support exploration and interpretation.

## 2. Data Sources

QORVEX uses NASA Fire Information for Resource Management System (FIRMS) data.

The current collection pipeline supports three historical standard-processing products:

| Satellite product | Instrument |
|---|---|
| MODIS_SP | MODIS |
| VIIRS_SNPP_SP | VIIRS |
| VIIRS_NOAA20_SP | VIIRS |

The system preserves important product-specific attributes, including:

- Acquisition timestamps
- Geographic coordinates
- Satellite and sensor identifiers
- Confidence information
- Fire Radiative Power (FRP)
- Sensor-specific brightness temperatures
- Scan and track information
- Processing and source provenance

**Data access:** [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)

## 3. Core Capabilities

### 3.1 Data Collection and Harmonization

The configurable FIRMS collector supports geographical areas, date ranges, multiple satellite products, and configurable collection chunks.

The harmonization module transforms heterogeneous FIRMS records into a common schema while retaining the original sensor-specific measurements and relevant metadata.

### 3.2 Geographic Exploration

The Geographic Map dashboard provides interactive exploration of satellite detection records.

Its capabilities include:

- Geographical visualization of detections
- Date and satellite-product filtering
- Detection-density exploration
- Heatmap and hexagon-based visualization
- Cross-sensor evidence exploration

### 3.3 H3 Spatial Analytics

QORVEX uses Uber's H3 hierarchical spatial indexing system to organize detection records into hexagonal geographic cells.

The analytical pipeline currently supports H3 resolutions 5, 7, 8, and 9.

This enables spatial aggregation and exploration at different geographic scales.

### 3.4 Temporal and Anomaly Analysis

The project includes analytical components for:

- Daily and monthly detection patterns
- Seasonal variations
- Historical detection anomalies
- Anomaly episode analysis
- Cross-sensor temporal comparisons

These analyses are intended to identify unusual patterns in recorded detections, not to establish confirmed wildfire events.

### 3.5 Interactive Dashboard

The application is built with Streamlit and includes:

- Main dashboard
- Geographic Map
- H3 Spatial Analytics

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core development |
| pandas | Data manipulation |
| GeoPandas | Geospatial data processing |
| PyArrow | Parquet storage |
| H3 | Hierarchical spatial indexing |
| Plotly | Interactive visualization |
| PyDeck | Geospatial visualization |
| Streamlit | Interactive application |
| pytest | Automated testing |
| uv | Python project and dependency management |

## 5. Project Architecture

```text
NASA-2026-QORVEX-Challenge-09/
│
├── app/
│   ├── dashboard.py
│   ├── data_access.py
│   └── pages/
│       ├── 2_Geographic_Map.py
│       └── 3_H3_Spatial_Analytics.py
│
├── scripts/
│   ├── collect_firms_2024.py
│   ├── build_analytical_dataset_2024.py
│   ├── build_victoria_2024_filtered.py
│   ├── build_global_test_2024.py
│   ├── analyze_*.py
│   ├── explore_victoria_2024.py
│   └── validate_*.py
│
├── src/
│   └── qorvex/
│       ├── harmonize_firms.py
│       ├── spatial_index.py
│       ├── daily_aggregation.py
│       ├── geographic_filter.py
│       ├── anomaly_detection.py
│       ├── episode_detection.py
│       └── activity_calendar.py
│
├── tests/
│   ├── test_collect_firms_2024.py
│   ├── test_harmonize_firms.py
│   ├── test_spatial_index.py
│   └── test_daily_aggregation.py
│
├── reports/
├── pyproject.toml
├── uv.lock
├── LICENSE
└── README.md
```

## 6. Installation

### Prerequisites

- Python 3.13 or later
- Git
- uv

Install uv following its official documentation:

https://docs.astral.sh/uv/

### Clone the repository

```powershell
git clone https://github.com/CSHub-Project/NASA-2026-QORVEX-Challenge-09.git
cd NASA-2026-QORVEX-Challenge-09
```

### Install dependencies

```powershell
uv sync --dev
```

## 7. Running QORVEX

Start the Streamlit application:

```powershell
uv run streamlit run app/dashboard.py
```

The application will be available at the local Streamlit address displayed in the terminal.

### Data configuration

QORVEX uses local datasets that are not included in the repository.

For the Parquet-based analytical dataset, configure:

```powershell
$env:QORVEX_PARQUET_DIR = "data/processed/victoria_2024_filtered"
```

For legacy CSV-based datasets, the dashboard can use:

```powershell
$env:QORVEX_DATA_DIR = "data"
```

The required dataset files must exist in the configured directories.

## 8. Running the FIRMS Collector

The collector requires a NASA FIRMS API key.

Configure it locally in PowerShell:

```powershell
$env:FIRMS_MAP_KEY = "YOUR_FIRMS_MAP_KEY"
```

Example configuration for a global collection:

```powershell
$env:QORVEX_AREA = "world"
$env:QORVEX_START_DATE = "2024-01-01"
$env:QORVEX_END_DATE = "2024-01-01"
$env:QORVEX_PRODUCTS = "MODIS_SP,VIIRS_SNPP_SP,VIIRS_NOAA20_SP"
$env:QORVEX_CHUNK_DAYS = "1"
```

Run:

```powershell
uv run python scripts/collect_firms_2024.py
```

The collector supports historical standard-processing products currently configured in the project. Check the NASA FIRMS documentation for product availability and API requirements.

**Never commit API keys or other credentials to the repository.**

## 9. Running Tests

Run the complete automated test suite:

```powershell
uv run pytest -q
```

The development test suite currently contains 58 passing tests.

## 10. Scientific Considerations and Limitations

QORVEX is designed around careful interpretation of satellite observations.

Important considerations include:

- A hotspot detection is not necessarily a confirmed wildfire.
- Multiple satellite detections may refer to the same underlying fire activity.
- A missing FIRMS record does not necessarily indicate an absence of fire activity.
- MODIS and VIIRS have different sensor characteristics and observation properties.
- MODIS numerical confidence values and VIIRS categorical confidence levels must retain their original meanings.
- FRP represents instantaneous radiative power in megawatts, not total energy released.
- Spatial and temporal co-occurrence does not independently establish that detections belong to the same fire event.

Consequently, QORVEX distinguishes recorded detection patterns from validated fire events and avoids treating exploratory indicators as confirmed measurements of wildfire severity.

## 11. Current Demonstration

The project includes a global FIRMS demonstration based on historical observations from **1 January 2024**.

The combined dataset contains:

| Product | Detection records |
|---|---:|
| MODIS_SP | 9,391 |
| VIIRS_SNPP_SP | 41,837 |
| VIIRS_NOAA20_SP | 47,587 |
| **Total** | **98,815** |

The demonstration includes global geographic visualization, harmonized records, H3 spatial indexing, and daily spatial aggregation.

These figures describe the records returned for the selected date and products; they do not represent complete global observation coverage or continuous global monitoring.

## 12. Future Development

Potential development directions include:

- Incremental data collection and recovery.
- More comprehensive observation-coverage assessment.
- Expanded satellite-product support.
- Improved cross-sensor association methods.
- More advanced temporal anomaly analysis.
- Additional geographical and analytical capabilities.

## 13. Licence

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

---

**QORVEX — NASA Space Apps Challenge 2026**