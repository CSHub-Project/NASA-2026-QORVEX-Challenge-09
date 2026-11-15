"""Locked 2023 geometry-feature and empirical-interval experiment."""

from __future__ import annotations

import argparse
from datetime import date
from math import ceil

import numpy as np
import pandas as pd
import polars as pl

from pipeline.common import DATA_PROCESSED, ROOT
from pipeline.day3_harmonize import add_neighborhood_features, make_contemporaneous_grid_pairs
from pipeline.day7_upgrade import (
    GRID_KM,
    REGION,
    baseline_prediction,
    bootstrap_difference,
    estimator,
    features,
    load_historical_pairs,
    metric_rows,
)


TEST_YEAR = 2023
METHODS = ("incumbent", "geometry_aware")


def model_features(frame: pd.DataFrame, method: str, columns: pd.Index | None = None) -> pd.DataFrame:
    result = features(frame, "legacy")
    if method == "geometry_aware":
        count = frame["viirs_count"].to_numpy(float)
        scan = frame["viirs_scan_mean_km"].to_numpy(float)
        track = frame["viirs_track_mean_km"].to_numpy(float)
        area = np.where(count > 0, scan * track, 0.0)
        mean_frp = np.divide(frame["viirs_frp_mw"].to_numpy(float), count,
                             out=np.zeros(len(frame)), where=count > 0)
        density = np.divide(mean_frp, area, out=np.zeros(len(frame)), where=area > 0)
        result["viirs_pixel_area_approx_km2"] = area
        result["log_viirs_mean_frp_per_detection"] = np.log1p(mean_frp)
        result["log_viirs_frp_per_pixel_area"] = np.log1p(density)
    if columns is not None:
        result = result.reindex(columns=columns, fill_value=0)
    if not np.isfinite(result.to_numpy(float)).all():
        raise ValueError("Non-finite model feature")
    return result


def load_2020_calibration() -> pd.DataFrame:
    pairs = pl.read_parquet(DATA_PROCESSED / "contemporaneous_pairs_2017_2020_10km.parquet")
    pairs = pairs.filter(
        (pl.col("observation_date").dt.year() == 2020)
        & (pl.col("region_id") == REGION)
    )
    frame = add_neighborhood_features(pairs).to_pandas()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.date
    if frame.empty or {day.year for day in frame["observation_date"]} != {2020}:
        raise ValueError("The 2020 Western Iberia calibration split is invalid")
    return frame


def load_2023_test() -> tuple[pd.DataFrame, pd.DataFrame]:
    observations = pl.read_parquet(DATA_PROCESSED / f"overlap_observations_{TEST_YEAR}.parquet")
    if set(observations["region_id"].unique().to_list()) != {REGION}:
        raise ValueError("The 2023 observations must contain only Western Iberia")
    pairs, matches = make_contemporaneous_grid_pairs(observations, GRID_KM)
    frame = add_neighborhood_features(pairs).to_pandas()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.date
    if {day.year for day in frame["observation_date"]} != {TEST_YEAR}:
        raise ValueError("The locked test contains a different year")
    return frame, matches


def fit_predict(train: pd.DataFrame, target: pd.DataFrame, method: str) -> np.ndarray:
    x_train = model_features(train, method)
    x_target = model_features(target, method, x_train.columns)
    model = estimator("legacy")
    model.fit(x_train, train["modis_count"])
    return model.predict(x_target)


def calibration_quantile(errors: np.ndarray, alpha: float = 0.1) -> float:
    if not len(errors) or not np.isfinite(errors).all() or (errors < 0).any():
        raise ValueError("Calibration residuals must be finite, nonnegative, and nonempty")
    rank = ceil((len(errors) + 1) * (1 - alpha))
    return float(np.sort(errors)[min(rank, len(errors)) - 1])


