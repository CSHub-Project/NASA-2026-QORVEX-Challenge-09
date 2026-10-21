
"""Interactive QORVEX dashboard for historical fire activity."""

import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


DATA_DIR = Path(os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data"))
ACTIVITY_DIR = DATA_DIR / "activity_calendar"

DAILY_FILE = ACTIVITY_DIR / "victoria_daily_activity_2024.csv"
ANOMALY_FILE = ACTIVITY_DIR / "victoria_anomaly_report_2024.csv"
EPISODE_FILE = ACTIVITY_DIR / "victoria_anomaly_episodes_2024.csv"

PRODUCT_COLUMNS = {
    "MODIS": "detections_MODIS_SP",
    "VIIRS NOAA-20": "detections_VIIRS_NOAA20_SP",
    "VIIRS Suomi-NPP": "detections_VIIRS_SNPP_SP",
}

ANOMALY_COLUMNS = {
    "MODIS": "is_anomaly_detections_MODIS_SP",
    "VIIRS NOAA-20": "is_anomaly_detections_VIIRS_NOAA20_SP",
    "VIIRS Suomi-NPP": "is_anomaly_detections_VIIRS_SNPP_SP",
}


st.set_page_config(
    page_title="QORVEX | Fire Activity Explorer",
    page_icon="🔥",
    layout="wide",
)


@st.cache_data
def load_csv(path_string: str) -> pd.DataFrame:
    """Load a CSV file and cache it until the app data changes."""
    return pd.read_csv(path_string)


def parse_dates(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return a copy with a normalized UTC date column."""
    result = frame.copy()
    result[column] = pd.to_datetime(
        result[column], errors="coerce", utc=True
    ).dt.floor("D")

    if result[column].isna().any():
        raise ValueError(f"Invalid dates found in column {column!r}.")

    return result


def parse_boolean(values: pd.Series) -> pd.Series:
    """Interpret boolean values read from CSV."""
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)

    normalized = values.astype("string").str.strip().str.lower()
    return normalized.isin({"true", "1", "yes"})


def show_missing_files(missing: list[Path]) -> None:
    st.error("One or more required data files are missing.")
    for path in missing:
        st.code(str(path))
    st.info(
        "Run the existing calendar, anomaly-detection, and episode "
        "scripts before starting the dashboard."
    )


@st.cache_data
def load_dashboard_data(
    daily_path: str,
    anomaly_path: str,
    episode_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and validate the dashboard's three data sources."""
    daily = parse_dates(load_csv(daily_path), "date")
    anomalies = parse_dates(load_csv(anomaly_path), "date")
    episodes = load_csv(episode_path)

    if daily["date"].duplicated().any():
        raise ValueError("The daily calendar contains duplicate dates.")

    if anomalies["date"].duplicated().any():
        raise ValueError("The anomaly report contains duplicate dates.")

    required_daily = {"date", "total_detections", *PRODUCT_COLUMNS.values()}
    missing_daily = required_daily - set(daily.columns)
    if missing_daily:
        raise ValueError(
            f"Daily calendar missing columns: {sorted(missing_daily)}"
        )

    required_anomaly = {
        "date",
        "is_anomaly_total_detections",
        *ANOMALY_COLUMNS.values(),
    }
    missing_anomaly = required_anomaly - set(anomalies.columns)
    if missing_anomaly:
        raise ValueError(
            f"Anomaly report missing columns: {sorted(missing_anomaly)}"
        )

    required_episodes = {
        "episode_id",
        "start_date",
        "end_date",
        "duration_days",
        "total_detections",
        "peak_daily_detections",
        "peak_date",
        "multi_product_support_pct",
    }
    missing_episodes = required_episodes - set(episodes.columns)
    if missing_episodes:
        raise ValueError(
            f"Episode report missing columns: {sorted(missing_episodes)}"
        )

    daily = daily.sort_values("date").reset_index(drop=True)
    anomalies = anomalies.sort_values("date").reset_index(drop=True)

    daily = daily.merge(
        anomalies[
            ["date", "is_anomaly_total_detections", *ANOMALY_COLUMNS.values()]
        ],
        on="date",
        how="left",
        validate="one_to_one",
    )

    for column in [
        "is_anomaly_total_detections",
        *ANOMALY_COLUMNS.values(),
    ]:
        daily[column] = parse_boolean(daily[column])

    for column in ["total_detections", *PRODUCT_COLUMNS.values()]:
        daily[column] = pd.to_numeric(daily[column], errors="coerce")
        if daily[column].isna().any() or (daily[column] < 0).any():
            raise ValueError(
                f"Invalid or negative counts in column {column!r}."
            )

    if daily["is_anomaly_total_detections"].isna().any():
        raise ValueError("Some calendar days have no anomaly report match.")

    episodes["start_date"] = pd.to_datetime(
        episodes["start_date"], errors="coerce"
    )
    episodes["end_date"] = pd.to_datetime(
        episodes["end_date"], errors="coerce"
    )
    episodes["peak_date"] = pd.to_datetime(
        episodes["peak_date"], errors="coerce"
    )

    if episodes[["start_date", "end_date", "peak_date"]].isna().any().any():
        raise ValueError("The episode report contains invalid dates.")

    return daily, anomalies, episodes


st.title("🔥 QORVEX — Fire Activity Explorer")
st.caption(
    "Interactive historical analysis of harmonized MODIS and VIIRS "
    "active-fire detections."
)

missing_files = [
    path
    for path in [DAILY_FILE, ANOMALY_FILE, EPISODE_FILE]
    if not path.is_file()
]

if missing_files:
    show_missing_files(missing_files)
    st.stop()

try:
    daily, anomalies, episodes = load_dashboard_data(
        str(DAILY_FILE),
        str(ANOMALY_FILE),
        str(EPISODE_FILE),
    )
except (ValueError, KeyError) as error:
    st.error(f"Could not load dashboard data: {error}")
    st.stop()

if daily.empty:
    st.warning("The daily activity calendar is empty.")
    st.stop()

# Sidebar filters
st.sidebar.header("Explore the data")

minimum_date = daily["date"].min().date()
maximum_date = daily["date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range

if start_date > end_date:
    st.error("The start date must be on or before the end date.")
    st.stop()

selected_products = st.sidebar.multiselect(
    "Satellite products",
    options=list(PRODUCT_COLUMNS.keys()),
    default=list(PRODUCT_COLUMNS.keys()),
)

show_anomalies = st.sidebar.checkbox(
    "Highlight overall anomaly days",
    value=True,
)

filtered = daily[
    daily["date"].dt.date.between(start_date, end_date)
].copy()

if filtered.empty:
    st.warning("No daily records are available for this date range.")
    st.stop()

# Summary metrics
total_detections = int(filtered["total_detections"].sum())
peak_index = filtered["total_detections"].idxmax()
peak_row = filtered.loc[peak_index]
anomaly_days = int(filtered["is_anomaly_total_detections"].sum())

period_episodes = episodes[
    (episodes["start_date"].dt.date <= end_date)
    & (episodes["end_date"].dt.date >= start_date)
]

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric("Detection records", f"{total_detections:,}")
metric2.metric("Peak daily detections", f"{int(peak_row['total_detections']):,}")
metric3.metric("Overall anomaly days", f"{anomaly_days:,}")
metric4.metric("Episodes intersecting period", f"{len(period_episodes):,}")

st.caption(
    f"Peak date: {peak_row['date'].strftime('%d %B %Y')}. "
    "Detection records are not unique fires or burned area."
)

# Interactive daily timeline
st.subheader("Daily fire-detection activity")

figure = go.Figure()

for product in selected_products:
    count_column = PRODUCT_COLUMNS[product]

    figure.add_trace(
        go.Scatter(
            x=filtered["date"],
            y=filtered[count_column],
            mode="lines",
            name=product,
            line={"width": 1.8},
            hovertemplate=(
                "%{x|%d %b %Y}<br>"
                + product
                + ": %{y:,}<extra></extra>"
            ),
        )
    )

if show_anomalies:
    overall_flags = filtered["is_anomaly_total_detections"]

    figure.add_trace(
        go.Scatter(
            x=filtered.loc[overall_flags, "date"],
            y=filtered.loc[overall_flags, "total_detections"],
            mode="markers",
            name="Overall anomaly",
            marker={
                "symbol": "diamond",
                "size": 9,
                "color": "#D97706",
                "line": {"width": 1, "color": "#FFFFFF"},
            },
            customdata=filtered.loc[
                overall_flags, ["total_detections"]
            ].to_numpy(),
            hovertemplate=(
                "%{x|%d %b %Y}<br>"
                "Overall detections: %{customdata[0]:,}"
                "<br>Anomalous overall<extra></extra>"
            ),
        )
    )

for _, episode in period_episodes.iterrows():
    figure.add_vrect(
        x0=max(pd.Timestamp(start_date), episode["start_date"]),
        x1=min(
            pd.Timestamp(end_date) + pd.Timedelta(days=1),
            episode["end_date"] + pd.Timedelta(days=1),
        ),
        fillcolor="#D97706",
        opacity=0.09,
        line_width=0,
        layer="below",
    )

figure.update_layout(
    height=520,
    hovermode="x unified",
    xaxis_title="Date",
    yaxis_title="Detection records per day",
    legend_title="Series",
    margin={"l": 20, "r": 20, "t": 30, "b": 20},
)
figure.update_xaxes(rangeslider_visible=True)

st.plotly_chart(figure, use_container_width=True)

if not selected_products:
    st.info("Select at least one satellite product to display its daily series.")

# Overall daily activity
with st.expander("Inspect daily activity records"):
    display_columns = [
        "date",
        "total_detections",
        *PRODUCT_COLUMNS.values(),
        "is_anomaly_total_detections",
    ]
    st.dataframe(
        filtered[display_columns].sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

# Episode explorer
st.subheader("Episode explorer")

if period_episodes.empty:
    st.info("No anomaly episodes overlap the selected date range.")
else:
    def episode_label(row: pd.Series) -> str:
        return (
            f"{row['episode_id']} · "
            f"{row['start_date']:%d %b}–{row['end_date']:%d %b %Y} · "
            f"{int(row['duration_days'])} days"
        )

    episode_records = period_episodes.to_dict(orient="records")
    episode_labels = {
        episode_label(pd.Series(record)): record
        for record in episode_records
    }

    selected_label = st.selectbox(
        "Select an episode",
        options=list(episode_labels.keys()),
    )
    selected_episode = episode_labels[selected_label]

    st.markdown(f"### {selected_episode['episode_id']}")

    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Duration", f"{int(selected_episode['duration_days'])} days")
    e2.metric(
        "Detection records",
        f"{int(selected_episode['total_detections']):,}",
    )
    e3.metric(
        "Peak daily detections",
        f"{int(selected_episode['peak_daily_detections']):,}",
    )
    e4.metric(
        "Multi-product support",
        f"{float(selected_episode['multi_product_support_pct']):.1f}%",
    )

    st.write(
        f"**Period:** {selected_episode['start_date']:%d %B %Y} – "
        f"{selected_episode['end_date']:%d %B %Y}"
    )
    st.write(
        f"**Peak date:** {selected_episode['peak_date']:%d %B %Y}"
    )

    evidence_columns = [
        "modis_anomaly_days",
        "viirs_noaa20_anomaly_days",
        "viirs_snpp_anomaly_days",
        "multi_product_anomaly_days",
    ]

    if all(column in selected_episode for column in evidence_columns):
        evidence_labels = {
            "modis_anomaly_days": "MODIS anomaly days",
            "viirs_noaa20_anomaly_days": "VIIRS NOAA-20 anomaly days",
            "viirs_snpp_anomaly_days": "VIIRS Suomi-NPP anomaly days",
            "multi_product_anomaly_days": "Days with multiple products flagged",
        }

        evidence_frame = pd.DataFrame(
            {
                "Evidence measure": [
                    evidence_labels[column]
                    for column in evidence_columns
                ],
                "Days": [
                    int(selected_episode[column])
                    for column in evidence_columns
                ],
            }
        )

        st.dataframe(evidence_frame, hide_index=True, use_container_width=True)

    st.caption(
        "Cross-product anomaly agreement is supporting evidence. "
        "An episode is not a confirmed individual wildfire."
    )

# Monthly activity context
st.subheader("Monthly activity")

monthly = (
    filtered.assign(month=filtered["date"].dt.strftime("%Y-%m"))
    .groupby("month", as_index=False)["total_detections"]
    .sum()
)

monthly_figure = go.Figure(
    go.Bar(
        x=monthly["month"],
        y=monthly["total_detections"],
        hovertemplate="%{x}<br>Detection records: %{y:,}<extra></extra>",
    )
)
monthly_figure.update_layout(
    height=330,
    xaxis_title="Month",
    yaxis_title="Detection records",
    margin={"l": 20, "r": 20, "t": 20, "b": 20},
)
st.plotly_chart(monthly_figure, use_container_width=True)

st.caption(
    "Prototype: Victoria, 2024. Anomalies are relative to the current "
    "statistical baseline and should not be interpreted as verified fire "
    "severity or burned area."
)
