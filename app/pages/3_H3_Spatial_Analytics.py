from __future__ import annotations

import json
from datetime import date

import h3
import pandas as pd
import pydeck as pdk
import streamlit as st

from data_access import load_daily_activity


st.set_page_config(
    page_title="QORVEX | H3 Spatial Analytics",
    page_icon="🌐",
    layout="wide",
)

st.title("H3 Spatial Analytics")
st.caption(
    "Daily satellite hotspot-detection activity aggregated to genuine "
    "H3 resolution-7 cells — Victoria, Australia, 2024."
)

PRODUCT_COLUMNS = {
    "MODIS": "modis_detection_count",
    "VIIRS NOAA-20": "noaa20_detection_count",
    "VIIRS Suomi-NPP": "snpp_detection_count",
}


def color_for_value(value: float, maximum: float) -> list[int]:
    """Return a simple pale-yellow to dark-red ramp."""
    if maximum <= 0:
        return [245, 245, 245, 150]

    ratio = max(0.0, min(float(value) / float(maximum), 1.0))
    stops = [
        (255, 245, 204),
        (254, 196, 79),
        (239, 101, 72),
        (165, 0, 38),
    ]
    scaled = ratio * (len(stops) - 1)
    lower = int(scaled)
    upper = min(lower + 1, len(stops) - 1)
    fraction = scaled - lower
    rgb = [
        round(stops[lower][i] * (1 - fraction) + stops[upper][i] * fraction)
        for i in range(3)
    ]
    return [*rgb, 190]


@st.cache_data(show_spinner="Preparing H3 cell boundaries...")
def build_geojson(frame: pd.DataFrame, value_column: str) -> str:
    """Build GeoJSON polygons for the H3 cells present in the filtered data."""
    if frame.empty:
        return json.dumps({"type": "FeatureCollection", "features": []})

    maximum = float(frame[value_column].max())
    features = []

    for row in frame[["h3_res7", value_column]].itertuples(index=False):
        cell = row.h3_res7
        value = int(row[1])

        # h3.cell_to_boundary returns (latitude, longitude) pairs.
        boundary = h3.cell_to_boundary(cell)
        ring = [[longitude, latitude] for latitude, longitude in boundary]
        ring.append(ring[0])

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "h3_index": cell,
                    "detection_count": value,
                    "fill_color": color_for_value(value, maximum),
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring],
                },
            }
        )

    return json.dumps({"type": "FeatureCollection", "features": features})


@st.cache_data(show_spinner="Loading H3 spatial activity...")
def get_activity() -> pd.DataFrame:
    frame = load_daily_activity().copy()
    frame["date_utc"] = pd.to_datetime(frame["date_utc"], errors="raise").dt.date
    return frame


try:
    activity = get_activity()
except Exception as exc:
    st.error(f"Unable to load the daily H3 activity dataset: {exc}")
    st.stop()

required_products = list(PRODUCT_COLUMNS.values())
missing_products = [column for column in required_products if column not in activity]
if missing_products:
    st.error(f"The daily activity dataset is missing columns: {missing_products}")
    st.stop()

if activity.empty:
    st.warning("The daily activity dataset contains no records.")
    st.stop()

st.sidebar.header("Spatial analysis controls")

available_dates = sorted(activity["date_utc"].dropna().unique())
selected_date = st.sidebar.selectbox(
    "Observation date (UTC)",
    options=available_dates,
    index=0,
    format_func=lambda value: value.strftime("%d %B %Y"),
)

selected_products = st.sidebar.multiselect(
    "Satellite products",
    options=list(PRODUCT_COLUMNS),
    default=list(PRODUCT_COLUMNS),
)

if not selected_products:
    st.info("Select at least one satellite product to display its detections.")
    st.stop()

selected_columns = [PRODUCT_COLUMNS[name] for name in selected_products]

daily = activity.loc[activity["date_utc"] == selected_date].copy()
daily["selected_detection_count"] = daily[selected_columns].sum(axis=1)

