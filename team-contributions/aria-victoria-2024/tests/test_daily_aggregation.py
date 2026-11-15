
from datetime import date

import h3
import pandas as pd
import pytest

from qorvex.daily_aggregation import (
    OUTPUT_COLUMNS,
    aggregate_daily_activity,
)


TEST_CELL = h3.latlng_to_cell(-37.6459, 145.0045, 7)


@pytest.fixture
def sample_detections():
    return pd.DataFrame([
        {
            "timestamp_utc": "2024-01-03T04:30:00Z",
            "h3_res7": TEST_CELL,
            "source_product": "MODIS_SP",
            "frp_mw": 7.5,
        },
        {
            "timestamp_utc": "2024-01-03T05:00:00Z",
            "h3_res7": TEST_CELL,
            "source_product": "MODIS_SP",
            "frp_mw": 12.5,
        },
        {
            "timestamp_utc": "2024-01-03T04:14:00Z",
            "h3_res7": TEST_CELL,
            "source_product": "VIIRS_NOAA20_SP",
            "frp_mw": 3.52,
        },
        {
            "timestamp_utc": "2024-01-03T14:43:00Z",
            "h3_res7": TEST_CELL,
            "source_product": "VIIRS_SNPP_SP",
            "frp_mw": 2.6,
        },
    ])


def test_output_schema_contains_18_columns(sample_detections):
    result = aggregate_daily_activity(sample_detections)

    assert list(result.columns) == OUTPUT_COLUMNS
    assert len(OUTPUT_COLUMNS) == 18


def test_all_products_are_aggregated(sample_detections):
    result = aggregate_daily_activity(sample_detections)

    assert len(result) == 1

    row = result.iloc[0]

    assert row["modis_detection_count"] == 2
    assert row["noaa20_detection_count"] == 1
    assert row["snpp_detection_count"] == 1
    assert row["combined_detection_count"] == 4
    assert row["active_product_count"] == 3


def test_frp_statistics_are_product_specific(sample_detections):
    result = aggregate_daily_activity(sample_detections)
    row = result.iloc[0]

    assert row["modis_frp_mean_mw"] == 10.0
    assert row["modis_frp_max_mw"] == 12.5
    assert row["modis_frp_sum_mw"] == 20.0

    assert row["noaa20_frp_mean_mw"] == 3.52
    assert row["noaa20_frp_max_mw"] == 3.52
    assert row["noaa20_frp_sum_mw"] == 3.52

    assert row["snpp_frp_mean_mw"] == 2.6
    assert row["snpp_frp_max_mw"] == 2.6
    assert row["snpp_frp_sum_mw"] == 2.6


def test_missing_product_has_zero_count_and_null_frp(sample_detections):
    detections = sample_detections[
        sample_detections["source_product"] != "VIIRS_SNPP_SP"
    ]

    result = aggregate_daily_activity(detections)
    row = result.iloc[0]

    assert row["snpp_detection_count"] == 0
    assert pd.isna(row["snpp_frp_mean_mw"])
    assert pd.isna(row["snpp_frp_max_mw"])
    assert pd.isna(row["snpp_frp_sum_mw"])
    assert row["active_product_count"] == 2


def test_all_missing_frp_values_remain_null():
    detections = pd.DataFrame([
        {
            "timestamp_utc": "2024-01-03T04:30:00Z",
            "h3_res7": TEST_CELL,
            "source_product": "MODIS_SP",
            "frp_mw": None,
        },
    ])

    result = aggregate_daily_activity(detections)
    row = result.iloc[0]

    assert row["modis_detection_count"] == 1
    assert pd.isna(row["modis_frp_mean_mw"])
    assert pd.isna(row["modis_frp_max_mw"])
    assert pd.isna(row["modis_frp_sum_mw"])


def test_utc_date_boundary_creates_separate_daily_records():
    detections = pd.DataFrame([
        {
            "timestamp_utc": "2024-01-03T23:59:00Z",
            "h3_res7": TEST_CELL,
            "source_product": "MODIS_SP",
            "frp_mw": 5.0,
        },
        {
            "timestamp_utc": "2024-01-04T00:01:00Z",
            "h3_res7": TEST_CELL,
            "source_product": "MODIS_SP",
            "frp_mw": 10.0,
        },
    ])

    result = aggregate_daily_activity(detections)

    assert len(result) == 2
    assert set(result["date_utc"]) == {
        date(2024, 1, 3),
        date(2024, 1, 4),
    }


def test_first_and_last_detection_timestamps(sample_detections):
    result = aggregate_daily_activity(sample_detections)
    row = result.iloc[0]

    assert row["first_detection_utc"] == pd.Timestamp(
        "2024-01-03T04:14:00Z"
    )

    assert row["last_detection_utc"] == pd.Timestamp(
        "2024-01-03T14:43:00Z"
    )


def test_different_h3_cells_create_separate_records(sample_detections):
    other_cell = h3.latlng_to_cell(-37.0, 145.0, 7)

    detections = sample_detections.iloc[[0]].copy()
    other_detection = detections.copy()
    other_detection["h3_res7"] = other_cell

    combined = pd.concat(
        [detections, other_detection],
        ignore_index=True,
    )

    result = aggregate_daily_activity(combined)

    assert len(result) == 2
    assert set(result["h3_res7"]) == {TEST_CELL, other_cell}


def test_unknown_product_is_rejected(sample_detections):
    detections = sample_detections.copy()
    detections.loc[0, "source_product"] = "UNKNOWN_PRODUCT"

    with pytest.raises(ValueError, match="Unsupported source products"):
        aggregate_daily_activity(detections)


def test_invalid_h3_cell_is_rejected(sample_detections):
    detections = sample_detections.copy()
    detections.loc[0, "h3_res7"] = "invalid-cell"

    with pytest.raises(ValueError, match="resolution 7"):
        aggregate_daily_activity(detections)


def test_missing_required_column_is_rejected():
    detections = pd.DataFrame({
        "timestamp_utc": ["2024-01-03T04:30:00Z"],
        "h3_res7": [TEST_CELL],
        "source_product": ["MODIS_SP"],
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        aggregate_daily_activity(detections)


def test_empty_input_returns_empty_dataframe():
    detections = pd.DataFrame(columns=[
        "timestamp_utc",
        "h3_res7",
        "source_product",
        "frp_mw",
    ])

    result = aggregate_daily_activity(detections)

    assert result.empty
    assert list(result.columns) == OUTPUT_COLUMNS
