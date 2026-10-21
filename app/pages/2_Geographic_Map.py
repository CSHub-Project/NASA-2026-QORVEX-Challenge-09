
"""Interactive geographic and density explorer for QORVEX."""

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pydeck as pdk
import streamlit as st


DATA_DIR = Path(os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data"))
FIRE_FILE = DATA_DIR / "victoria_fires_2024.csv"
BOUNDARY_FILE = DATA_DIR / "boundaries" / "victoria_boundary.geojson"

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
    """Load and validate filtered satellite detections."""
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
    """Load the Victoria boundary as GeoJSON."""
    boundary = gpd.read_file(path)

    if boundary.empty:
        raise ValueError("The Victoria boundary file is empty.")

    if boundary.crs is None:
        raise ValueError("The Victoria boundary has no declared CRS.")

    boundary = boundary.to_crs("EPSG:4326")

    # Keep mainland and island land features, excluding the sea feature.
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


st.title("🌏 QORVEX — Geographic Explorer")
st.caption(
    "Explore harmonized MODIS and VIIRS active-fire detections "
    "within Victoria during 2024."
)

missing_files = [
    path for path in [FIRE_FILE, BOUNDARY_FILE] if not path.is_file()
]

if missing_files:
    st.error("Required geographic data files are missing.")
    for path in missing_files:
        st.code(str(path))
    st.stop()

try:
    detections = load_detections(str(FIRE_FILE))
    boundary_geojson = load_boundary(str(BOUNDARY_FILE))
except (ValueError, OSError, ImportError) as error:
    st.error(f"Could not load geographic data: {error}")
    st.stop()

if detections.empty:
    st.warning("No valid detection records are available.")
    st.stop()


# Sidebar controls
st.sidebar.header("Map filters")

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

start_date, end_date = date_range

if start_date > end_date:
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
    help=(
        "The heatmap emphasizes spatial concentration. The hexagonal grid "
        "aggregates detection records into spatial cells."
    ),
)

show_boundary = st.sidebar.checkbox(
    "Show Victoria boundary",
    value=True,
)

show_all_points = st.sidebar.checkbox(
    "Show every detection in point mode",
    value=True,
    help=(
        "Only applies to individual-detection mode. Disable it to sample "
        "points when rendering a large number of records."
    ),
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

filtered = detections[
    detections["date"].between(start_date, end_date)
    & detections["source_product"].isin(selected_products)
].copy()

if filtered.empty:
    st.warning("No detections match the selected filters.")
    st.stop()


# Summary metrics always describe the full filtered dataset.
col1, col2, col3 = st.columns(3)
col1.metric("Detection records", f"{len(filtered):,}")
col2.metric("Satellite products", filtered["source_product"].nunique())
col3.metric("Dates represented", f"{filtered['date'].nunique():,}")

st.caption(
    "Counts refer to satellite detection records, not unique fires "
    "or burned area."
)


# Point rendering can be sampled, but density and grid modes use all
# filtered records so their spatial aggregation is not sample-dependent.
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
        f"Showing {len(map_data):,} sampled points out of "
        f"{len(filtered):,} matching records. Summary metrics use all records."
    )
else:
    map_data = filtered.copy()
    st.caption(f"Map input: {len(map_data):,} matching detection records.")


# Tooltips for the individual point layer.
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


# Map layers
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

elif map_mode == "Aggregated hexagonal grid":
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
        "records. The result depends on the selected radius and zoom level."
    )
else:
    st.caption(
        "Hexagonal cells aggregate the number of input detection records "
        "within each spatial cell. Cell counts are not counts of unique fires."
    )

st.pydeck_chart(deck, use_container_width=True)


# Product summary uses all filtered records.
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
    "They do not by themselves establish a unique fire, fire perimeter, "
    "cause, or burned area."
)
