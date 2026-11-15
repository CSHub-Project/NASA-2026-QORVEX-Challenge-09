
"""QORVEX activity dashboard for selectable harmonized FIRMS datasets."""
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_access import (
    get_dataset_metadata,
    load_detections as load_parquet_detections,
)

DATA_DIR = Path(os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data"))
ACTIVITY_DIR = DATA_DIR / "activity_calendar"
PARQUET_DATASET_LABEL = "Victoria 2024 — Corrected Parquet"

PRODUCT_LABELS = {
    "MODIS_SP": "MODIS",
    "VIIRS_NOAA20_SP": "VIIRS NOAA-20",
    "VIIRS_SNPP_SP": "VIIRS Suomi-NPP",
}
COLORS = {
    "MODIS": "#1E78DC",
    "VIIRS NOAA-20": "#E65A28",
    "VIIRS Suomi-NPP": "#1EAA6E",
}

st.set_page_config(
    page_title="QORVEX | Fire Activity Explorer",
    page_icon="🔥",
    layout="wide",
)


@st.cache_data
def discover_datasets(directory: str) -> list[str]:
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
def load_detections(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = {
        "latitude",
        "longitude",
        "timestamp_utc",
        "source_product",
    }
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    df["latitude"] = pd.to_numeric(
        df["latitude"], errors="coerce"
    )
    df["longitude"] = pd.to_numeric(
        df["longitude"], errors="coerce"
    )
    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        errors="coerce",
        utc=True,
    )

    valid = (
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
        & df["timestamp_utc"].notna()
    )
    df = df.loc[valid].copy()
    df["date"] = df["timestamp_utc"].dt.floor("D")

    return df.sort_values(
        "timestamp_utc"
    ).reset_index(drop=True)


@st.cache_data
def load_legacy_reports(directory: str):
    root = Path(directory)

    anomaly_path = root / "victoria_anomaly_report_2024.csv"
    episode_path = root / "victoria_anomaly_episodes_2024.csv"

    anomalies = (
        pd.read_csv(anomaly_path)
        if anomaly_path.is_file()
        else None
    )
    episodes = (
        pd.read_csv(episode_path)
        if episode_path.is_file()
        else None
    )

    if anomalies is not None and "date" in anomalies.columns:
        anomalies["date"] = pd.to_datetime(
            anomalies["date"],
            errors="coerce",
            utc=True,
        ).dt.floor("D")

    if episodes is not None:
        for column in ("start_date", "end_date", "peak_date"):
            if column in episodes.columns:
                episodes[column] = pd.to_datetime(
                    episodes[column],
                    errors="coerce",
                )

    return anomalies, episodes


def scope_frame(
    df: pd.DataFrame,
    scope: str,
    west: float,
    south: float,
    east: float,
    north: float,
) -> pd.DataFrame:
    if scope != "Bounding box":
        return df.copy()

    return df.loc[
        df["longitude"].between(west, east)
        & df["latitude"].between(south, north)
    ].copy()


st.title("🔥 QORVEX — Fire Activity Explorer")
st.caption(
    "Interactive analysis of harmonized MODIS and VIIRS "
    "active-fire detection records."
)

st.sidebar.header("Data and filters")

data_source = st.sidebar.radio(
    "Data source",
    [
        PARQUET_DATASET_LABEL,
        "Legacy CSV datasets",
    ],
)

selected_path = None
metadata = None

try:
    if data_source == PARQUET_DATASET_LABEL:
        detections = load_parquet_detections()
        metadata = get_dataset_metadata()

        scope_options = [
            "Victoria (dataset extent)",
            "Bounding box",
        ]

        st.sidebar.success("Corrected Parquet dataset loaded")
        st.sidebar.caption(
            "Victoria, Australia · 2024 · "
            f"{metadata['detection_records']:,} detection records"
        )

    else:
        datasets = discover_datasets(str(DATA_DIR))

        if not datasets:
            st.error(
                f"No harmonized CSV files found in {DATA_DIR}. "
                "Set QORVEX_DATA_DIR or place harmonized_fires*.csv there."
            )
            st.stop()

        default = next(
            (
                path for path in datasets
                if Path(path).name == "victoria_fires_2024.csv"
            ),
            datasets[0],
        )

        selected_path = st.sidebar.selectbox(
            "Harmonized dataset",
            datasets,
            index=datasets.index(default),
            format_func=lambda path: Path(path).name,
        )

        detections = load_detections(selected_path)
        scope_options = ["World", "Bounding box"]

except (OSError, ValueError, KeyError, RuntimeError) as error:
    st.error(f"Could not load the selected dataset: {error}")
    st.stop()

# Both data sources need the same UTC date field for dashboard filters.
detections["latitude"] = pd.to_numeric(
    detections["latitude"], errors="coerce"
)
detections["longitude"] = pd.to_numeric(
    detections["longitude"], errors="coerce"
)
detections["timestamp_utc"] = pd.to_datetime(
    detections["timestamp_utc"], errors="coerce", utc=True
)

valid = (
    detections["latitude"].between(-90, 90)
    & detections["longitude"].between(-180, 180)
    & detections["timestamp_utc"].notna()
)
detections = detections.loc[valid].copy()
detections["date"] = detections["timestamp_utc"].dt.floor("D")

if detections.empty:
    st.warning("The selected dataset contains no valid detections.")
    st.stop()

scope = st.sidebar.radio(
    "Geographic scope",
    scope_options,
    horizontal=True,
)

if scope == "Bounding box":
    with st.sidebar.expander(
        "Bounding-box coordinates",
        expanded=True,
    ):
        st.caption("West, south, east, north; decimal degrees.")

        west = st.number_input(
            "West longitude",
            min_value=-180.0,
            max_value=180.0,
            value=140.9,
            step=0.1,
        )
        south = st.number_input(
            "South latitude",
            min_value=-90.0,
            max_value=90.0,
            value=-39.2,
            step=0.1,
        )
        east = st.number_input(
            "East longitude",
            min_value=-180.0,
            max_value=180.0,
            value=150.1,
            step=0.1,
        )
        north = st.number_input(
            "North latitude",
            min_value=-90.0,
            max_value=90.0,
            value=-33.9,
            step=0.1,
        )

    if west >= east or south >= north:
        st.sidebar.error("Require west < east and south < north.")
        st.stop()
else:
    west, south, east, north = (
        -180.0, -90.0, 180.0, 90.0
    )
    if data_source == "Legacy CSV datasets":
        st.sidebar.caption(
            "World shows all records in the selected file; "
            "it does not fetch additional global data."
        )

if detections.empty:
    st.warning(
        "The selected dataset contains no valid detections."
    )
    st.stop()

filtered = scope_frame(
    detections, scope, west, south, east, north
)

if filtered.empty:
    st.warning(
        "No detections match the geographic scope."
    )
    st.stop()

minimum = filtered["date"].min().date()
maximum = filtered["date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(minimum, maximum),
    min_value=minimum,
    max_value=maximum,
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range

if start_date > end_date:
    st.error("The start date must be on or before the end date.")
    st.stop()

products = sorted(
    filtered["source_product"].dropna().astype(str).unique()
)

selected_products = st.sidebar.multiselect(
    "Satellite products",
    products,
    default=products,
    format_func=lambda product: PRODUCT_LABELS.get(
        product, product
    ),
)

filtered = filtered.loc[
    filtered["date"].dt.date.between(start_date, end_date)
    & filtered["source_product"].isin(selected_products)
].copy()

if filtered.empty:
    st.warning(
        "No detections match the selected dates, scope, and products."
    )
    st.stop()

daily = (
    filtered.assign(
        day=filtered["date"].dt.date,
        product=filtered["source_product"]
        .map(PRODUCT_LABELS)
        .fillna(filtered["source_product"]),
    )
    .groupby(["day", "product"], as_index=False)
    .size()
    .rename(columns={"day": "date", "size": "detections"})
)

totals = daily.groupby("date", as_index=False)["detections"].sum()
peak = totals.loc[totals["detections"].idxmax()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Detection records", f"{len(filtered):,}")
col2.metric(
    "Satellite products",
    f"{filtered['source_product'].nunique():,}",
)
col3.metric(
    "Dates represented",
    f"{filtered['date'].dt.date.nunique():,}",
)
col4.metric(
    "Peak daily detections",
    f"{int(peak['detections']):,}",
)

dataset_label = (
    PARQUET_DATASET_LABEL
    if selected_path is None
    else Path(selected_path).name
)

st.caption(
    f"{dataset_label} · {scope} · "
    f"{start_date:%d %b %Y}–{end_date:%d %b %Y}. "
    "Detection records are not unique fires or burned area."
)

st.subheader("Daily fire-detection activity")

fig = go.Figure()

for product in daily["product"].drop_duplicates():
    part = daily[daily["product"] == product]

    fig.add_trace(
        go.Scatter(
            x=part["date"],
            y=part["detections"],
            mode="lines",
            name=product,
            line={
                "width": 1.8,
                "color": COLORS.get(product),
            },
            hovertemplate=(
                "%{x|%d %b %Y}<br>"
                + product
                + ": %{y:,}<extra></extra>"
            ),
        )
    )

fig.update_layout(
    height=460,
    hovermode="x unified",
    xaxis_title="Date",
    yaxis_title="Detection records per day",
    margin={"l": 20, "r": 20, "t": 25, "b": 20},
)
fig.update_xaxes(rangeslider_visible=True)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly activity")

monthly = (
    filtered.assign(
        month=filtered["date"].dt.strftime("%Y-%m")
    )
    .groupby("month", as_index=False)
    .size()
    .rename(columns={"size": "detections"})
)

monthly_fig = go.Figure(
    go.Bar(
        x=monthly["month"],
        y=monthly["detections"],
        hovertemplate=(
            "%{x}<br>Records: %{y:,}<extra></extra>"
        ),
    )
)

monthly_fig.update_layout(
    height=330,
    xaxis_title="Month",
    yaxis_title="Detection records",
    margin={"l": 20, "r": 20, "t": 20, "b": 20},
)
st.plotly_chart(monthly_fig, use_container_width=True)

# Legacy anomaly reports are only associated with the original
# Victoria 2024 dataset. They are not recalculated for other data.
if (
    selected_path is not None
    and Path(selected_path).name == "victoria_fires_2024.csv"
):
    anomalies, episodes = load_legacy_reports(str(ACTIVITY_DIR))

    if anomalies is not None and {
        "date", "is_anomaly_total_detections"
    }.issubset(anomalies.columns):
        st.subheader("Victoria 2024 anomaly context")

        anomaly_slice = anomalies.loc[
            anomalies["date"].dt.date.between(
                start_date, end_date
            )
        ]
        flags = (
            anomaly_slice["is_anomaly_total_detections"]
            .astype(str)
            .str.lower()
            .isin({"true", "1", "yes"})
        )

        st.metric(
            "Precomputed overall anomaly days",
            f"{int(flags.sum()):,}",
        )
        st.caption(
            "These flags belong to the legacy Victoria 2024 "
            "analysis and are not recalculated for other datasets "
            "or geographic scopes."
        )

    if (
        episodes is not None
        and not episodes.empty
        and {"episode_id", "start_date", "end_date"}.issubset(
            episodes.columns
        )
    ):
        relevant_episodes = episodes.loc[
            (episodes["start_date"].dt.date <= end_date)
            & (episodes["end_date"].dt.date >= start_date)
        ]

        st.subheader("Anomaly episodes")

        if relevant_episodes.empty:
            st.info(
                "No precomputed episodes overlap the selected period."
            )
        else:
            # Each column appears only once; duplicate names cause
            # a PyArrow error when Streamlit renders the dataframe.
            display_columns = [
                "episode_id",
                "start_date",
                "end_date",
                "duration_days",
                "total_detections",
                "peak_daily_detections",
                "multi_product_support_pct",
            ]
            display_columns = [
                column for column in display_columns
                if column in relevant_episodes.columns
            ]

            st.dataframe(
                relevant_episodes[display_columns],
                use_container_width=True,
                hide_index=True,
            )

with st.expander("Inspect daily activity"):
    st.dataframe(
        totals.sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Inspect filtered detections"):
    display_columns = [
        column for column in [
            "timestamp_utc",
            "latitude",
            "longitude",
            "sensor",
            "source_product",
            "confidence_raw",
            "frp_mw",
            "brightness_raw",
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
    "The corrected Parquet dataset represents filtered FIRMS "
    "detection records for Victoria, Australia, during 2024. "
    "A detection record is not necessarily a unique fire. "
    "The absence of a record does not establish zero fire activity "
    "or valid satellite observation coverage. "
    "Anomaly episodes, where shown for the legacy dataset, are "
    "statistical activity periods, not confirmed individual wildfires."
)
