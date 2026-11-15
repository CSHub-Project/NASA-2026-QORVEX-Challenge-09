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


def test_historical_anomalies_use_other_years_without_self_inclusion():
    pairs = pl.DataFrame(
        {
            "pair_id": ["p17", "p18", "p19"],
            "region_id": ["test", "test", "test"],
            "observation_date": [
                date(2017, 1, 2),
                date(2018, 1, 2),
                date(2019, 1, 2),
            ],
            "daynight": ["D", "D", "D"],
            "modis_count": [1, 3, 9],
        }
    )
    scored = pd.DataFrame(
        {
            "pair_id": ["p20"],
            "region_id": ["test"],
            "observation_date": [date(2020, 1, 2)],
            "daynight": ["D"],
            "selected_modis_count": [5.0],
        }
    )

    calendar = build_calendar_ready(
        pairs, scored, [2017, 2018, 2019, 2020], date(2020, 1, 1)
    )
    observed = calendar[
        calendar["has_matched_coverage"] & (calendar["daynight"] == "D")
    ].set_index("year")

    assert observed.loc[2017, "percentile_vs_history"] == 100.0 / 6.0
    assert observed.loc[2018, "percentile_vs_history"] == 50.0
    assert observed.loc[2019, "percentile_vs_history"] == 500.0 / 6.0
    assert observed.loc[2020, "percentile_vs_history"] == 62.5
    assert observed["robust_z_vs_history"].notna().all()