# Rows in daily_activity represent cell-days with at least one detection.
# Filtering to selected products may leave cells with zero selected-product detections.
daily = daily.loc[daily["selected_detection_count"] > 0].copy()
daily = daily.sort_values("selected_detection_count", ascending=False)

total_detections = int(daily["selected_detection_count"].sum())
active_cells = int(daily["h3_res7"].nunique())
max_cell_count = int(daily["selected_detection_count"].max()) if not daily.empty else 0

metric_columns = st.columns(3)
metric_columns[0].metric("Recorded detections", f"{total_detections:,}")
metric_columns[1].metric("Active H3 cells", f"{active_cells:,}")
metric_columns[2].metric("Highest cell count", f"{max_cell_count:,}")

st.caption(
    f"Selected date: {selected_date:%Y-%m-%d} UTC · "
    f"Products: {', '.join(selected_products)} · "
    "A cell is shown only when at least one selected product has a recorded detection."
)

if daily.empty:
    st.warning(
        "No records for the selected products on this date. "
        "This means no matching records in this dataset, not proof of zero fire activity."
    )
    st.stop()

geojson_data = build_geojson(daily, "selected_detection_count")

view_state = pdk.ViewState(
    latitude=-36.8,
    longitude=144.3,
    zoom=5.8,
    pitch=0,
    bearing=0,
)

layer = pdk.Layer(
    "GeoJsonLayer",
    data=json.loads(geojson_data),
    pickable=True,
    stroked=True,
    filled=True,
    extruded=False,
    get_fill_color="properties.fill_color",
    get_line_color=[80, 55, 45, 120],
    line_width_min_pixels=0.5,
)

tooltip = {
    "html": (
        "<b>H3 cell:</b> {h3_index}<br/>"
        "<b>Recorded detections:</b> {detection_count}"
    ),
    "style": {"backgroundColor": "#20242b", "color": "white"},
}

st.subheader("Daily H3 detection activity")
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style=None,
    ),
    use_container_width=True,
)

st.subheader("Highest-activity H3 cells")
display_columns = [
    "h3_res7",
    "selected_detection_count",
    "active_product_count",
    "modis_detection_count",
    "noaa20_detection_count",
    "snpp_detection_count",
]
available_display_columns = [column for column in display_columns if column in daily.columns]
top_cells = daily[available_display_columns].head(20).rename(
    columns={
        "h3_res7": "H3 resolution-7 cell",
        "selected_detection_count": "Selected-product detections",
        "active_product_count": "Products active in source record",
        "modis_detection_count": "MODIS detections",
        "noaa20_detection_count": "VIIRS NOAA-20 detections",
        "snpp_detection_count": "VIIRS Suomi-NPP detections",
    }
)
st.dataframe(top_cells, use_container_width=True, hide_index=True)

st.subheader("Inspect an H3 cell")
cell_options = daily["h3_res7"].tolist()
selected_cell = st.selectbox("H3 cell", options=cell_options)
cell_row = daily.loc[daily["h3_res7"] == selected_cell].iloc[0]

detail_columns = st.columns(3)
detail_columns[0].metric(
    "Selected-product detections",
    f"{int(cell_row['selected_detection_count']):,}",
)
detail_columns[1].metric(
    "Products active in source record",
    int(cell_row["active_product_count"]),
)
detail_columns[2].metric("H3 resolution", "7")

product_details = pd.DataFrame(
    {
        "Satellite product": [
            "MODIS",
            "VIIRS NOAA-20",
            "VIIRS Suomi-NPP",
        ],
        "Detection records": [
            int(cell_row["modis_detection_count"]),
            int(cell_row["noaa20_detection_count"]),
            int(cell_row["snpp_detection_count"]),
        ],
    }
)
st.dataframe(product_details, use_container_width=True, hide_index=True)

st.caption(
    "Interpretation: counts represent FIRMS hotspot detection records, not unique fires, "
    "burned area, or independently validated fire events. Missing records do not establish "
    "zero fire activity or valid satellite observation coverage. H3 cell-day co-occurrence "
    "does not prove that different products detected the same physical fire."
)
