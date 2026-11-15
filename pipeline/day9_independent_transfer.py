"""Locked 2024 transfer test on three regions absent from model development."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

from pipeline.common import DATA_PROCESSED, ROOT, load_regions
from pipeline.day3_harmonize import (
    add_neighborhood_features,
    make_contemporaneous_grid_pairs,
    make_features,
)
from pipeline.fetch_firms import SOURCES, iter_chunks


GRID_KM = 10.0
TRAIN_END_YEAR = 2019
TEST_YEAR = 2024
REGIONS_FILE = ROOT / "configs" / "day9_independent_regions.json"
TEST_OBSERVATIONS = DATA_PROCESSED / "overlap_observations_2024_day9_independent.parquet"
RAW_MANIFEST = ROOT / "outputs" / "tables" / "day9_firms_raw_manifest_2024.csv"
BOOTSTRAP_REPLICATES = 500
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
class TransferResult:
    metrics: pd.DataFrame
    bootstrap: pd.DataFrame
    decision: pd.DataFrame
    matches: pd.DataFrame
    predictions: pd.DataFrame


def verify_manifest(path: Path = RAW_MANIFEST) -> None:
    manifest = pd.read_csv(path)
    regions = {region.id for region in load_regions(REGIONS_FILE)}
    expected_partitions = {f"{start.isoformat()}_{days}d.csv" for start, days in iter_chunks(TEST_YEAR)}
    expected = {
        (region, source, partition)
        for region in regions for source in SOURCES for partition in expected_partitions
    }
    actual = set(manifest[["region_id", "source", "partition"]].itertuples(index=False, name=None))
    if actual != expected:
        raise ValueError(
            f"Day-9 raw manifest mismatch: missing={len(expected - actual)}, extra={len(actual - expected)}"
        )
    if manifest["sha256"].str.fullmatch(r"[0-9a-f]{64}", case=False).ne(True).any():
        raise ValueError("Day-9 manifest contains an invalid SHA-256 digest")


def load_training_pairs() -> pd.DataFrame:
    path = DATA_PROCESSED / "contemporaneous_pairs_2017_2020_10km.parquet"
    pairs = pl.read_parquet(path).filter(pl.col("observation_date").dt.year() <= TRAIN_END_YEAR)
    expected = {region.id for region in load_regions()}
    if set(pairs["region_id"].unique()) != expected:
        raise ValueError("Historical training corpus does not contain exactly the four sealed regions")
    frame = add_neighborhood_features(pairs).to_pandas()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.date
    if max(day.year for day in frame["observation_date"]) != TRAIN_END_YEAR:
        raise ValueError("Historical training corpus does not end in 2019")
    return frame


def load_test_pairs() -> tuple[pd.DataFrame, pd.DataFrame]:
    observations = pl.read_parquet(TEST_OBSERVATIONS)
    expected = {region.id for region in load_regions(REGIONS_FILE)}
    if set(observations["region_id"].unique()) != expected:
        raise ValueError("2024 observations do not contain exactly the sealed day-9 regions")
    pairs, matches = make_contemporaneous_grid_pairs(observations, GRID_KM)
    frame = add_neighborhood_features(pairs).to_pandas()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.date
    if {day.year for day in frame["observation_date"]} != {TEST_YEAR}:
        raise ValueError("Day-9 test pairs contain a year other than 2024")
    return frame, matches


def metric_table(frame: pd.DataFrame) -> pd.DataFrame:
    groups: list[tuple[str, str, pd.DataFrame]] = [("all", "all", frame)]
    groups.extend((region, "all", group) for region, group in frame.groupby("region_id"))
    groups.extend((region, daynight, group) for (region, daynight), group in frame.groupby(["region_id", "daynight"]))
    rows = []
    for region, daynight, group in groups:
        observed = group["modis_count"].to_numpy(float)
        for method in ("baseline", "model"):
            predicted = group[f"{method}_prediction"].to_numpy(float)
            error = predicted - observed
            rho = spearmanr(observed, predicted).statistic if len(group) > 1 else np.nan
            rows.append({
                "region_id": region,
                "daynight": daynight,
                "method": method,
                "cell_passes": len(group),
                "modis_count": int(observed.sum()),
                "mae": float(np.abs(error).mean()),
                "wape": float(np.abs(error).sum() / max(observed.sum(), 1e-12)),
                "signed_bias": float(error.mean()),
                "spearman": float(rho) if np.isfinite(rho) else np.nan,
            })
    return pd.DataFrame(rows)


def date_block_bootstrap(frame: pd.DataFrame, replicates: int = BOOTSTRAP_REPLICATES) -> pd.DataFrame:
    working = frame[["observation_date", "modis_count", "baseline_prediction", "model_prediction"]].copy()
    working["baseline_error"] = np.abs(working["baseline_prediction"] - working["modis_count"])
    working["model_error"] = np.abs(working["model_prediction"] - working["modis_count"])
    daily = working.groupby("observation_date").agg(
        baseline_error=("baseline_error", "sum"), model_error=("model_error", "sum"),
        cells=("modis_count", "size"),
    )
    rng = np.random.default_rng(42)
    deltas = np.empty(replicates)
    for index in range(replicates):
        sample = daily.iloc[rng.integers(0, len(daily), size=len(daily))]
        deltas[index] = (sample["model_error"].sum() - sample["baseline_error"].sum()) / sample["cells"].sum()
    estimate = (working["model_error"].sum() - working["baseline_error"].sum()) / len(working)
    return pd.DataFrame([{
        "comparison": "model_minus_baseline_mae",
        "replicates": replicates,
        "utc_dates": len(daily),
        "estimate": float(estimate),
        "ci_2_5": float(np.quantile(deltas, 0.025)),
        "ci_97_5": float(np.quantile(deltas, 0.975)),
        "fraction_model_better": float(np.mean(deltas < 0)),
    }])


def make_decision(metrics: pd.DataFrame, bootstrap: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    region_ids = [region.id for region in load_regions(REGIONS_FILE)]
    match_counts = matches.groupby("region_id").size().reindex(region_ids, fill_value=0)
    indexed = metrics.set_index(["region_id", "daynight", "method"])
    support = all(
        match_counts[region] >= 50
        and indexed.loc[(region, "all", "model"), "cell_passes"] >= 500
        for region in region_ids
    )
    pooled_better = indexed.loc[("all", "all", "model"), "wape"] < indexed.loc[("all", "all", "baseline"), "wape"]
    regional_ratios = {
        region: indexed.loc[(region, "all", "model"), "wape"]
        / indexed.loc[(region, "all", "baseline"), "wape"]
        for region in region_ids
    }
    regions_better = sum(ratio < 1 for ratio in regional_ratios.values())
    no_material_harm = max(regional_ratios.values()) <= 1.10
    bootstrap_below_zero = bootstrap.loc[0, "ci_97_5"] < 0
    passed = support and pooled_better and regions_better >= 2 and no_material_harm and bootstrap_below_zero
    row = {
        "test_year": TEST_YEAR,
        "raw_manifest_complete": True,
        "minimum_support_all_regions": bool(support),
        "pooled_model_wape_lower": bool(pooled_better),
        "regions_with_lower_model_wape": int(regions_better),
        "no_region_over_10pct_relatively_worse": bool(no_material_harm),
        "bootstrap_ci_entirely_below_zero": bool(bootstrap_below_zero),
        "external_transfer_gate_passed": bool(passed),
    }
    row.update({f"matched_passes_{region}": int(match_counts[region]) for region in region_ids})
    return pd.DataFrame([row])


def evaluate() -> TransferResult:
    verify_manifest()
    train = load_training_pairs()
    test, matches = load_test_pairs()
    ratios = train.groupby("daynight").agg(modis=("modis_count", "sum"), viirs=("viirs_count", "sum"))
    ratio_map = (ratios["modis"] / ratios["viirs"]).to_dict()
    test["baseline_prediction"] = test["viirs_count"] * test["daynight"].map(ratio_map)
    x_train = make_features(train, GRID_KM, include_region=False)
    x_test = make_features(test, GRID_KM, include_region=False).reindex(columns=x_train.columns, fill_value=0)
    model = HistGradientBoostingRegressor(**PARAMETERS)
    model.fit(x_train, train["modis_count"])
    test["model_prediction"] = model.predict(x_test)
    metrics = metric_table(test)
    bootstrap = date_block_bootstrap(test)
    decision = make_decision(metrics, bootstrap, matches)
    return TransferResult(metrics, bootstrap, decision, matches, test)


def main() -> None:
    result = evaluate()
    output = ROOT / "outputs" / "tables"
    result.metrics.to_csv(output / "day9_independent_transfer_metrics.csv", index=False)
    result.bootstrap.to_csv(output / "day9_independent_transfer_bootstrap.csv", index=False)
    result.decision.to_csv(output / "day9_independent_transfer_decision.csv", index=False)
    result.matches.to_csv(output / "day9_independent_transfer_pass_matches.csv", index=False)
    result.predictions.to_parquet(DATA_PROCESSED / "day9_independent_transfer_scored.parquet", index=False)
    print(result.metrics[result.metrics["daynight"] == "all"].to_string(index=False))
    print(result.bootstrap.to_string(index=False))
    print(result.decision.to_string(index=False))


if __name__ == "__main__":
    main()