def interval_table(test: pd.DataFrame, prediction: np.ndarray, calibration: pd.DataFrame,
                   calibration_prediction: np.ndarray) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    if not len(test) or not len(calibration):
        raise ValueError("Test or calibration split is empty")
    quantiles = {}
    low = np.zeros(len(test), dtype=float)
    high = np.zeros(len(test), dtype=float)
    for daynight in ("D", "N"):
        c_mask = calibration["daynight"].to_numpy() == daynight
        t_mask = test["daynight"].to_numpy() == daynight
        quantiles[daynight] = calibration_quantile(
            np.abs(calibration.loc[c_mask, "modis_count"].to_numpy(float) - calibration_prediction[c_mask])
        )
        low[t_mask] = np.maximum(0.0, prediction[t_mask] - quantiles[daynight])
        high[t_mask] = prediction[t_mask] + quantiles[daynight]
    actual = test["modis_count"].to_numpy(float)
    rows = []
    for group in ("all", "D", "N"):
        mask = np.ones(len(test), dtype=bool) if group == "all" else test["daynight"].to_numpy() == group
        rows.append({
            "year": TEST_YEAR,
            "region_id": REGION,
            "daynight": group,
            "cell_passes": int(mask.sum()),
            "nominal_coverage": 0.9,
            "empirical_coverage": float(np.mean((actual[mask] >= low[mask]) & (actual[mask] <= high[mask]))),
            "mean_interval_width": float(np.mean(high[mask] - low[mask])),
            "calibration_quantile": None if group == "all" else quantiles[group],
        })
    return pd.DataFrame(rows), low, high


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-only", action="store_true")
    args = parser.parse_args()
    historical = load_historical_pairs()
    fit = historical[historical["observation_date"] < date(2019, 1, 1)]
    validation = historical[historical["observation_date"] >= date(2019, 1, 1)]
    if {day.year for day in historical["observation_date"]} != {2017, 2018, 2019}:
        raise ValueError("Historical model fitting includes a forbidden year")

    validation_predictions = {name: fit_predict(fit, validation, name) for name in METHODS}
    validation_rows = [row for name in METHODS for row in metric_rows(
        validation, name, validation_predictions[name], "2019_selection")]
    validation_table = pd.DataFrame(validation_rows)
    west = validation_table[(validation_table.region_id == REGION) & (validation_table.daynight == "all")].set_index("model")
    selected = "geometry_aware" if west.loc["geometry_aware", "wape"] < west.loc["incumbent", "wape"] else "incumbent"
    output = ROOT / "outputs" / "tables"
    output.mkdir(parents=True, exist_ok=True)
    validation_table.to_csv(output / "geometry_2019_selection.csv", index=False)
    print("selected_by_2019=", selected)
    print(west[["cell_passes", "wape", "mae"]].to_string())
    if args.validation_only:
        return

    # Selection precedes opening the 2023 file; 2020 is used only for interval calibration.
    calibration = load_2020_calibration()
    calibration_prediction = fit_predict(historical, calibration, selected)
    test, matches = load_2023_test()
    predictions = {name: fit_predict(historical, test, name) for name in METHODS}
    predictions["fixed_ratio"] = baseline_prediction(historical, test)
    test_table = pd.DataFrame([
        row for name, prediction in predictions.items()
        for row in metric_rows(test, name, prediction, "2023_locked_test")
    ])
    test_index = test_table.set_index(["model", "region_id", "daynight"])
    bootstrap = bootstrap_difference(test, predictions["geometry_aware"], predictions["incumbent"],
                                     "geometry_aware_minus_incumbent_mae")
    upper = float(bootstrap.iloc[0]["ci_97_5"])
    promote = (
        selected == "geometry_aware"
        and test_index.loc[("geometry_aware", REGION, "all"), "wape"]
        < min(test_index.loc[("incumbent", REGION, "all"), "wape"],
              test_index.loc[("fixed_ratio", REGION, "all"), "wape"])
        and all(test_index.loc[("geometry_aware", REGION, d), "wape"]
                <= test_index.loc[("incumbent", REGION, d), "wape"] for d in ("D", "N"))
        and upper < 0
    )
    intervals, low, high = interval_table(test, predictions[selected], calibration, calibration_prediction)
    scored = test[["pair_id", "region_id", "observation_date", "daynight", "cell_x", "cell_y",
                   "modis_count", "viirs_count"]].copy()
    for name, prediction in predictions.items():
        scored[f"{name}_prediction"] = prediction
    scored["selected_method"] = selected
    scored["selected_interval_low"] = low
    scored["selected_interval_high"] = high

    test_table.to_csv(output / "geometry_2023_locked_test.csv", index=False)
    bootstrap.to_csv(output / "geometry_2023_bootstrap.csv", index=False)
    intervals.to_csv(output / "geometry_2023_interval_coverage.csv", index=False)
    scored.to_csv(output / "geometry_2023_cell_pass_predictions.csv", index=False)
    matches.to_csv(output / "geometry_2023_pass_matches.csv", index=False)
    print("promoted_on_2023=", bool(promote))
    print(test_table[(test_table.region_id == REGION) & (test_table.daynight == "all")].to_string(index=False))
    print(bootstrap.to_string(index=False))
    print(intervals.to_string(index=False))


if __name__ == "__main__":
    main()
