import numpy as np

from pipeline.day7_upgrade import load_historical_pairs
from pipeline.evaluate_2023 import calibration_quantile, model_features


def test_geometry_features_are_finite_for_modis_only_cells():
    frame = load_historical_pairs()
    sample = frame[frame["viirs_count"] == 0].head(10)
    assert not sample.empty
    candidate = model_features(sample, "geometry_aware")
    incumbent = model_features(sample, "incumbent")
    assert set(incumbent.columns).issubset(candidate.columns)
    assert np.isfinite(candidate.to_numpy(float)).all()
    assert (candidate["viirs_pixel_area_approx_km2"] == 0).all()
    assert (candidate["log_viirs_frp_per_pixel_area"] == 0).all()


def test_finite_sample_quantile_uses_next_rank():
    assert calibration_quantile(np.arange(1, 11, dtype=float), alpha=0.2) == 9.0
