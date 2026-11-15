import numpy as np
import pytest
import h5py

from pipeline.day8_swath_mask import aggregate_fire_mask, read_viirs_pair


def test_clear_cloud_and_fire_remain_distinct() -> None:
    mask = np.array([[5, 4, 3], [7, 5, 0]], dtype=np.uint8)
    latitude = np.full(mask.shape, 40.0)
    longitude = np.full(mask.shape, -8.0)
    result = aggregate_fire_mask(mask, latitude, longitude, (-9, 39, -7, 41))
    assert len(result) == 1
    row = result.iloc[0]
    assert row["clear_nonfire_land"] == 2
    assert row["cloud"] == 1
    assert row["water"] == 1
    assert row["fire"] == 1
    assert row["not_processed"] == 1
    assert not row["observed_clear_no_detection"]


def test_clear_sample_without_detection_is_explicit() -> None:
    mask = np.array([[5, 4]], dtype=np.uint8)
    lat = np.array([[40.0, 40.0]])
    lon = np.array([[-8.0, -8.0]])
    result = aggregate_fire_mask(mask, lat, lon, (-9, 39, -7, 41))
    assert bool(result.loc[0, "observed_clear_no_detection"])
    assert result.loc[0, "cloud"] == 1
    assert result.loc[0, "valid_land_pixels"] == 1


def test_cloud_only_is_not_a_clear_negative() -> None:
    mask = np.array([[4, 4]], dtype=np.uint8)
    lat = np.array([[40.0, 40.0]])
    lon = np.array([[-8.0, -8.0]])
    result = aggregate_fire_mask(mask, lat, lon, (-9, 39, -7, 41))
    assert not bool(result.loc[0, "observed_clear_no_detection"])


def test_array_alignment_required() -> None:
    with pytest.raises(ValueError, match="identical shapes"):
        aggregate_fire_mask(np.zeros((2, 2)), np.zeros((1, 2)), np.zeros((2, 2)),
                            (-9, 39, -7, 41))


def test_viirs_pair_reads_nested_geolocation(tmp_path) -> None:
    fire_file = tmp_path / "fire.nc"
    geo_file = tmp_path / "geo.nc"
    with h5py.File(fire_file, "w") as fire:
        fire.create_dataset("fire mask", data=np.array([[5, 7]], dtype="u1"))
    with h5py.File(geo_file, "w") as geo:
        group = geo.create_group("geolocation_data")
        group.create_dataset("latitude", data=[[40.0, 40.0]])
        group.create_dataset("longitude", data=[[-8.0, -8.0]])
    mask, latitude, longitude = read_viirs_pair(fire_file, geo_file)
    assert mask.tolist() == [[5, 7]]
    assert latitude.shape == longitude.shape == mask.shape
