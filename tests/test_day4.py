from datetime import date

import pandas as pd
import polars as pl

from pipeline.day4_multiyear import build_calendar_ready


def test_calendar_marks_missing_coverage_instead_of_inventing_zero():
    pairs = pl.DataFrame(
        {
            "pair_id": ["history-pair"],
            "region_id": ["test"],
            "observation_date": [date(2019, 1, 2)],
            "daynight": ["D"],
            "modis_count": [3],
        }
    )
    scored = pd.DataFrame(
        {
            "pair_id": ["holdout-pair"],
            "region_id": ["test"],
            "observation_date": [date(2020, 1, 2)],
            "daynight": ["D"],
            "selected_modis_count": [4.5],
        }
    )
    calendar = build_calendar_ready(pairs, scored, [2019, 2020], date(2020, 1, 1))

    missing = calendar[
        (calendar["observation_date"] == pd.Timestamp("2020-01-03"))
        & (calendar["daynight"] == "D")
    ].iloc[0]
    assert not missing["has_matched_coverage"]
    assert pd.isna(missing["activity_count"])

    observed = calendar[
        (calendar["observation_date"] == pd.Timestamp("2020-01-02"))
        & (calendar["daynight"] == "D")
    ].iloc[0]
    assert observed["has_matched_coverage"]
    assert observed["activity_count"] == 4.5
