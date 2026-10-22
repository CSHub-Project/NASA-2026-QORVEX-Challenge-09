
"""QORVEX geographic explorer with anomaly-episode selection."""

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pydeck as pdk
import streamlit as st


DATA_DIR = Path(os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data"))
ACTIVITY_DIR = DATA_DIR / "activity_calendar"

FIRE_FILE = DATA_DIR / "victoria_fires_2024.csv"
BOUNDARY_FILE = DATA_DIR / "boundaries" / "victoria_boundary.geojson"
EPISODE_FILE = ACTIVITY_DIR / "victoria_anomaly_episodes_2024.csv"

PRODUCT_LABELS = {
    "MODIS_SP": "MODIS",
    "VIIRS_NOAA20_SP": "VIIRS NOAA-20",
    "VIIRS_SNPP_SP": "VIIRS Suomi-NPP",
}

PRODUCT_COLORS = {
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


st.set_page_config(
    page_title="QORVEX | Geographic Explorer",
    page_icon="🌏",
    layout="wide",
)


@st.cache_data
def load_detections(path: str) -> pd.DataFrame:
    """Load and validate the filtered satellite detections."""
    frame = pd.read_csv(path)

    required = {
        "latitude",
        "longitude",
        "timestamp_utc",
        "sensor",
        "source_product",
    }
    missing = required - set(frame.columns)

    if missing:
        raise ValueError(
            f"The detection file is missing columns: {sorted(missing)}"
        )

    frame["latitude"] = pd.to_numeric(
        frame["latitude"], errors="coerce"
    )
    frame["longitude"] = pd.to_numeric(
        frame["longitude"], errors="coerce"
    )
    frame["timestamp_utc"] = pd.to_datetime(
        frame["timestamp_utc"], errors="coerce", utc=True
    )

    valid = (
        frame["latitude"].between(-90, 90)
        & frame["longitude"].between(-180, 180)
        & frame["timestamp_utc"].notna()
    )
    frame = frame.loc[valid].copy()

    frame["date"] = frame["timestamp_utc"].dt.date
    frame["product_label"] = (
        frame["source_product"]
        .map(PRODUCT_LABELS)
        .fillna(frame["source_product"])
    )
    frame["color"] = frame["source_product"].map(
        PRODUCT_COLORS
    ).apply(
        lambda value: value
        if isinstance(value, list)
        else [120, 120, 120, 190]
    )

    return frame.reset_index(drop=True)


@st.cache_data
def load_boundary(path: str) -> dict:
    """Load the Victoria land boundary as GeoJSON."""
    boundary = gpd.read_file(path)

    if boundary.empty:
        raise ValueError("The Victoria boundary file is empty.")

    if boundary.crs is None:
        raise ValueError("The Victoria boundary has no declared CRS.")

    boundary = boundary.to_crs("EPSG:4326")

    if "FEATURE_TY" in boundary.columns:
        boundary = boundary[
            boundary["FEATURE_TY"].astype(str).str.lower() != "sea"
        ].copy()

    boundary = boundary[
        boundary.geometry.notna() & ~boundary.geometry.is_empty
    ].copy()

    if boundary.empty:
        raise ValueError("No usable land geometries remain in the boundary.")

    return boundary.__geo_interface__


@st.cache_data
def load_episodes(path: str) -> pd.DataFrame:
    """Load and validate the anomaly-episode report."""
    episodes = pd.read_csv(path)

    required = {
        "episode_id",
        "start_date",
        "end_date",
        "duration_days",
        "total_detections",
        "peak_daily_detections",
        "peak_date",
        "overall_anomaly_days",
        "modis_anomaly_days",
        "viirs_noaa20_anomaly_days",
        "viirs_snpp_anomaly_days",
        "multi_product_anomaly_days",
        "multi_product_support_pct",
        "anomaly_reasons",
    }

    missing = required - set(episodes.columns)
    if missing:
        raise ValueError(
            f"The episode report is missing columns: {sorted(missing)}"
        )

    if episodes["episode_id"].duplicated().any():
        raise ValueError("The episode report contains duplicate episode IDs.")

    for column in ["start_date", "end_date", "peak_date"]:
        episodes[column] = pd.to_datetime(
            episodes[column], errors="coerce"
        )

    if episodes[["start_date", "end_date", "peak_date"]].isna().any().any():
        raise ValueError("The episode report contains invalid dates.")

    if (episodes["start_date"] > episodes["end_date"]).any():
        raise ValueError("An episode starts after its end date.")

    numeric_columns = [
        "duration_days",
        "total_detections",
        "peak_daily_detections",
        "overall_anomaly_days",
        "modis_anomaly_days",
        "viirs_noaa20_anomaly_days",
        "viirs_snpp_anomaly_days",
        "multi_product_anomaly_days",
        "multi_product_support_pct",
    ]

    for column in numeric_columns:
        episodes[column] = pd.to_numeric(
            episodes[column], errors="coerce"
        )

    if episodes[numeric_columns].isna().any().any():
        raise ValueError("The episode report contains invalid numeric values.")

    return episodes.sort_values("start_date").reset_index(drop=True)


st.title("🌏 QORVEX — Geographic Explorer")
st.caption(
    "Explore harmonized MODIS and VIIRS active-fire detections, "
    "including the locations observed during anomaly episodes."
)

required_files = [FIRE_FILE, BOUNDARY_FILE, EPISODE_FILE]
missing_files = [path for path in required_files if not path.is_file()]

if missing_files:
    st.error("Required data files are missing:")
    for path in missing_files:
        st.code(str(path))
    st.info(
        "Check QORVEX_DATA_DIR and ensure the filtered detections, "
        "Victoria boundary, and anomaly-episode report are available."
    )
    st.stop()

try:
    detections = load_detections(str(FIRE_FILE))
    boundary_geojson = load_boundary(str(BOUNDARY_FILE))
    episodes = load_episodes(str(EPISODE_FILE))
except (ValueError, OSError, ImportError) as error:
    st.error(f"Could not load geographic data: {error}")
    st.stop()

if detections.empty:
    st.warning("No valid detection records are available.")
    st.stop()

if episodes.empty:
    st.warning("The anomaly-episode report contains no episodes.")
    st.stop()


# Sidebar controls
st.sidebar.header("Explore detections")

time_mode = st.sidebar.radio(
    "Time selection",
    options=["All dates", "Anomaly episode"],
    index=0,
)

selected_episode = None

if time_mode == "Anomaly episode":
    episode_options = episodes["episode_id"].tolist()

    selected_episode_id = st.sidebar.selectbox(
        "Select anomaly episode",
        options=episode_options,
        index=0,
        format_func=lambda episode_id: (
            lambda row: (
                f"{row['episode_id']} · "
                f"{row['start_date']:%d %b}–"
                f"{row['end_date']:%d %b %Y} · "
                f"{int(row['duration_days'])} day(s)"
            )
        )(episodes.loc[episodes["episode_id"] == episode_id].iloc[0]),
    )

    selected_episode = episodes.loc[
        episodes["episode_id"] == selected_episode_id
    ].iloc[0]

    effective_start = selected_episode["start_date"].date()
    effective_end = selected_episode["end_date"].date()

    st.sidebar.caption(
        "The selected episode determines the date range. "
        "The date picker is not used in episode mode."
    )
else:
    minimum_date = detections["date"].min()
    maximum_date = detections["date"].max()

    date_range = st.sidebar.date_input(
        "Detection date range",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )

    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        st.info("Select both a start date and an end date.")
        st.stop()

    effective_start, effective_end = date_range

    if effective_start > effective_end:
        st.error("The start date must not be later than the end date.")
        st.stop()

available_products = [
    product
    for product in PRODUCT_LABELS
    if product in set(detections["source_product"])
]

selected_products = st.sidebar.multiselect(
    "Satellite products",
    options=available_products,
    default=available_products,
    format_func=lambda product: PRODUCT_LABELS[product],
)

map_mode = st.sidebar.radio(
    "Map visualization",
    options=[
        "Individual detections",
        "Density heatmap",
        "Aggregated hexagonal grid",
    ],
    index=0,
)

show_boundary = st.sidebar.checkbox(
    "Show Victoria boundary",
    value=True,
)

show_all_points = st.sidebar.checkbox(
    "Show every detection in point mode",
    value=True,
    help="Only applies to individual-detection mode.",
)

maximum_map_points = st.sidebar.slider(
    "Maximum displayed points",
    min_value=1000,
    max_value=50000,
    value=20000,
    step=1000,
    disabled=show_all_points or map_mode != "Individual detections",
)

heatmap_radius = st.sidebar.slider(
    "Heatmap radius (pixels)",
    min_value=10,
    max_value=60,
    value=30,
    step=5,
    disabled=map_mode != "Density heatmap",
)

hexagon_radius = st.sidebar.slider(
    "Hexagon radius (metres)",
    min_value=1000,
    max_value=20000,
    value=5000,
    step=1000,
    disabled=map_mode != "Aggregated hexagonal grid",
)


# Apply date and product filters to the full detection dataset.
filtered = detections[
    detections["date"].between(effective_start, effective_end)
    & detections["source_product"].isin(selected_products)
].copy()

if filtered.empty:
    st.warning(
        "No detections match the selected time period and satellite products."
    )
    st.stop()


# Episode metadata
if selected_episode is not None:
    st.subheader(f"Anomaly episode {selected_episode['episode_id']}")

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
        st.dataframe(evidence, hide_index=True, use_container_width=True)

    st.caption(
        "The episode report summarizes anomaly activity across the period. "
        "The map below includes all matching detection records in that "
        "date range, not only records from days or products that triggered "
        "an anomaly flag."
    )


# Summary metrics describe the complete filtered dataset.
st.subheader("Geographic overview")

col1, col2, col3 = st.columns(3)
col1.metric("Matching detection records", f"{len(filtered):,}")
col2.metric("Satellite products", filtered["source_product"].nunique())
col3.metric("Dates represented", f"{filtered['date'].nunique():,}")

st.caption(
    f"Date range: {effective_start:%d %b %Y} – {effective_end:%d %b %Y}. "
    "Detection records are not unique fires or burned area."
)


# Point mode can use a reproducible sample. Density and grid modes use
# all records that match the active filters.
if (
    map_mode == "Individual detections"
    and not show_all_points
    and len(filtered) > maximum_map_points
):
    map_data = filtered.sample(
        n=maximum_map_points,
        random_state=42,
    ).copy()
    st.caption(
        f"Displaying {len(map_data):,} sampled points out of "
        f"{len(filtered):,} matching records. Summary metrics use all records."
    )
else:
    map_data = filtered.copy()
    st.caption(f"Map input: {len(map_data):,} matching records.")


# Point tooltip fields.
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
        "<b>Brightness:</b> {brightness_raw}<br/>"
        "<b>MODIS Band 31 brightness:</b> {brightness_11um_raw}<br/>"
        "<b>VIIRS I4 brightness:</b> {viirs_bright_ti4}<br/>"
        "<b>VIIRS I5 brightness:</b> {viirs_bright_ti5}<br/>"
        "<b>Day/night:</b> {daynight_raw}"
    ),
    "style": {
        "backgroundColor": "#182334",
        "color": "white",
        "fontSize": "12px",
        "padding": "10px",
    },
}


