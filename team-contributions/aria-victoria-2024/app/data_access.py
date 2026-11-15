
from pathlib import Path
import os

import pandas as pd
import streamlit as st


# app/data_access.py -> repository root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

PARQUET_DIR = Path(
    os.getenv(
        "QORVEX_PARQUET_DIR",
        str(PROJECT_ROOT / "data" / "processed" / "victoria_2024_filtered"),
    )
)

DETECTIONS_FILE = PARQUET_DIR / "spatially_indexed_detections.parquet"
DAILY_ACTIVITY_FILE = PARQUET_DIR / "daily_activity.parquet"

EXPECTED_DETECTION_COLUMNS = {
    "timestamp_utc",
    "latitude",
    "longitude",
    "sensor",
    "source_product",
    "frp_mw",
    "confidence_raw",
    "h3_res7",
}

EXPECTED_DAILY_COLUMNS = {
    "date_utc",
    "h3_res7",
    "modis_detection_count",
    "noaa20_detection_count",
    "snpp_detection_count",
    "combined_detection_count",
    "active_product_count",
}


class DatasetValidationError(RuntimeError):
    """Raised when an analytical dataset is missing required fields."""


@st.cache_data(show_spinner="Loading QORVEX datasets...")
def load_detections() -> pd.DataFrame:
    if not DETECTIONS_FILE.is_file():
        raise FileNotFoundError(
            f"Detection dataset not found: {DETECTIONS_FILE}"
        )

    df = pd.read_parquet(DETECTIONS_FILE)

    missing = EXPECTED_DETECTION_COLUMNS.difference(df.columns)
    if missing:
        raise DatasetValidationError(
            f"Detection dataset is missing columns: {sorted(missing)}"
        )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"], utc=True, errors="raise"
    )

    return df


@st.cache_data(show_spinner="Loading daily spatial activity...")
def load_daily_activity() -> pd.DataFrame:
    if not DAILY_ACTIVITY_FILE.is_file():
        raise FileNotFoundError(
            f"Daily activity dataset not found: {DAILY_ACTIVITY_FILE}"
        )

    df = pd.read_parquet(DAILY_ACTIVITY_FILE)

    missing = EXPECTED_DAILY_COLUMNS.difference(df.columns)
    if missing:
        raise DatasetValidationError(
            f"Daily activity dataset is missing columns: {sorted(missing)}"
        )

    df["date_utc"] = pd.to_datetime(
        df["date_utc"], errors="raise"
    )

    return df


@st.cache_data(show_spinner="Preparing daily detection statistics...")
def load_daily_detection_summary() -> pd.DataFrame:
    detections = load_detections()

    daily = (
        detections.assign(
            date_utc=detections["timestamp_utc"].dt.strftime("%Y-%m-%d")
        )
        .groupby("date_utc", as_index=False)
        .agg(
            detection_count=("source_product", "size"),
            active_products=("source_product", "nunique"),
        )
    )

    daily["date_utc"] = pd.to_datetime(daily["date_utc"])

    return daily.sort_values("date_utc")


def get_dataset_metadata() -> dict:
    detections = load_detections()
    daily = load_daily_activity()

    return {
        "dataset_name": "Victoria 2024 — Filtered FIRMS Detections",
        "geographic_scope": "Victoria, Australia",
        "period_start": detections["timestamp_utc"].min(),
        "period_end": detections["timestamp_utc"].max(),
        "detection_records": len(detections),
        "daily_spatial_records": len(daily),
        "active_dates": detections["timestamp_utc"].dt.date.nunique(),
        "active_h3_res7_cells": detections["h3_res7"].nunique(),
        "products": sorted(detections["source_product"].dropna().unique()),
    }
