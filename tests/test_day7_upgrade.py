from datetime import date

from pipeline.day7_upgrade import features, load_historical_pairs, MONOTONE_FEATURES


def test_candidate_features_remove_modis_match_time():
    historical = load_historical_pairs()
    sample = historical.head(20)
    legacy = features(sample, "legacy")
    viirs_only = features(sample, "viirs_only")
    assert "pass_time_difference" in legacy.columns
    assert "pass_time_difference" not in viirs_only.columns
    assert set(MONOTONE_FEATURES).issubset(viirs_only.columns)


def test_later_year_excluded_from_model_fit():
    historical = load_historical_pairs()
    years = {day.year for day in historical["observation_date"]}
    assert years == {2017, 2018, 2019}
    assert not historical[historical["observation_date"] >= date(2020, 1, 1)].shape[0]
