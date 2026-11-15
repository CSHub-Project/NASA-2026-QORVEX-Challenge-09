
import h3
import pytest

from qorvex.spatial_index import (
    H3_RESOLUTIONS,
    add_h3_indices,
)


def test_add_h3_indices_preserves_original_fields():
    record = {
        "latitude": -37.6459,
        "longitude": 145.0045,
        "sensor": "MODIS",
        "frp_mw": 7.5,
    }

    result = add_h3_indices(record)

    assert result["latitude"] == record["latitude"]
    assert result["longitude"] == record["longitude"]
    assert result["sensor"] == record["sensor"]
    assert result["frp_mw"] == record["frp_mw"]


def test_add_h3_indices_does_not_modify_original_record():
    record = {
        "latitude": -37.6459,
        "longitude": 145.0045,
    }

    original = record.copy()

    add_h3_indices(record)

    assert record == original


@pytest.mark.parametrize("resolution", H3_RESOLUTIONS)
def test_h3_cell_has_expected_resolution(resolution):
    record = {
        "latitude": -37.6459,
        "longitude": 145.0045,
    }

    result = add_h3_indices(record)

    cell = result[f"h3_res{resolution}"]

    assert h3.is_valid_cell(cell)
    assert h3.get_resolution(cell) == resolution


@pytest.mark.parametrize("latitude,longitude", [
    (-91, 145),
    (91, 145),
    (-37, -181),
    (-37, 181),
])
def test_invalid_coordinates_are_rejected(latitude, longitude):
    record = {
        "latitude": latitude,
        "longitude": longitude,
    }

    with pytest.raises(ValueError):
        add_h3_indices(record)


@pytest.mark.parametrize("latitude,longitude", [
    (None, 145),
    (-37, None),
    ("invalid", 145),
    (-37, "invalid"),
    (float("nan"), 145),
    (-37, float("inf")),
])
def test_non_numeric_or_non_finite_coordinates_are_rejected(
    latitude,
    longitude,
):
    record = {
        "latitude": latitude,
        "longitude": longitude,
    }

    with pytest.raises(ValueError):
        add_h3_indices(record)


def test_boolean_coordinates_are_rejected():
    record = {
        "latitude": True,
        "longitude": 145,
    }

    with pytest.raises(ValueError):
        add_h3_indices(record)
