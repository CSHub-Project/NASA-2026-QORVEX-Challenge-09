"""Frozen VIIRS-only count-model comparison on a later European year."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import argparse

import numpy as np
import pandas as pd
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pipeline.common import DATA_PROCESSED, ROOT
from pipeline.day3_harmonize import (
    add_neighborhood_features,
    fit_baseline,
    make_contemporaneous_grid_pairs,
    make_features,
)


GRID_KM = 10.0
REGION = "western_iberia"
TRAIN_END = date(2019, 1, 1)
TEST_YEAR = 2022
MODELS = ("viirs_only", "monotone_viirs_only", "legacy")
MONOTONE_FEATURES = (
    "viirs_count",
    "log_viirs_count",
    "log_viirs_frp",
    "viirs_count_3x3",
    "log_viirs_count_3x3",
    "log_viirs_frp_3x3",
)
PARAMETERS = dict(
    loss="poisson",
    learning_rate=0.05,
    max_iter=180,
    max_leaf_nodes=15,
    min_samples_leaf=30,
    l2_regularization=1.0,
    random_state=42,
)


@dataclass(frozen=True)
class UpgradeResult:
    validation: pd.DataFrame
    test: pd.DataFrame
    bootstrap: pd.DataFrame
    chosen: str
    promoted: bool
    matches: pd.DataFrame


def features(frame: pd.DataFrame, name: str, columns: pd.Index | None = None) -> pd.DataFrame:
    output = make_features(frame, GRID_KM)
    if name != "legacy":
        output = output.drop(columns="pass_time_difference")
    if columns is not None:
        output = output.reindex(columns=columns, fill_value=0)
    return output


def estimator(name: str) -> HistGradientBoostingRegressor:
    parameters = PARAMETERS.copy()
    if name == "monotone_viirs_only":
        parameters["monotonic_cst"] = {feature: 1 for feature in MONOTONE_FEATURES}
    return HistGradientBoostingRegressor(**parameters)


def metric_rows(frame: pd.DataFrame, name: str, prediction: np.ndarray, split: str) -> list[dict]:
    result = frame[["region_id", "daynight", "modis_count"]].copy()
    result["prediction"] = prediction
    groups = [("all", "all", result)]
    groups.extend((REGION, daynight, group) for daynight, group in result[
        result["region_id"] == REGION
    ].groupby("daynight"))
    groups.append((REGION, "all", result[result["region_id"] == REGION]))
    output = []
    for region_id, daynight, group in groups:
        observed = group["modis_count"].to_numpy(float)
        predicted = group["prediction"].to_numpy(float)
        error = predicted - observed
        output.append({
            "split": split,
            "model": name,
            "region_id": region_id,
            "daynight": daynight,
            "cell_passes": len(group),
            "wape": float(np.abs(error).sum() / max(observed.sum(), 1e-12)),
            "mae": float(np.abs(error).mean()),
            "signed_bias": float(error.mean()),
        })
    return output


def baseline_prediction(train: pd.DataFrame, target: pd.DataFrame) -> np.ndarray:
    ratios = fit_baseline(train, date(max(train["observation_date"]).year + 1, 1, 1))
    ratio_map = ratios.set_index(["region_id", "daynight"])["count_ratio"]
    mapped = pd.MultiIndex.from_frame(target[["region_id", "daynight"]]).map(ratio_map)
    if pd.isna(mapped).any():
        raise ValueError("Missing region/day-night fixed ratio")
    return target["viirs_count"].to_numpy(float) * mapped.to_numpy(float)


def load_historical_pairs() -> pd.DataFrame:
    path = DATA_PROCESSED / "contemporaneous_pairs_2017_2020_10km.parquet"
    if not path.is_file():
        raise FileNotFoundError(path)
    pairs = pl.read_parquet(path).filter(pl.col("observation_date").dt.year() <= 2019)
    frame = add_neighborhood_features(pairs).to_pandas()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.date
    return frame


def load_later_pairs() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = DATA_PROCESSED / f"overlap_observations_{TEST_YEAR}.parquet"
    if not path.is_file():
        raise FileNotFoundError(path)
    observations = pl.read_parquet(path)
    if set(observations["region_id"].unique().to_list()) != {REGION}:
        raise ValueError("The later-year normalized file must contain only Western Iberia")
    pairs, matches = make_contemporaneous_grid_pairs(observations, GRID_KM)
    frame = add_neighborhood_features(pairs).to_pandas()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.date
    if {day.year for day in frame["observation_date"]} != {TEST_YEAR}:
        raise ValueError("The later-year score contains a different year")
    return frame, matches


def bootstrap_difference(
    frame: pd.DataFrame, candidate: np.ndarray, legacy: np.ndarray,
    comparison: str, replicates: int = 500,
) -> pd.DataFrame:
    working = frame[["observation_date", "modis_count"]].copy()
    working["candidate_error"] = np.abs(candidate - working["modis_count"])
    working["legacy_error"] = np.abs(legacy - working["modis_count"])
    daily = working.groupby("observation_date").agg(
        candidate_error=("candidate_error", "sum"),
        legacy_error=("legacy_error", "sum"),
        cells=("modis_count", "size"),
    )
    rng = np.random.default_rng(42)
    deltas = []
    for _ in range(replicates):
        sample = daily.iloc[rng.integers(0, len(daily), size=len(daily))]
        deltas.append(float((sample["candidate_error"].sum() - sample["legacy_error"].sum()) / sample["cells"].sum()))
    return pd.DataFrame([{
        "comparison": comparison,
        "replicates": replicates,
        "estimate": float((working["candidate_error"].sum() - working["legacy_error"].sum()) / len(working)),
        "ci_2_5": float(np.quantile(deltas, 0.025)),
        "ci_97_5": float(np.quantile(deltas, 0.975)),
        "fraction_bootstrap_candidate_better": float(np.mean(np.array(deltas) < 0)),
    }])


def select_historical() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    historical = load_historical_pairs()
    fit = historical[historical["observation_date"] < TRAIN_END].copy()
    validation = historical[historical["observation_date"] >= TRAIN_END].copy()
    if not len(fit) or not len(validation):
        raise ValueError("Historical fit or validation sample is empty")

    validation_predictions: dict[str, np.ndarray] = {
        "fixed_ratio": baseline_prediction(fit, validation)
    }
    for name in MODELS:
        x_fit = features(fit, name)
        x_validation = features(validation, name, x_fit.columns)
        model = estimator(name)
        model.fit(x_fit, fit["modis_count"])
        validation_predictions[name] = model.predict(x_validation)
    validation_table = pd.DataFrame([
        row for name, prediction in validation_predictions.items()
        for row in metric_rows(validation, name, prediction, "2019_validation")
    ])
    west_validation = validation_table[
        (validation_table["region_id"] == REGION)
        & (validation_table["daynight"] == "all")
        & (validation_table["model"].isin(MODELS))
    ].set_index("model")
    chosen = min(MODELS, key=lambda name: (west_validation.loc[name, "wape"], MODELS.index(name)))
    return historical, validation_table, chosen


def evaluate() -> UpgradeResult:
    historical, validation_table, chosen = select_historical()
    # The later-year data is opened only after all validation scores and the choice are fixed.
    later, matches = load_later_pairs()
    test_predictions: dict[str, np.ndarray] = {
        "fixed_ratio": baseline_prediction(historical, later)
    }
    for name in MODELS:
        x_train = features(historical, name)
        x_test = features(later, name, x_train.columns)
        model = estimator(name)
        model.fit(x_train, historical["modis_count"])
        test_predictions[name] = model.predict(x_test)
    test_table = pd.DataFrame([
        row for name, prediction in test_predictions.items()
        for row in metric_rows(later, name, prediction, "2022_locked_test")
    ])
    test_index = test_table.set_index(["model", "region_id", "daynight"])
    selected_wape = test_index.loc[(chosen, REGION, "all"), "wape"]
    promoted = (
        chosen != "legacy"
        and selected_wape < test_index.loc[("legacy", REGION, "all"), "wape"]
        and selected_wape < test_index.loc[("fixed_ratio", REGION, "all"), "wape"]
        and all(test_index.loc[(chosen, REGION, d), "wape"] <= test_index.loc[("legacy", REGION, d), "wape"] for d in ("D", "N"))
    )
    # Additional candidate comparisons are descriptive only; selection was locked on 2019.
    bootstrap = pd.concat([
        bootstrap_difference(later, test_predictions[name], test_predictions["legacy"],
                             f"{name}_minus_legacy_mae")
        for name in ("fixed_ratio", "viirs_only", "monotone_viirs_only")
    ], ignore_index=True)
    return UpgradeResult(validation_table, test_table, bootstrap, chosen, bool(promoted), matches)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-only", action="store_true")
    args = parser.parse_args()
    if args.validation_only:
        _, table, chosen = select_historical()
        print("selected_by_2019=", chosen)
        print(table[(table.region_id == REGION) & (table.daynight == "all")].to_string(index=False))
        return
    result = evaluate()
    tables = ROOT / "outputs" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    result.validation.to_csv(tables / "day7_2019_candidate_selection.csv", index=False)
    result.test.to_csv(tables / "day7_2022_locked_test.csv", index=False)
    result.bootstrap.to_csv(tables / "day7_2022_candidate_bootstrap.csv", index=False)
    result.matches.to_csv(tables / "day7_2022_western_iberia_pass_matches.csv", index=False)
    print("selected_by_2019=", result.chosen, "promoted_on_2022=", result.promoted)
    print(result.validation[(result.validation.region_id == REGION) & (result.validation.daynight == "all")].to_string(index=False))
    print(result.test[(result.test.region_id == REGION) & (result.test.daynight == "all")].to_string(index=False))
    print(result.bootstrap.to_string(index=False))


if __name__ == "__main__":
    main()
