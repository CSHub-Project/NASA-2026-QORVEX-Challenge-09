
"""Interactive geographic explorer for QORVEX fire detections."""

import os
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st


DATA_DIR = Path(os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data"))
FIRE_FILE = DATA_DIR / "victoria_fires_2024.csv"

PRODUCT_LABELS = {
    "MODIS_SP": "MODIS",
    "VIIRS_NOAA20_SP": "VIIRS NOAA-20",
    "VIIRS_SNPP_SP": "VIIRS Suomi-NPP",
}

PRODUCT_COLORS = {
    "MODIS_SP": [30, 120, 220, 180],
    "VIIRS_NOAA20_SP": [230, 90, 40, 180],
    "VIIRS_SNPP_SP": [30, 170, 110, 180],
}


st.set_page_config(
    page_title="QORVEX | Geographic Explorer",
    page_icon="🌏",
    layout="wide",
)


@st.cache_data
def load_detections(path: str) -> pd.DataFrame:
    """Load and validate the filtered detection dataset."""
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
        lambda color: color if isinstance(color, list)
        else [120, 120, 120, 180]
    )

    return frame.reset_index(drop=True)


st.title("🌏 QORVEX — Geographic Explorer")
st.caption(
    "Explore the locations of harmonized MODIS and VIIRS "
    "active-fire detections within Victoria during 2024."
)

if not FIRE_FILE.is_file():
    st.error(f"Detection dataset not found: {FIRE_FILE}")
    st.info(
        "Run scripts/filter_victoria_fires_2024.py first."
    )
    st.stop()

try:
    detections = load_detections(str(FIRE_FILE))
except (ValueError, OSError) as error:
    st.error(f"Could not load detection data: {error}")
    st.stop()

if detections.empty:
    st.warning("No valid detection records are available.")
    st.stop()


# Sidebar filters
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

show_all_points = st.sidebar.checkbox(
    "Show every detection",
    value=True,
    help=(
        "Disable this option to display a random sample when many "
        "detections are selected. The metrics still use all records."
    ),
)

maximum_map_points = st.sidebar.slider(
    "Maximum displayed points",
    min_value=1000,
    max_value=50000,
    value=20000,
    step=1000,
    disabled=show_all_points,
    help="Limits map rendering only, not the analysis or record counts.",
)

filtered = detections[
    detections["date"].between(start_date, end_date)
    & detections["source_product"].isin(selected_products)
].copy()

if filtered.empty:
    st.warning("No detections match the selected filters.")
    st.stop()


# Summary metrics
col1, col2, col3 = st.columns(3)
col1.metric("Detection records", f"{len(filtered):,}")
col2.metric("Satellite products", filtered["source_product"].nunique())
col3.metric(
    "Dates represented",
    f"{filtered['date'].nunique():,}",
)

st.caption(
    "Each point represents a satellite detection record, not necessarily "
    "a unique fire. Points may overlap geographically."
)


# Limit the rendering workload when requested.
if show_all_points or len(filtered) <= maximum_map_points:
    map_data = filtered.copy()
    sampling_note = f"Displaying all {len(map_data):,} matching records."
else:
    map_data = filtered.sample(
        n=maximum_map_points,
        random_state=42,
    ).copy()
    sampling_note = (
        f"Displaying a reproducible random sample of "
        f"{len(map_data):,} of {len(filtered):,} matching records. "
        "Summary metrics still use all matching records."
    )

st.caption(sampling_note)


# Construct rich tooltips without exposing unnecessary raw fields.
tooltip_fields = [
    field
    for field in [
        "timestamp_utc",
        "product_label",
        "sensor",
        "latitude",
        "longitude",
        "confidence_raw",
        "frp_mw",
        "brightness_raw",
        "brightness_11um_raw",
        "viirs_bright_ti4",
        "viirs_bright_ti5",
        "daynight_raw",
    ]
    if field in map_data.columns
]

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

layer = pdk.Layer(
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
    opacity=0.65,
)

view_state = pdk.ViewState(
    latitude=float(map_data["latitude"].median()),
    longitude=float(map_data["longitude"].median()),
    zoom=6,
    pitch=0,
    bearing=0,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
)

st.subheader("Detection locations")
st.pydeck_chart(deck, use_container_width=True)


# Product-level summaries
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
    "Scientific note: active-fire detections indicate satellite-observed "
    "thermal anomalies. They do not by themselves establish a unique fire, "
    "fire perimeter, cause, or burned area."
)
