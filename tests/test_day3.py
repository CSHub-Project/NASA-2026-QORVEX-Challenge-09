from datetime import date, datetime, timezone

import pandas as pd
import polars as pl

from pipeline.day3_harmonize import add_neighborhood_features, build_pass_catalog, match_passes


def test_pass_catalog_splits_large_time_gaps():
    observations = pl.DataFrame(
        {
            "sensor_family": ["MODIS", "MODIS", "MODIS"],
            "satellite": ["Aqua", "Aqua", "Aqua"],
            "region_id": ["test"] * 3,
            "daynight": ["D"] * 3,
            "acquired_at_utc": [
                datetime(2019, 1, 1, 12, 0, tzinfo=timezone.utc),
                datetime(2019, 1, 1, 12, 10, tzinfo=timezone.utc),
                datetime(2019, 1, 1, 13, 0, tzinfo=timezone.utc),
            ],
        }
    )
    mapping, summary = build_pass_catalog(observations, gap_minutes=30)
    assert mapping["sensor_pass_id"].n_unique() == 2
    assert len(summary) == 2


def test_pass_matching_is_nearest_and_one_to_one():
    base = {
        "region_id": "test",
        "observation_date": date(2019, 1, 1),
        "daynight": "D",
        "timestamp_count": 1,
    }
    summary = pd.DataFrame(
        [
            {
                **base,
                "sensor_family": "MODIS",
                "sensor_pass_id": "m1",
                "pass_time_utc": pd.Timestamp("2019-01-01T12:00Z"),
            },
            {
                **base,
                "sensor_family": "MODIS",
                "sensor_pass_id": "m2",
                "pass_time_utc": pd.Timestamp("2019-01-01T12:50Z"),
            },
            {
                **base,
                "sensor_family": "VIIRS",
                "sensor_pass_id": "v1",
                "pass_time_utc": pd.Timestamp("2019-01-01T12:05Z"),
            },
            {
                **base,
                "sensor_family": "VIIRS",
                "sensor_pass_id": "v2",
                "pass_time_utc": pd.Timestamp("2019-01-01T13:40Z"),
            },
        ]
    )
    matches = match_passes(summary, max_match_minutes=60)
    assert len(matches) == 2
    assert set(zip(matches["modis_pass_id"], matches["viirs_pass_id"])) == {
        ("m1", "v1"),
        ("m2", "v2"),
    }


def test_neighborhood_features_include_adjacent_cells():
    pairs = pl.DataFrame(
        {
            "pair_id": ["p1", "p1"],
            "region_id": ["test", "test"],
            "observation_date": [date(2019, 1, 1), date(2019, 1, 1)],
            "daynight": ["D", "D"],
            "cell_x": [10, 11],
            "cell_y": [20, 20],
            "viirs_count": [1, 2],
            "viirs_frp_mw": [3.0, 5.0],
        }
    )
    enriched = add_neighborhood_features(pairs, radius=1)
    assert enriched["viirs_count_3x3"].to_list() == [3, 3]
    assert enriched["viirs_frp_3x3_mw"].to_list() == [8.0, 8.0]
