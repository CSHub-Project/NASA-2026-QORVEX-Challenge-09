"""QORVEX Geographic Explorer using corrected Parquet and optional legacy CSV."""

import os
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from data_access import load_detections as load_parquet_detections

DATA_DIR = Path(os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data"))
BOUNDARY_FILE = DATA_DIR / "boundaries" / "victoria_boundary.geojson"
EPISODE_FILE = DATA_DIR / "activity_calendar" / "victoria_anomaly_episodes_2024.csv"

PARQUET_DATASET_LABEL = "Victoria 2024 — Corrected Parquet"

LABELS = {
    "MODIS_SP": "MODIS",
    "VIIRS_NOAA20_SP": "VIIRS NOAA-20",
    "VIIRS_SNPP_SP": "VIIRS Suomi-NPP",
}
COLORS = {
    "MODIS_SP": [30, 120, 220, 190],
    "VIIRS_NOAA20_SP": [230, 90, 40, 190],
    "VIIRS_SNPP_SP": [30, 170, 110, 190],
}
HEATMAP_COLORS = [
    [65, 182, 196, 0],
    [127, 205, 187, 100],
    [255, 255, 120, 150],
    [253, 141, 60, 200],
    [189, 0, 38, 230],
]
OPTIONAL_COLUMNS = [
    "confidence_raw", "frp_mw", "brightness_raw",
    "brightness_11um_raw", "viirs_bright_ti4",
    "viirs_bright_ti5", "daynight_raw", "h3_res7",
]

st.set_page_config(
    page_title="QORVEX | Geographic Explorer",
    page_icon="🌏",
    layout="wide",
)


@st.cache_data
def discover_datasets(directory: str) -> list[str]:
    """Discover legacy harmonized CSV datasets."""
    root = Path(directory)
    paths = set(root.glob("harmonized_fires*.csv"))
    paths.update(root.glob("victoria_fires_2024.csv"))
    return sorted(
        (str(path.resolve()) for path in paths if path.is_file()),
        key=lambda path: (
            Path(path).name != "victoria_fires_2024.csv",
            Path(path).name.lower(),
        ),
    )


@st.cache_data
def load_legacy_detections(path: str) -> pd.DataFrame:
    """Load a legacy harmonized CSV dataset."""
    df = pd.read_csv(path)
    required = {"latitude", "longitude", "timestamp_utc", "source_product"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    return df


@st.cache_data
def load_boundary(path: str) -> dict:
    """Load Victoria land boundary and convert it to WGS84 GeoJSON."""
    import geopandas as gpd

    frame = gpd.read_file(path)
    if frame.empty or frame.crs is None:
        raise ValueError("Boundary is empty or has no declared CRS.")
    frame = frame.to_crs("EPSG:4326")
    if "FEATURE_TY" in frame.columns:
        frame = frame[
            frame["FEATURE_TY"].astype(str).str.lower() != "sea"
        ].copy()
    frame = frame[
        frame.geometry.notna() & ~frame.geometry.is_empty
    ].copy()
    if frame.empty:
        raise ValueError("No usable land geometries remain in boundary.")
    return frame.__geo_interface__


@st.cache_data
def load_episodes(path: str) -> pd.DataFrame:
    """Load and validate the optional legacy anomaly-episode report."""
    episodes = pd.read_csv(path)
    required = {
        "episode_id", "start_date", "end_date", "duration_days",
        "total_detections", "peak_daily_detections", "peak_date",
        "overall_anomaly_days", "modis_anomaly_days",
        "viirs_noaa20_anomaly_days", "viirs_snpp_anomaly_days",
        "multi_product_anomaly_days", "multi_product_support_pct",
        "anomaly_reasons",
    }
    missing = required - set(episodes.columns)
    if missing:
        raise ValueError(
            f"The episode report is missing columns: {sorted(missing)}"
        )
    if episodes["episode_id"].duplicated().any():
        raise ValueError("The episode report contains duplicate episode IDs.")
    for column in ("start_date", "end_date", "peak_date"):
        episodes[column] = pd.to_datetime(
            episodes[column], errors="coerce"
        )
    if episodes[["start_date", "end_date", "peak_date"]].isna().any().any():
        raise ValueError("The episode report contains invalid dates.")
    if (episodes["start_date"] > episodes["end_date"]).any():
        raise ValueError("An episode starts after its end date.")
    numeric_columns = [
        "duration_days", "total_detections", "peak_daily_detections",
        "overall_anomaly_days", "modis_anomaly_days",
        "viirs_noaa20_anomaly_days", "viirs_snpp_anomaly_days",
        "multi_product_anomaly_days", "multi_product_support_pct",
    ]
    for column in numeric_columns:
        episodes[column] = pd.to_numeric(
            episodes[column], errors="coerce"
        )
    if episodes[numeric_columns].isna().any().any():
        raise ValueError("The episode report contains invalid numeric values.")
    return episodes.sort_values("start_date").reset_index(drop=True)


def prepare_detections(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize fields used by the map for Parquet and CSV records."""
    result = df.copy()
    required = {"latitude", "longitude", "timestamp_utc", "source_product"}
    missing = required - set(result.columns)
    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {sorted(missing)}"
        )

    result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")
    result["timestamp_utc"] = pd.to_datetime(
        result["timestamp_utc"], errors="coerce", utc=True
    )
    valid = (
        result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
        & result["timestamp_utc"].notna()
        & result["source_product"].notna()
    )
    result = result.loc[valid].copy()
    result["date"] = result["timestamp_utc"].dt.date
    result["product_label"] = (
        result["source_product"].map(LABELS)
        .fillna(result["source_product"].astype(str))
    )
    if "sensor" not in result.columns:
        result["sensor"] = (
            result["source_product"].astype(str).str.replace(
                "_SP", "", regex=False
            )
        )
    for column in OPTIONAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    result["color"] = result["source_product"].map(COLORS).apply(
        lambda value: value
        if isinstance(value, list)
        else [120, 120, 120, 190]
    )
    return result.reset_index(drop=True)


# ---------------------------------------------------------------------
# Header and data source
# ---------------------------------------------------------------------

st.title("🌏 QORVEX — Geographic Explorer")
st.caption(
    "Explore harmonized MODIS and VIIRS detection records, "
    "spatial density and geographic patterns."
)
st.sidebar.header("Explore detections")

data_source = st.sidebar.radio(
    "Data source",
    [PARQUET_DATASET_LABEL, "Legacy CSV datasets"],
)
selected_path = None
is_corrected_parquet = data_source == PARQUET_DATASET_LABEL

try:
    if is_corrected_parquet:
        detections = load_parquet_detections()
        dataset_label = PARQUET_DATASET_LABEL
        st.sidebar.success("Corrected Parquet dataset loaded")
        st.sidebar.caption(
            "Victoria, Australia · 2024 · 57,305 detection records"
        )
        is_victoria_dataset = True
    else:
        datasets = discover_datasets(str(DATA_DIR))
        if not datasets:
            st.error(
                f"No harmonized CSV files found in {DATA_DIR}. "
                "Set QORVEX_DATA_DIR or place harmonized_fires*.csv there."
            )
            st.stop()
        default_dataset = next(
            (
                path for path in datasets
                if Path(path).name == "victoria_fires_2024.csv"
            ),
            datasets[0],
        )
        selected_path = st.sidebar.selectbox(
            "Harmonized dataset",
            datasets,
            index=datasets.index(default_dataset),
            format_func=lambda path: Path(path).name,
        )
        detections = load_legacy_detections(selected_path)
        dataset_label = Path(selected_path).name
        is_victoria_dataset = (
            Path(selected_path).name == "victoria_fires_2024.csv"
        )
    detections = prepare_detections(detections)
except (OSError, ValueError, KeyError, RuntimeError) as exc:
    st.error(f"Could not load the selected dataset: {exc}")
    st.stop()

if detections.empty:
    st.warning("No valid detection records are available.")
    st.stop()


# ---------------------------------------------------------------------
# Geographic scope
# ---------------------------------------------------------------------

scope_options = (
    ["Victoria (dataset extent)", "Bounding box"]
    if is_corrected_parquet
    else ["World", "Bounding box"]
)
scope = st.sidebar.radio(
    "Geographic scope", scope_options, horizontal=True
)

if scope == "Bounding box":
    with st.sidebar.expander("Bounding-box coordinates", expanded=True):
        st.caption("West, south, east, north in decimal degrees.")
        west = st.number_input(
            "West longitude", -180.0, 180.0, 140.9, 0.1
        )
        south = st.number_input(
            "South latitude", -90.0, 90.0, -39.2, 0.1
        )
        east = st.number_input(
            "East longitude", -180.0, 180.0, 150.1, 0.1
        )
        north = st.number_input(
            "North latitude", -90.0, 90.0, -33.9, 0.1
        )
    if west >= east or south >= north:
        st.sidebar.error("Require west < east and south < north.")
        st.stop()
else:
    west, south, east, north = -180.0, -90.0, 180.0, 90.0
    if not is_corrected_parquet:
        st.sidebar.caption(
            "World displays all records in the selected CSV; "
            "it does not fetch additional global data."
        )

scoped = detections.loc[
    detections["longitude"].between(west, east)
    & detections["latitude"].between(south, north)
].copy()
if scoped.empty:
    st.warning("No detections match the geographic scope.")
    st.stop()

minimum_date = scoped["date"].min()
maximum_date = scoped["date"].max()


# ---------------------------------------------------------------------
# Optional legacy anomaly episodes
# ---------------------------------------------------------------------

episodes = pd.DataFrame()
episode_report_available = (
    not is_corrected_parquet
    and is_victoria_dataset
    and EPISODE_FILE.is_file()
)
if episode_report_available:
    try:
        episodes = load_episodes(str(EPISODE_FILE))
    except (OSError, ValueError, KeyError) as exc:
        st.sidebar.warning(
            f"Legacy anomaly-episode report could not be loaded: {exc}"
        )
elif is_corrected_parquet:
    st.sidebar.info(
        "The legacy anomaly-episode report is not automatically "
        "applied to the corrected Parquet dataset."
    )
elif is_victoria_dataset:
    st.sidebar.info(
        "The Victoria anomaly-episode report was not found. "
        "All-date exploration is still available."
    )

selected_episode = None
time_mode = "All dates"
if episode_report_available and not episodes.empty:
    time_mode = st.sidebar.radio(
        "Time selection", ["All dates", "Anomaly episode"], index=0
    )

if time_mode == "Anomaly episode":
    episode_ids = episodes["episode_id"].tolist()

    def episode_label(episode_id):
        row = episodes.loc[
            episodes["episode_id"] == episode_id
        ].iloc[0]
        return (
            f"{row['episode_id']} · "
            f"{row['start_date']:%d %b}–{row['end_date']:%d %b %Y} · "
            f"{int(row['duration_days'])} day(s)"
        )

    selected_episode_id = st.sidebar.selectbox(
        "Select anomaly episode",
        options=episode_ids,
        format_func=episode_label,
    )
    selected_episode = episodes.loc[
        episodes["episode_id"] == selected_episode_id
    ].iloc[0]
    effective_start = selected_episode["start_date"].date()
    effective_end = selected_episode["end_date"].date()
    st.sidebar.caption(
        "The selected episode determines the date range."
    )
else:
    date_range = st.sidebar.date_input(
        "Detection date range",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )
    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        st.info("Select both a start and an end date.")
        st.stop()
    effective_start, effective_end = date_range
    if effective_start > effective_end:
        st.error("Start date must not be later than end date.")
        st.stop()


# ---------------------------------------------------------------------
# Product and visualization controls
# ---------------------------------------------------------------------

products = sorted(
    scoped["source_product"].dropna().astype(str).unique()
)
selected_products = st.sidebar.multiselect(
    "Satellite products",
    products,
    default=products,
    format_func=lambda product: LABELS.get(product, product),
)
map_mode = st.sidebar.radio(
    "Map visualization",
    [
        "Individual detections",
        "Density heatmap",
        "Hexagonal density aggregation",
    ],
)

boundary_available = BOUNDARY_FILE.is_file()
show_boundary = st.sidebar.checkbox(
    "Show Victoria boundary",
    value=boundary_available and is_victoria_dataset,
    disabled=not boundary_available,
)
show_all = st.sidebar.checkbox(
    "Show every detection in point mode",
    value=True,
    disabled=map_mode != "Individual detections",
)
max_points = st.sidebar.slider(
    "Maximum displayed points",
    1000, 50000, 20000, 1000,
    disabled=show_all or map_mode != "Individual detections",
)
heat_radius = st.sidebar.slider(
    "Heatmap radius (pixels)",
    10, 60, 30, 5,
    disabled=map_mode != "Density heatmap",
)
hex_radius = st.sidebar.slider(
    "Hexagon radius (metres)",
    1000, 20000, 5000, 1000,
    disabled=map_mode != "Hexagonal density aggregation",
)


# ---------------------------------------------------------------------
# Apply date and product filters
# ---------------------------------------------------------------------

date_mask = scoped["date"].between(effective_start, effective_end)
product_mask = scoped["source_product"].isin(selected_products)
filtered = scoped.loc[date_mask & product_mask].copy()

if filtered.empty:
    st.warning(
        "No detections match the selected dates, area and products."
    )
    st.stop()


# ---------------------------------------------------------------------
# Selected episode metadata
# ---------------------------------------------------------------------

if selected_episode is not None:
    st.subheader(
        f"Legacy anomaly episode {selected_episode['episode_id']}"
    )
    st.write(
        f"**Period:** {selected_episode['start_date']:%d %B %Y} – "
        f"{selected_episode['end_date']:%d %B %Y}"
    )
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric(
        "Episode duration",
        f"{int(selected_episode['duration_days'])} day(s)",
    )
    metric2.metric(
        "Episode report total",
        f"{int(selected_episode['total_detections']):,}",
    )
    metric3.metric(
        "Peak daily detections",
        f"{int(selected_episode['peak_daily_detections']):,}",
    )
    metric4.metric(
        "Multi-product support",
        f"{selected_episode['multi_product_support_pct']:.1f}%",
    )
    st.write(
        f"**Peak date:** {selected_episode['peak_date']:%d %B %Y}"
    )
    st.write(
        f"**Anomaly reasons:** {selected_episode['anomaly_reasons']}"
    )
    evidence = pd.DataFrame(
        [
            {
                "Satellite product": "MODIS",
                "Anomaly days": int(selected_episode["modis_anomaly_days"]),
            },
            {
                "Satellite product": "VIIRS NOAA-20",
                "Anomaly days": int(
                    selected_episode["viirs_noaa20_anomaly_days"]
                ),
            },
            {
                "Satellite product": "VIIRS Suomi-NPP",
                "Anomaly days": int(
                    selected_episode["viirs_snpp_anomaly_days"]
                ),
            },
            {
                "Satellite product": "Multiple products",
                "Anomaly days": int(
                    selected_episode["multi_product_anomaly_days"]
                ),
            },
        ]
    )
    with st.expander("Inspect cross-sensor episode evidence"):
        st.dataframe(
            evidence, hide_index=True, use_container_width=True
        )
    st.caption(
        "This episode comes from the legacy anomaly report. It describes "
        "a statistical period of unusual detection activity, not a "
        "confirmed individual wildfire. The map shows matching records "
        "within the selected date range."
    )


# ---------------------------------------------------------------------
# Geographic overview
# ---------------------------------------------------------------------

st.subheader("Geographic overview")
metric1, metric2, metric3 = st.columns(3)
metric1.metric("Matching detection records", f"{len(filtered):,}")
metric2.metric(
    "Satellite products", f"{filtered['source_product'].nunique():,}"
)
metric3.metric("Dates represented", f"{filtered['date'].nunique():,}")
st.caption(
    f"{dataset_label} · {scope} · "
    f"{effective_start:%d %b %Y}–{effective_end:%d %b %Y}. "
    "Records are not unique fires or burned area."
)


# ---------------------------------------------------------------------
# Map data and tooltip
# ---------------------------------------------------------------------

if (
    map_mode == "Individual detections"
    and not show_all
    and len(filtered) > max_points
):
    map_data = filtered.sample(n=max_points, random_state=42).copy()
    st.caption(
        f"Showing {len(map_data):,} sampled points "
        f"from {len(filtered):,} matching records."
    )
else:
    map_data = filtered.copy()

map_data["timestamp_display"] = map_data[
    "timestamp_utc"
].dt.strftime("%Y-%m-%d %H:%M UTC")
map_data["latitude_display"] = map_data["latitude"].round(5)
map_data["longitude_display"] = map_data["longitude"].round(5)

tooltip = {
    "html": (
        "<b>Product:</b> {product_label}<br/>"
        "<b>Time:</b> {timestamp_display}<br/>"
        "<b>Latitude:</b> {latitude_display}<br/>"
        "<b>Longitude:</b> {longitude_display}<br/>"
        "<b>Sensor:</b> {sensor}<br/>"
        "<b>Confidence:</b> {confidence_raw}<br/>"
        "<b>FRP (MW):</b> {frp_mw}<br/>"
        "<b>MODIS brightness:</b> {brightness_raw}<br/>"
        "<b>MODIS Band 31:</b> {brightness_11um_raw}<br/>"
        "<b>VIIRS I4:</b> {viirs_bright_ti4}<br/>"
        "<b>VIIRS I5:</b> {viirs_bright_ti5}<br/>"
        "<b>Day/night:</b> {daynight_raw}"
    ),
    "style": {
        "backgroundColor": "#182334",
        "color": "white",
        "fontSize": "12px",
        "padding": "10px",
    },
}


# ---------------------------------------------------------------------
# Build and display map
# ---------------------------------------------------------------------

layers = []
if show_boundary and boundary_available:
    try:
        boundary = load_boundary(str(BOUNDARY_FILE))
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=boundary,
                stroked=True,
                filled=True,
                get_fill_color=[40, 120, 170, 12],
                get_line_color=[20, 75, 115, 220],
                line_width_min_pixels=1.5,
                get_line_width=2,
                pickable=False,
            )
        )
    except (OSError, ValueError, ImportError) as exc:
        st.warning(f"Could not load boundary: {exc}")

if map_mode == "Individual detections":
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_line_color=[255, 255, 255, 100],
            get_radius=800,
            radius_min_pixels=3,
            radius_max_pixels=12,
            pickable=True,
            auto_highlight=True,
            opacity=0.7,
        )
    )
elif map_mode == "Density heatmap":
    layers.append(
        pdk.Layer(
            "HeatmapLayer",
            data=filtered,
            get_position="[longitude, latitude]",
            get_weight=1,
            radius_pixels=heat_radius,
            intensity=1,
            threshold=0.05,
            color_range=HEATMAP_COLORS,
            pickable=False,
        )
    )
else:
    layers.append(
        pdk.Layer(
            "HexagonLayer",
            data=filtered,
            get_position="[longitude, latitude]",
            radius=hex_radius,
            elevation_scale=0,
            extruded=False,
            coverage=0.85,
            color_range=[
                [255, 237, 160],
                [254, 178, 76],
                [253, 141, 60],
                [240, 59, 32],
                [189, 0, 38],
            ],
            opacity=0.8,
            pickable=True,
            auto_highlight=True,
        )
    )

view = pdk.ViewState(
    latitude=float(filtered["latitude"].median()),
    longitude=float(filtered["longitude"].median()),
    zoom=6 if is_victoria_dataset else 2,
    pitch=0,
    bearing=0,
)
deck = pdk.Deck(
    layers=layers,
    initial_view_state=view,
    tooltip=tooltip if map_mode == "Individual detections" else True,
    map_style=(
        "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    ),
)
st.subheader("Detection locations")
st.pydeck_chart(deck, use_container_width=True)


# ---------------------------------------------------------------------
# Product summary and record inspection
# ---------------------------------------------------------------------

st.subheader("Detection records by product")
summary = (
    filtered.assign(
        product_label=filtered["source_product"]
        .map(LABELS)
        .fillna(filtered["source_product"])
    )
    .groupby("product_label", as_index=False)
    .agg(
        detection_records=("source_product", "size"),
        first_date=("date", "min"),
        last_date=("date", "max"),
    )
    .sort_values("detection_records", ascending=False)
)
st.dataframe(summary, use_container_width=True, hide_index=True)

with st.expander("Inspect matching detection records"):
    columns = [
        column for column in [
            "timestamp_utc", "latitude", "longitude", "sensor",
            "source_product", "confidence_raw", "frp_mw",
            "brightness_raw", "brightness_11um_raw",
            "viirs_bright_ti4", "viirs_bright_ti5",
            "daynight_raw", "h3_res7",
        ]
        if column in filtered.columns
    ]
    st.dataframe(
        filtered[columns].sort_values(
            "timestamp_utc", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------
# Scientific notes
# ---------------------------------------------------------------------

st.caption(
    "The corrected Parquet dataset contains filtered FIRMS detection "
    "records for Victoria, Australia, during 2024. A detection record "
    "is not necessarily a unique fire. The absence of a record does not "
    "establish zero fire activity or valid satellite observation coverage. "
    "The hexagonal density layer is a map aggregation of points, not the "
    "precomputed H3 resolution-7 daily activity table. Legacy anomaly "
    "episodes, where available, are statistical activity periods, not "
    "confirmed individual wildfires or fire perimeters."
)
