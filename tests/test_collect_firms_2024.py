
import pytest

from scripts.collect_firms_2024 import (
    REQUIRED_COLUMNS,
    OUTPUT_COLUMNS,
    validate_csv_header,
    get_processing_type,
)


def test_valid_firms_csv_header_is_accepted():
    header = ",".join(sorted(REQUIRED_COLUMNS))
    content = f"{header}\n"

    result = validate_csv_header(content)

    assert set(result) == REQUIRED_COLUMNS


def test_empty_csv_response_is_rejected():
    with pytest.raises(ValueError, match="no CSV header"):
        validate_csv_header("")


def test_csv_missing_required_columns_is_rejected():
    content = "latitude,longitude,acq_date\n"

    with pytest.raises(
        ValueError,
        match="missing columns",
    ):
        validate_csv_header(content)


@pytest.mark.parametrize(
    ("product", "expected"),
    [
        ("MODIS_SP", "SP"),
        ("VIIRS_SNPP_SP", "SP"),
        ("VIIRS_NOAA20_SP", "SP"),
        ("VIIRS_NOAA21_NRT", "NRT"),
    ],
)
def test_get_processing_type(product, expected):
    assert get_processing_type(product) == expected


def test_get_processing_type_rejects_unknown_suffix():
    with pytest.raises(
        ValueError,
        match="Unsupported FIRMS processing type",
    ):
        get_processing_type("MODIS_UNKNOWN")


def test_collector_output_columns_match_harmonizer_schema():
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

    assert set(OUTPUT_COLUMNS) == expected_fields
    assert len(OUTPUT_COLUMNS) == len(expected_fields)