# Construct the map.
layers = []

if show_boundary:
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            data=boundary_geojson,
            stroked=True,
            filled=True,
            get_fill_color=[40, 120, 170, 12],
            get_line_color=[20, 75, 115, 220],
            line_width_min_pixels=1.5,
            get_line_width=2,
            pickable=False,
        )
    )

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
            radius_pixels=heatmap_radius,
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
            radius=hexagon_radius,
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

view_state = pdk.ViewState(
    latitude=float(filtered["latitude"].median()),
    longitude=float(filtered["longitude"].median()),
    zoom=6,
    pitch=0,
    bearing=0,
)

deck = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=tooltip if map_mode == "Individual detections" else True,
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
)

st.subheader("Detection locations")

if map_mode == "Individual detections":
    st.caption(
        "Point colors identify the satellite product. Overlapping points "
        "may represent repeated or coincident detections."
    )
elif map_mode == "Density heatmap":
    st.caption(
        "Brighter areas indicate greater local concentration of detection "
        "records. The result depends on radius and zoom level."
    )
else:
    st.caption(
        "Hexagonal cells aggregate matching detection records into spatial "
        "cells. Cell counts are not counts of unique fires."
    )

st.pydeck_chart(deck, use_container_width=True)


# Product-level summary for the active date and product filters.
st.subheader("Detection records by product")

product_summary = (
    filtered.groupby("product_label", as_index=False)
    .agg(
        detection_records=("source_product", "size"),
        first_date=("date", "min"),
        last_date=("date", "max"),
    )
    .sort_values("detection_records", ascending=False)
)

st.dataframe(
    product_summary,
    use_container_width=True,
    hide_index=True,
)

with st.expander("Inspect matching detection records"):
    display_columns = [
        column
        for column in [
            "timestamp_utc",
            "latitude",
            "longitude",
            "sensor",
            "source_product",
            "confidence_raw",
            "frp_mw",
            "brightness_raw",
            "brightness_11um_raw",
            "viirs_bright_ti4",
            "viirs_bright_ti5",
            "daynight_raw",
        ]
        if column in filtered.columns
    ]

    st.dataframe(
        filtered[display_columns].sort_values(
            "timestamp_utc", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "Active-fire detections indicate satellite-observed thermal anomalies. "
    "An anomaly episode is a period of unusual activity, not necessarily "
    "one wildfire or a fire perimeter."
)
