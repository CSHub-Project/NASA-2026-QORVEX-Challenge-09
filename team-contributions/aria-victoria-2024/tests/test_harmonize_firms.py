
from datetime import datetime, timezone

import pytest

from qorvex.harmonize_firms import harmonize_record


# Representative MODIS record from our earlier FIRMS query.
MODIS_RECORD = {
    "latitude": "-37.6459",
    "longitude": "145.0045",
    "acq_date": "2024-01-03",
    "acq_time": "430",
    "satellite": "Aqua",
    "instrument": "MODIS",
    "confidence": "37",
    "brightness": "320.4",
    "bright_t31": "296.8",
    "frp": "7.5",
    "daynight": "D",
    "type": "2",
    "version": "61.03",
}

# Representative VIIRS record from our earlier FIRMS query.
VIIRS_RECORD = {
    "latitude": "-33.98823",
    "longitude": "145.50688",
    "acq_date": "2024-01-01",
    "acq_time": "1443",
    "satellite": "N",
    "instrument": "VIIRS",
    "confidence": "n",
    "bright_ti4": "295.85",
    "bright_ti5": "263.28",
    "frp": "2.6",
    "daynight": "N",
    "type": "0",
    "version": "2",
}


def test_harmonize_modis_record():
    result = harmonize_record(MODIS_RECORD, "MODIS_SP")

    assert result["latitude"] == -37.6459
    assert result["longitude"] == 145.0045
    assert result["frp_mw"] == 7.5
    assert result["confidence_raw"] == "37"
    assert result["timestamp_utc"] == datetime(
        2024, 1, 3, 4, 30, tzinfo=timezone.utc
    )
    assert result["viirs_bright_ti4"] is None


def test_harmonize_viirs_record():
    result = harmonize_record(VIIRS_RECORD, "VIIRS_SNPP_SP")

    assert result["latitude"] == -33.98823
    assert result["longitude"] == 145.50688
    assert result["frp_mw"] == 2.6
    assert result["confidence_raw"] == "n"
    assert result["timestamp_utc"] == datetime(
        2024, 1, 1, 14, 43, tzinfo=timezone.utc
    )
    assert result["brightness_raw"] is None


@pytest.mark.parametrize(
    ("acq_time", "expected"),
    [
        (430.0, datetime(2024, 1, 3, 4, 30, tzinfo=timezone.utc)),
        (30.0, datetime(2024, 1, 3, 0, 30, tzinfo=timezone.utc)),
        ("0030", datetime(2024, 1, 3, 0, 30, tzinfo=timezone.utc)),
    ],
)
def test_numeric_and_zero_padded_acquisition_times(acq_time, expected):
    record = MODIS_RECORD.copy()
    record["acq_time"] = acq_time

    result = harmonize_record(record, "MODIS_SP")

    assert result["timestamp_utc"] == expected


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", "-120"),
        ("frp", "-5"),
        ("acq_time", "2560"),
    ],
    ids=[
        "invalid-latitude",
        "negative-frp",
        "invalid-acquisition-time",
    ],
)
def test_invalid_modis_records_are_rejected(field, value):
    record = MODIS_RECORD.copy()
    record[field] = value

    with pytest.raises(ValueError):
        harmonize_record(record, "MODIS_SP")


def test_output_schema_is_stable():
    result = harmonize_record(MODIS_RECORD, "MODIS_SP")

    expected_fields = {
        "timestamp_utc",
        "latitude",
        "longitude",
        "sensor",
        "satellite_raw",
        "source_product",
        "processing_type",
        "source_file",
        "source_record_id",
        "confidence_raw",
        "confidence_type",
        "frp_mw",
        "brightness_raw",
        "brightness_11um_raw",
        "viirs_bright_ti4",
        "viirs_bright_ti5",
        "scan",
        "track",
        "daynight_raw",
        "source_type_raw",
        "product_version",
    }

    assert set(result.keys()) == expected_fields


def test_modis_metadata_is_preserved():
    result = harmonize_record(MODIS_RECORD, "MODIS_SP")

    assert result["sensor"] == "MODIS"
    assert result["satellite_raw"] == "Aqua"
    assert result["source_product"] == "MODIS_SP"
    assert result["daynight_raw"] == "D"
    assert result["source_type_raw"] == "2"
    assert result["product_version"] == "61.03"


def test_viirs_metadata_and_sensor_fields_are_preserved():
    result = harmonize_record(VIIRS_RECORD, "VIIRS_SNPP_SP")

    assert result["sensor"] == "VIIRS"
    assert result["satellite_raw"] == "N"
    assert result["source_product"] == "VIIRS_SNPP_SP"
    assert result["brightness_raw"] is None
    assert result["brightness_11um_raw"] is None
    assert result["viirs_bright_ti4"] == 295.85
    assert result["viirs_bright_ti5"] == 263.28


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", "nan"),
        ("longitude", "inf"),
        ("frp", "nan"),
        ("brightness", "inf"),
    ],
    ids=[
        "nan-latitude",
        "infinite-longitude",
        "nan-frp",
        "infinite-brightness",
    ],
)
def test_non_finite_numeric_values_are_rejected(field, value):
    record = MODIS_RECORD.copy()
    record[field] = value

    with pytest.raises(ValueError):
        harmonize_record(record, "MODIS_SP")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", "90.0001"),
        ("longitude", "-180.0001"),
    ],
    ids=["latitude-above-maximum", "longitude-below-minimum"],
)
def test_coordinates_outside_valid_ranges_are_rejected(field, value):
    record = MODIS_RECORD.copy()
    record[field] = value

    with pytest.raises(ValueError):
        harmonize_record(record, "MODIS_SP")


def test_missing_optional_numeric_fields_become_none():
    record = MODIS_RECORD.copy()
    record["frp"] = ""
    record["brightness"] = ""
    record["bright_t31"] = None

    result = harmonize_record(record, "MODIS_SP")

    assert result["frp_mw"] is None
    assert result["brightness_raw"] is None
    assert result["brightness_11um_raw"] is None


def test_unsupported_instrument_is_rejected():
    record = MODIS_RECORD.copy()
    record["instrument"] = "UNKNOWN"

    with pytest.raises(ValueError, match="Unsupported instrument"):
        harmonize_record(record, "MODIS_SP")


def test_confidence_zero_is_preserved():
    record = MODIS_RECORD.copy()
    record["confidence"] = "0"

    result = harmonize_record(record, "MODIS_SP")

    assert result["confidence_raw"] == "0"
    assert result["confidence_type"] == "numeric_0_100"


def test_viirs_confidence_is_identified_as_categorical():
    result = harmonize_record(VIIRS_RECORD, "VIIRS_SNPP_SP")

    assert result["confidence_raw"] == "n"
    assert result["confidence_type"] == "categorical"


def test_scan_and_track_are_preserved():
    record = MODIS_RECORD.copy()
    record["scan"] = "1.2"
    record["track"] = "1.1"

    result = harmonize_record(record, "MODIS_SP")

    assert result["scan"] == 1.2
    assert result["track"] == 1.1


def test_provenance_fields_are_preserved():
    result = harmonize_record(
        MODIS_RECORD,
        "MODIS_SP",
        processing_type="SP",
        source_file="MODIS_2024.csv",
        source_record_id=125,
    )

    assert result["processing_type"] == "SP"
    assert result["source_file"] == "MODIS_2024.csv"
    assert result["source_record_id"] == 125
