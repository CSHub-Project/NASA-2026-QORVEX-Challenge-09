from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
import seaborn as sns
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

from pipeline.common import DATA_PROCESSED, FIGURES, ROOT, ensure_directories
from pipeline.day2_baseline import EARTH_RADIUS_M, add_equal_area_cells


DEFAULT_GRID_KM = 10.0
DEFAULT_VALIDATION_START = date(2019, 7, 1)
DEFAULT_TEST_START = date(2019, 10, 1)
PASS_GAP_MINUTES = 30
MAX_MATCH_MINUTES = 60
BOOTSTRAP_REPLICATES = 500
PAIR_KEYS = ["pair_id", "region_id", "observation_date", "daynight", "cell_x", "cell_y"]


@dataclass(frozen=True)
class ModelResult:
    scored: pd.DataFrame
    metrics: pd.DataFrame
    bootstrap: pd.DataFrame
    selection: pd.DataFrame


def build_pass_catalog(
    observations: pl.DataFrame, gap_minutes: int = PASS_GAP_MINUTES
) -> tuple[pl.DataFrame, pd.DataFrame]:
    selected = observations.filter(
        (pl.col("sensor_family") == "VIIRS")
        | ((pl.col("sensor_family") == "MODIS") & (pl.col("satellite") == "Aqua"))
    )
    timestamps = (
        selected.select("sensor_family", "region_id", "daynight", "acquired_at_utc")
        .unique()
        .sort("sensor_family", "region_id", "daynight", "acquired_at_utc")
        .to_pandas()
    )
    timestamps["observation_date"] = timestamps["acquired_at_utc"].dt.date

    mapping_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    pass_number = 0
    group_columns = ["sensor_family", "region_id", "daynight", "observation_date"]
    for keys, group in timestamps.groupby(group_columns, sort=True):
        times = sorted(group["acquired_at_utc"].tolist())
        clusters: list[list[pd.Timestamp]] = []
        for timestamp in times:
            if not clusters or (timestamp - clusters[-1][-1]).total_seconds() > gap_minutes * 60:
                clusters.append([timestamp])
            else:
                clusters[-1].append(timestamp)
        for cluster in clusters:
            pass_number += 1
            pass_id = f"pass-{pass_number:07d}"
            middle = cluster[len(cluster) // 2]
            sensor, region, daynight, observation_date = keys
            summary_rows.append(
                {
                    "sensor_family": sensor,
                    "region_id": region,
                    "daynight": daynight,
                    "observation_date": observation_date,
                    "sensor_pass_id": pass_id,
                    "pass_time_utc": middle,
                    "timestamp_count": len(cluster),
                }
            )
            for timestamp in cluster:
                mapping_rows.append(
                    {
                        "sensor_family": sensor,
                        "region_id": region,
                        "daynight": daynight,
                        "acquired_at_utc": timestamp,
                        "sensor_pass_id": pass_id,
                    }
                )
    mapping = pl.from_pandas(pd.DataFrame(mapping_rows)).with_columns(
        pl.col("acquired_at_utc").dt.cast_time_unit("us")
    )
    return mapping, pd.DataFrame(summary_rows)


def match_passes(
    pass_summary: pd.DataFrame, max_match_minutes: int = MAX_MATCH_MINUTES
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    pair_number = 0
    keys = ["region_id", "observation_date", "daynight"]
    for group_keys, group in pass_summary.groupby(keys, sort=True):
        modis = group[group["sensor_family"] == "MODIS"]
        viirs = group[group["sensor_family"] == "VIIRS"]
        candidates: list[tuple[float, pd.Series, pd.Series]] = []
        for _, modis_pass in modis.iterrows():
            for _, viirs_pass in viirs.iterrows():
                delta = abs(
                    (modis_pass["pass_time_utc"] - viirs_pass["pass_time_utc"]).total_seconds()
                ) / 60.0
                if delta <= max_match_minutes:
                    candidates.append((delta, modis_pass, viirs_pass))
        used_modis: set[str] = set()
        used_viirs: set[str] = set()
        for delta, modis_pass, viirs_pass in sorted(candidates, key=lambda item: item[0]):
            modis_id = str(modis_pass["sensor_pass_id"])
            viirs_id = str(viirs_pass["sensor_pass_id"])
            if modis_id in used_modis or viirs_id in used_viirs:
                continue
            pair_number += 1
            used_modis.add(modis_id)
            used_viirs.add(viirs_id)
            region_id, observation_date, daynight = group_keys
            rows.append(
                {
                    "pair_id": f"pair-{pair_number:07d}",
                    "region_id": region_id,
                    "observation_date": observation_date,
                    "daynight": daynight,
                    "modis_pass_id": modis_id,
                    "viirs_pass_id": viirs_id,
                    "time_difference_minutes": delta,
                }
            )
    return pd.DataFrame(rows)


def make_contemporaneous_grid_pairs(
    observations: pl.DataFrame,
    grid_km: float,
    gap_minutes: int = PASS_GAP_MINUTES,
    max_match_minutes: int = MAX_MATCH_MINUTES,
) -> tuple[pl.DataFrame, pd.DataFrame]:
    pass_mapping, pass_summary = build_pass_catalog(observations, gap_minutes)
    matches = match_passes(pass_summary, max_match_minutes)
    if matches.empty:
        raise ValueError("No contemporaneous Aqua MODIS / VIIRS passes were matched")

    pass_to_pair = pd.concat(
        [
            matches[["pair_id", "modis_pass_id"]].rename(
                columns={"modis_pass_id": "sensor_pass_id"}
            ),
            matches[["pair_id", "viirs_pass_id"]].rename(
                columns={"viirs_pass_id": "sensor_pass_id"}
            ),
        ],
        ignore_index=True,
    )
    match_meta = pl.from_pandas(matches[["pair_id", "time_difference_minutes"]])
    selected = observations.filter(
        (pl.col("sensor_family") == "VIIRS")
        | ((pl.col("sensor_family") == "MODIS") & (pl.col("satellite") == "Aqua"))
    )
    matched = (
        selected.join(
            pass_mapping,
            on=["sensor_family", "region_id", "daynight", "acquired_at_utc"],
            how="inner",
        )
        .join(pl.from_pandas(pass_to_pair), on="sensor_pass_id", how="inner")
        .pipe(add_equal_area_cells, grid_km)
    )
    aggregated = matched.group_by(PAIR_KEYS + ["sensor_family"]).agg(
        pl.len().alias("detections"),
        pl.col("frp").sum().alias("frp_sum_mw"),
        pl.col("scan").mean().alias("scan_mean_km"),
        pl.col("track").mean().alias("track_mean_km"),
    )
    modis = (
        aggregated.filter(pl.col("sensor_family") == "MODIS")
        .drop("sensor_family", "scan_mean_km", "track_mean_km")
        .rename({"detections": "modis_count", "frp_sum_mw": "modis_frp_mw"})
    )
    viirs = aggregated.filter(pl.col("sensor_family") == "VIIRS").drop("sensor_family").rename(
        {
            "detections": "viirs_count",
            "frp_sum_mw": "viirs_frp_mw",
            "scan_mean_km": "viirs_scan_mean_km",
            "track_mean_km": "viirs_track_mean_km",
        }
    )
    pairs = (
        modis.join(viirs, on=PAIR_KEYS, how="full", coalesce=True)
        .with_columns(
            pl.col("modis_count").fill_null(0).cast(pl.Int32),
            pl.col("viirs_count").fill_null(0).cast(pl.Int32),
            pl.col("modis_frp_mw").fill_null(0.0),
            pl.col("viirs_frp_mw").fill_null(0.0),
            pl.col("viirs_scan_mean_km").fill_null(0.0),
            pl.col("viirs_track_mean_km").fill_null(0.0),
        )
        .join(match_meta, on="pair_id", how="left")
        .sort(PAIR_KEYS)
    )
    return pairs, matches


def add_neighborhood_features(pairs: pl.DataFrame, radius: int = 1) -> pl.DataFrame:
    expanded: list[pl.DataFrame] = []
    source = pairs.select(*PAIR_KEYS, "viirs_count", "viirs_frp_mw")
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            expanded.append(
                source.with_columns(
                    (pl.col("cell_x") + dx).alias("cell_x"),
                    (pl.col("cell_y") + dy).alias("cell_y"),
                )
            )
    neighborhood = pl.concat(expanded).group_by(PAIR_KEYS).agg(
        pl.col("viirs_count").sum().alias("viirs_count_3x3"),
        pl.col("viirs_frp_mw").sum().alias("viirs_frp_3x3_mw"),
    )
    return pairs.join(neighborhood, on=PAIR_KEYS, how="left")


def fit_baseline(frame: pd.DataFrame, test_start: date) -> pd.DataFrame:
    train = frame[frame["observation_date"] < test_start]
    ratios = (
        train.groupby(["region_id", "daynight"], as_index=False)
        .agg(
            train_modis_count=("modis_count", "sum"),
            train_viirs_count=("viirs_count", "sum"),
            train_modis_frp_mw=("modis_frp_mw", "sum"),
            train_viirs_frp_mw=("viirs_frp_mw", "sum"),
        )
    )
    ratios["count_ratio"] = ratios["train_modis_count"] / ratios["train_viirs_count"]
    ratios["frp_ratio"] = ratios["train_modis_frp_mw"] / ratios["train_viirs_frp_mw"]
    return ratios


def make_features(
    frame: pd.DataFrame, grid_km: float, include_region: bool = True
) -> pd.DataFrame:
    month = pd.to_datetime(frame["observation_date"]).dt.month
    y_center_m = (frame["cell_y"].astype(float) + 0.5) * grid_km * 1_000.0
    latitude = np.degrees(np.arcsin(np.clip(y_center_m / EARTH_RADIUS_M, -1, 1)))
    numeric = pd.DataFrame(
        {
            "viirs_count": frame["viirs_count"],
            "log_viirs_count": np.log1p(frame["viirs_count"]),
            "log_viirs_frp": np.log1p(frame["viirs_frp_mw"]),
            "viirs_count_3x3": frame["viirs_count_3x3"],
            "log_viirs_count_3x3": np.log1p(frame["viirs_count_3x3"]),
            "log_viirs_frp_3x3": np.log1p(frame["viirs_frp_3x3_mw"]),
            "pass_time_difference": frame["time_difference_minutes"],
            "viirs_scan_mean_km": frame["viirs_scan_mean_km"],
            "viirs_track_mean_km": frame["viirs_track_mean_km"],
            "latitude": latitude,
            "month_sin": np.sin(2 * np.pi * month / 12),
            "month_cos": np.cos(2 * np.pi * month / 12),
        },
        index=frame.index,
    )
    category_columns = ["daynight"]
    prefixes = ["daynight"]
    if include_region:
        category_columns.insert(0, "region_id")
        prefixes.insert(0, "region")
    categories = pd.get_dummies(
        frame[category_columns], prefix=prefixes, dtype=float
    )
    return pd.concat([numeric, categories], axis=1)


def calculate_metrics(scored: pd.DataFrame, model_name: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groups = [
        ("all", "all", scored),
        *[(r, d, g) for (r, d), g in scored.groupby(["region_id", "daynight"])],
    ]
    for region_id, daynight, group in groups:
        for metric in ("count", "frp_mw"):
            observed = group[f"modis_{metric}"].to_numpy(float)
            predicted = group[f"{model_name}_modis_{metric}"].to_numpy(float)
            error = predicted - observed
            rho = spearmanr(observed, predicted).statistic if len(group) > 1 else np.nan
            rows.append(
                {
                    "model": model_name,
                    "region_id": region_id,
                    "daynight": daynight,
                    "metric": metric,
                    "test_cell_passes": len(group),
                    "mean_observed": np.mean(observed),
                    "mae": np.mean(np.abs(error)),
                    "wape": np.sum(np.abs(error)) / max(np.sum(observed), 1e-12),
                    "median_ae": np.median(np.abs(error)),
                    "signed_bias": np.mean(error),
                    "spearman": rho if np.isfinite(rho) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def block_bootstrap(
    scored: pd.DataFrame,
    replicates: int = BOOTSTRAP_REPLICATES,
    candidate_name: str = "selected",
) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = np.array(sorted(scored["observation_date"].unique()))
    rows: list[dict[str, object]] = []
    for metric in ("count", "frp_mw"):
        observed_column = f"modis_{metric}"
        baseline_column = f"baseline_modis_{metric}"
        model_column = f"{candidate_name}_modis_{metric}"
        daily: dict[object, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        for observation_date, group in scored.groupby("observation_date"):
            daily[observation_date] = (
                group[observed_column].to_numpy(float),
                group[baseline_column].to_numpy(float),
                group[model_column].to_numpy(float),
            )
        deltas: list[float] = []
        for _ in range(replicates):
            sampled_dates = rng.choice(dates, size=len(dates), replace=True)
            observed = np.concatenate([daily[d][0] for d in sampled_dates])
            baseline = np.concatenate([daily[d][1] for d in sampled_dates])
            model = np.concatenate([daily[d][2] for d in sampled_dates])
            deltas.append(np.mean(np.abs(model - observed)) - np.mean(np.abs(baseline - observed)))
        low, high = np.quantile(deltas, [0.025, 0.975])
        rows.append(
            {
                "metric": metric,
                "comparison": f"{candidate_name}_mae_minus_baseline_mae",
                "replicates": replicates,
                "estimate": float(np.mean(deltas)),
                "ci_2_5": float(low),
                "ci_97_5": float(high),
                "probability_model_better": float(np.mean(np.array(deltas) < 0)),
            }
        )
    return pd.DataFrame(rows)


def train_and_score(
    pairs: pl.DataFrame,
    grid_km: float,
    test_start: date,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
    validation_start: date = DEFAULT_VALIDATION_START,
) -> ModelResult:
    base_frame = add_neighborhood_features(pairs).to_pandas()
    base_frame["observation_date"] = pd.to_datetime(base_frame["observation_date"]).dt.date
    ratios = fit_baseline(base_frame, test_start)
    frame = base_frame.merge(
        ratios[["region_id", "daynight", "count_ratio", "frp_ratio"]],
        on=["region_id", "daynight"],
    )
    frame["baseline_modis_count"] = frame["viirs_count"] * frame["count_ratio"]
    frame["baseline_modis_frp_mw"] = frame["viirs_frp_mw"] * frame["frp_ratio"]

    features = make_features(frame, grid_km)
    fit_mask = frame["observation_date"] < validation_start
    validation_mask = (frame["observation_date"] >= validation_start) & (
        frame["observation_date"] < test_start
    )
    train_mask = frame["observation_date"] < test_start
    test_mask = ~train_mask
    model_parameters = dict(
        loss="poisson",
        learning_rate=0.05,
        max_iter=180,
        max_leaf_nodes=15,
        min_samples_leaf=30,
        l2_regularization=1.0,
        random_state=42,
    )
    validation_ratios = fit_baseline(base_frame, validation_start)
    validation = base_frame.loc[validation_mask].merge(
        validation_ratios[["region_id", "daynight", "count_ratio", "frp_ratio"]],
        on=["region_id", "daynight"],
        how="left",
    )
    validation_selection: list[dict[str, object]] = []
    for metric in ("count", "frp_mw"):
        validation[f"baseline_modis_{metric}"] = (
            validation[f"viirs_{metric}"]
            * validation["count_ratio" if metric == "count" else "frp_ratio"]
        )
        candidate = HistGradientBoostingRegressor(**model_parameters)
        candidate.fit(features.loc[fit_mask], frame.loc[fit_mask, f"modis_{metric}"])
        validation[f"model_modis_{metric}"] = candidate.predict(features.loc[validation_mask])
        for (region_id, daynight), group in validation.groupby(["region_id", "daynight"]):
            observed = group[f"modis_{metric}"].to_numpy(float)
            baseline_mae = np.mean(np.abs(group[f"baseline_modis_{metric}"] - observed))
            model_mae = np.mean(np.abs(group[f"model_modis_{metric}"] - observed))
            selected_method = (
                "model" if len(group) >= 100 and model_mae < baseline_mae else "baseline"
            )
            validation_selection.append(
                {
                    "region_id": region_id,
                    "daynight": daynight,
                    "metric": metric,
                    "validation_rows": len(group),
                    "validation_baseline_mae": baseline_mae,
                    "validation_model_mae": model_mae,
                    "selected_method": selected_method,
                }
            )

        model = HistGradientBoostingRegressor(**model_parameters)
        model.fit(features.loc[train_mask], frame.loc[train_mask, f"modis_{metric}"])
        frame.loc[test_mask, f"model_modis_{metric}"] = model.predict(features.loc[test_mask])

    scored = frame.loc[test_mask].copy()
    selection = pd.DataFrame(validation_selection)
    for metric in ("count", "frp_mw"):
        choices = selection[selection["metric"] == metric].set_index(["region_id", "daynight"])[
            "selected_method"
        ]
        choice_map = choices.to_dict()
        use_model = np.array(
            [
                choice_map[(region, daynight)] == "model"
                for region, daynight in zip(scored["region_id"], scored["daynight"])
            ],
            dtype=bool,
        )
        scored[f"selected_modis_{metric}"] = np.where(
            use_model,
            scored[f"model_modis_{metric}"],
            scored[f"baseline_modis_{metric}"],
        )
    metrics = pd.concat(
        [
            calculate_metrics(scored, "baseline"),
            calculate_metrics(scored, "model"),
            calculate_metrics(scored, "selected"),
        ],
        ignore_index=True,
    )
    bootstrap = block_bootstrap(scored, bootstrap_replicates, "selected")
    return ModelResult(scored=scored, metrics=metrics, bootstrap=bootstrap, selection=selection)


def make_figures(result: ModelResult) -> None:
    sns.set_theme(style="whitegrid")
    overall = result.metrics[result.metrics["region_id"] == "all"].copy()
    chart = sns.catplot(
        data=overall,
        x="model",
        y="mae",
        col="metric",
        kind="bar",
        sharey=False,
        height=4,
        aspect=1,
        hue="model",
        legend=False,
        palette="colorblind",
    )
    chart.set_axis_labels("Method", "Holdout mean absolute error")
    chart.fig.suptitle("Contemporaneous-pass holdout: baseline versus harmonization model", y=1.05)
    chart.savefig(FIGURES / "day3_model_vs_baseline_mae_2019.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)

    sample = result.scored.sample(min(30_000, len(result.scored)), random_state=42)
    long = sample.melt(
        id_vars=["modis_count", "region_id", "daynight"],
        value_vars=["baseline_modis_count", "selected_modis_count"],
        var_name="method",
        value_name="predicted",
    )
    long["method"] = long["method"].map(
        {
            "baseline_modis_count": "Fixed ratio",
            "selected_modis_count": "Guarded model",
        }
    )
    long["region_id"] = long["region_id"].map(
        {
            "amazon_arc": "Amazon",
            "california_north": "N. California",
            "hyrcanian": "Hyrcanian",
        }
    )
    chart = sns.relplot(
        data=long,
        x="modis_count",
        y="predicted",
        col="region_id",
        row="method",
        hue="daynight",
        kind="scatter",
        alpha=0.3,
        facet_kws={"sharex": False, "sharey": False},
        height=3.2,
        aspect=1.1,
    )
    for axis in chart.axes.flat:
        ceiling = max(axis.get_xlim()[1], axis.get_ylim()[1])
        axis.plot([0, ceiling], [0, ceiling], "--", color="black", linewidth=1)
    chart.set_titles(row_template="{row_name}", col_template="{col_name}")
    chart.set_axis_labels("Observed Aqua MODIS count", "Predicted MODIS-equivalent count")
    chart.fig.suptitle("Fixed ratio and nonlinear neighborhood model — Oct–Dec 2019", y=1.025)
    chart.savefig(FIGURES / "day3_prediction_scatter_2019.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--grid-km", type=float, default=DEFAULT_GRID_KM)
    parser.add_argument(
        "--validation-start", type=date.fromisoformat, default=DEFAULT_VALIDATION_START
    )
    parser.add_argument("--test-start", type=date.fromisoformat, default=DEFAULT_TEST_START)
    parser.add_argument("--bootstrap", type=int, default=BOOTSTRAP_REPLICATES)
    args = parser.parse_args()
    ensure_directories()

    source = DATA_PROCESSED / f"overlap_observations_{args.year}.parquet"
    if not source.exists():
        raise SystemExit(f"Missing {source}; run pipeline.analyze_overlap first")
    observations = pl.read_parquet(source)
    pairs, matches = make_contemporaneous_grid_pairs(observations, args.grid_km)
    result = train_and_score(
        pairs,
        args.grid_km,
        args.test_start,
        args.bootstrap,
        args.validation_start,
    )

    pairs.write_parquet(
        DATA_PROCESSED / f"contemporaneous_pairs_{args.year}_{args.grid_km:g}km.parquet"
    )
    result.scored.to_parquet(
        DATA_PROCESSED / f"harmonized_scored_{args.year}_{args.grid_km:g}km.parquet",
        index=False,
    )
    tables = ROOT / "outputs" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    matches.to_csv(tables / f"day3_pass_matches_{args.year}.csv", index=False)
    result.metrics.to_csv(tables / f"day3_model_metrics_{args.year}.csv", index=False)
    result.bootstrap.to_csv(tables / f"day3_bootstrap_{args.year}.csv", index=False)
    result.selection.to_csv(tables / f"day3_validation_selection_{args.year}.csv", index=False)
    make_figures(result)

    print(f"matched_passes={len(matches)} paired_cell_passes={pairs.height}")
    print(result.metrics[result.metrics["region_id"] == "all"].to_string(index=False))
    print(result.bootstrap.to_string(index=False))


if __name__ == "__main__":
    main()
