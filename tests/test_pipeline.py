from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import polars as pl
import pytest

from pipeline.common import load_regions
from pipeline.analyze_overlap import read_source
from pipeline.day2_baseline import add_equal_area_cells, make_sensor_pairs
from pipeline.fetch_firms import download_chunk, iter_chunks


def test_regions_have_valid_bboxes():
    regions = load_regions()
    assert len(regions) == 4
    assert len({region.id for region in regions}) == 4
    for region in regions:
        west, south, east, north = region.bbox
        assert -180 <= west < east <= 180
        assert -90 <= south < north <= 90


def test_day9_regions_are_separate_and_valid():
    path = Path(__file__).parents[1] / "configs" / "day9_independent_regions.json"
    regions = load_regions(path)
    assert len(regions) == 3
    assert not ({region.id for region in regions} & {region.id for region in load_regions()})
    for region in regions:
        west, south, east, north = region.bbox
        assert -180 <= west < east <= 180
        assert -90 <= south < north <= 90


def test_2019_chunks_cover_every_day_once():
    chunks = list(iter_chunks(2019))
    assert chunks[0] == (date(2019, 1, 1), 5)
    assert sum(days for _, days in chunks) == 365
    assert all(1 <= days <= 5 for _, days in chunks)
    assert chunks[-1][0] + __import__("datetime").timedelta(days=chunks[-1][1]) == date(2020, 1, 1)


def test_acquisition_time_is_zero_padded_and_timezone_aware(tmp_path):
    sample = tmp_path / "sample.csv"
    sample.write_text(
        "latitude,longitude,acq_date,acq_time,frp,daynight\n"
        "35.0,52.0,2019-01-02,5,1.5,N\n",
        encoding="utf-8",
    )

    frame = read_source([sample], "MODIS_SP", "test_region")

    assert frame["acq_time_hhmm"].item() == "0005"
    assert str(frame.schema["acquired_at_utc"]) == "Datetime(time_unit='us', time_zone='UTC')"
    assert frame["acquired_at_utc"].item().isoformat() == "2019-01-02T00:05:00+00:00"


def test_equal_area_grid_uses_integer_cells():
    frame = pl.DataFrame(
        {
            "longitude": [0.0, 0.01],
            "latitude": [0.0, 0.01],
            "acquired_at_utc": [
                datetime(2019, 1, 1, tzinfo=timezone.utc),
                datetime(2019, 1, 1, tzinfo=timezone.utc),
            ],
        }
    )
    gridded = add_equal_area_cells(frame, grid_km=10)
    assert gridded["cell_x"].to_list() == [0, 0]
    assert gridded["cell_y"].to_list() == [0, 0]


def test_sensor_pairing_preserves_one_sided_zeros():
    frame = pl.DataFrame(
        {
            "longitude": [0.0, 1.0],
            "latitude": [0.0, 1.0],
            "acquired_at_utc": [
                datetime(2019, 1, 1, 12, tzinfo=timezone.utc),
                datetime(2019, 1, 1, 12, tzinfo=timezone.utc),
            ],
            "sensor_family": ["MODIS", "VIIRS"],
            "satellite": ["Aqua", "N"],
            "region_id": ["test", "test"],
            "daynight": ["D", "D"],
            "frp": [2.0, 3.0],
        }
    )
    pairs = make_sensor_pairs(frame, grid_km=10)
    assert pairs.height == 2
    assert pairs["modis_count"].sum() == 1
    assert pairs["viirs_count"].sum() == 1
    assert pairs.filter(pl.col("modis_count") == 0).height == 1
    assert pairs.filter(pl.col("viirs_count") == 0).height == 1


def test_download_error_never_exposes_map_key(monkeypatch, tmp_path):
    secret = "secret-map-key"

    class RejectingClient:
        def get(self, url):
            request = httpx.Request("GET", url)
            return httpx.Response(
                400,
                text=f"limit reached for {secret}",
                request=request,
            )

    monkeypatch.setattr("pipeline.fetch_firms.MAX_ATTEMPTS", 1)
    with pytest.raises(RuntimeError) as error:
        download_chunk(
            RejectingClient(),
            secret,
            "MODIS_SP",
            "0,0,1,1",
            date(2019, 1, 1),
            1,
            Path(tmp_path) / "output.csv",
        )
    assert secret not in str(error.value)
    assert "[REDACTED]" in str(error.value)

