from __future__ import annotations

import argparse
from datetime import date

import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import polars as pl
import seaborn as sns
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

from pipeline.common import DATA_PROCESSED, FIGURES, ROOT, ensure_directories
from pipeline.day3_harmonize import (
    add_neighborhood_features,
    make_contemporaneous_grid_pairs,
    make_features,
    train_and_score,
)


DEFAULT_YEARS = [2017, 2018, 2019, 2020]
DEFAULT_VALIDATION_START = date(2019, 1, 1)
DEFAULT_TEST_START = date(2020, 1, 1)


def load_years(years: list[int]) -> pl.DataFrame:
    paths = [DATA_PROCESSED / f"overlap_observations_{year}.parquet" for year in years]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing normalized year files: {missing}")
    return pl.concat([pl.read_parquet(path) for path in paths], how="diagonal_relaxed")


def build_calendar_ready(
    pairs: pl.DataFrame,
    scored: pd.DataFrame,
    years: list[int],
    test_start: date,
) -> pd.DataFrame:
    history = (
        pairs.filter(pl.col("observation_date") < test_start)
        .group_by("region_id", "observation_date", "daynight")
        .agg(
            pl.col("modis_count").sum().alias("activity_count"),
            pl.col("pair_id").n_unique().alias("matched_passes"),
        )
        .with_columns(pl.lit("Aqua MODIS observed").alias("series_source"))
        .to_pandas()
    )
    holdout = (
        scored.groupby(["region_id", "observation_date", "daynight"], as_index=False)
        .agg(
            activity_count=("selected_modis_count", "sum"),
            matched_passes=("pair_id", "nunique"),
        )
        .assign(series_source="VIIRS harmonized holdout")
    )
    observed = pd.concat([history, holdout], ignore_index=True)
    observed["observation_date"] = pd.to_datetime(observed["observation_date"])

    regions = sorted(observed["region_id"].unique())
    complete = pd.MultiIndex.from_product(
        [
            regions,
            pd.date_range(f"{min(years)}-01-01", f"{max(years)}-12-31", freq="D"),
            ["D", "N"],
        ],
        names=["region_id", "observation_date", "daynight"],
    ).to_frame(index=False)
    calendar = complete.merge(
        observed,
        on=["region_id", "observation_date", "daynight"],
        how="left",
    )
    calendar["has_matched_coverage"] = calendar["matched_passes"].fillna(0).astype(int) > 0
    calendar["year"] = calendar["observation_date"].dt.year
    calendar["month"] = calendar["observation_date"].dt.month
    calendar["day"] = calendar["observation_date"].dt.day
    calendar["percentile_vs_history"] = np.nan
    calendar["robust_z_vs_history"] = np.nan

    history_mask = calendar["observation_date"].dt.date < test_start
    holdout_mask = calendar["observation_date"].dt.date >= test_start
    group_columns = ["region_id", "daynight", "month"]
    covered_history = calendar[history_mask & calendar["has_matched_coverage"]]

    def score_target(target: pd.Series, reference: pd.Series) -> None:
        values = reference.dropna().to_numpy(float)
        if not len(values) or not target.any():
            return
        target_values = calendar.loc[target, "activity_count"].to_numpy(float)
        calendar.loc[target, "percentile_vs_history"] = [
            100.0 * (np.sum(values <= item) + 0.5) / (len(values) + 1.0)
            for item in target_values
        ]
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad > 0:
            calendar.loc[target, "robust_z_vs_history"] = 0.6745 * (
                target_values - median
            ) / mad

    for keys, group in covered_history.groupby(group_columns):
        group_target = pd.Series(True, index=calendar.index)
        for column, value in zip(group_columns, keys):
            group_target &= calendar[column] == value

        # Score each historical year against the other historical years only.
        # This leave-one-year-out reference keeps the displayed anomaly useful
        # without allowing the target year's own observations into its baseline.
        for historical_year in sorted(group["year"].unique()):
            target = (
                group_target
                & history_mask
                & calendar["has_matched_coverage"]
                & (calendar["year"] == historical_year)
            )
            reference = group.loc[
                group["year"] != historical_year, "activity_count"
            ]
            score_target(target, reference)

        # The held-out year remains scored against every covered historical
        # observation in the matching region, overpass and calendar month.
        score_target(
            group_target & holdout_mask & calendar["has_matched_coverage"],
            group["activity_count"],
        )
    return calendar


def run_spatial_transfer(
    pairs: pl.DataFrame, grid_km: float, test_start: date
) -> pd.DataFrame:
    frame = add_neighborhood_features(pairs).to_pandas()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"]).dt.date
    features = make_features(frame, grid_km, include_region=False)
    parameters = dict(
        loss="poisson",
        learning_rate=0.05,
        max_iter=180,
        max_leaf_nodes=15,
        min_samples_leaf=30,
        l2_regularization=1.0,
        random_state=42,
    )
    rows: list[dict[str, object]] = []
    for heldout_region in sorted(frame["region_id"].unique()):
        train_mask = (frame["observation_date"] < test_start) & (
            frame["region_id"] != heldout_region
        )
        test_mask = (frame["observation_date"] >= test_start) & (
            frame["region_id"] == heldout_region
        )
        train = frame.loc[train_mask]
        test = frame.loc[test_mask].copy()
        ratios = train.groupby("daynight").agg(
            modis=("modis_count", "sum"),
            viirs=("viirs_count", "sum"),
        )
        ratio_map = (ratios["modis"] / ratios["viirs"]).to_dict()
        test["baseline_prediction"] = test["viirs_count"] * test["daynight"].map(ratio_map)

        model = HistGradientBoostingRegressor(**parameters)
        model.fit(features.loc[train_mask], frame.loc[train_mask, "modis_count"])
        test["model_prediction"] = model.predict(features.loc[test_mask])
        observed = test["modis_count"].to_numpy(float)
        for method in ("baseline", "model"):
            predicted = test[f"{method}_prediction"].to_numpy(float)
            error = predicted - observed
            rho = spearmanr(observed, predicted).statistic
            rows.append(
                {
                    "heldout_region": heldout_region,
                    "method": method,
                    "test_rows": len(test),
                    "mae": np.mean(np.abs(error)),
                    "wape": np.sum(np.abs(error)) / max(np.sum(observed), 1e-12),
                    "signed_bias": np.mean(error),
                    "spearman": rho if np.isfinite(rho) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def make_figures(
    metrics: pd.DataFrame,
    scored: pd.DataFrame,
    calendar: pd.DataFrame,
    spatial_transfer: pd.DataFrame,
) -> None:
    sns.set_theme(style="whitegrid")
    overall = metrics[
        (metrics["region_id"] == "all") & (metrics["model"].isin(["baseline", "selected"]))
    ]
    chart = sns.catplot(
        data=overall,
        x="model",
        y="wape",
        hue="model",
        col="metric",
        kind="bar",
        sharey=False,
        legend=False,
        palette="colorblind",
        height=4,
        aspect=1,
    )
    chart.set_axis_labels("Method", "2020 year-holdout WAPE")
    chart.fig.suptitle("Four-year validation: fixed ratio versus guarded model", y=1.04)
    chart.savefig(FIGURES / "day4_year_holdout_wape_2020.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)

    monthly = scored.copy()
    monthly["month"] = (
        pd.to_datetime(monthly["observation_date"]).dt.to_period("M").dt.to_timestamp()
    )
    monthly = (
        monthly.groupby(["region_id", "month"], as_index=False)[
            ["modis_count", "baseline_modis_count", "selected_modis_count"]
        ]
        .sum()
        .melt(
            id_vars=["region_id", "month"],
            var_name="series",
            value_name="detections",
        )
    )
    chart = sns.relplot(
        data=monthly,
        x="month",
        y="detections",
        hue="series",
        col="region_id",
        kind="line",
        marker="o",
        facet_kws={"sharey": False},
        palette="colorblind",
        height=4,
        aspect=1.1,
    )
    chart.set_axis_labels("2020 month", "Matched-pass detections")
    chart.fig.suptitle("Full-year holdout: observed MODIS and VIIRS-based estimates", y=1.04)
    chart.fig.autofmt_xdate()
    chart.savefig(FIGURES / "day4_monthly_holdout_2020.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)

    holdout = calendar[(calendar["year"] == 2020) & calendar["has_matched_coverage"]].copy()
    daily = (
        holdout.groupby(["region_id", "observation_date"], as_index=False)[
            "percentile_vs_history"
        ]
        .max()
        .assign(
            month=lambda frame: frame["observation_date"].dt.month,
            day=lambda frame: frame["observation_date"].dt.day,
        )
    )
    regions = sorted(daily["region_id"].unique())
    figure, axes = plt.subplots(len(regions), 1, figsize=(13, 7), constrained_layout=True)
    calendar_cmap = colormaps["viridis"].copy()
    calendar_cmap.set_bad("#e5e7eb")
    for axis, region in zip(np.atleast_1d(axes), regions):
        matrix = (
            daily[daily["region_id"] == region]
            .pivot(index="month", columns="day", values="percentile_vs_history")
            .reindex(index=range(1, 13), columns=range(1, 32))
        )
        sns.heatmap(
            matrix,
            ax=axis,
            cmap=calendar_cmap,
            vmin=0,
            vmax=100,
            cbar=axis is axes[-1],
            cbar_kws={"label": "Historical percentile"} if axis is axes[-1] else None,
        )
        axis.set_title(region)
        axis.set_xlabel("Day of month")
        axis.set_ylabel("Month")
    figure.suptitle("2020 harmonized activity calendar — maximum day/night percentile")
    figure.legend(
        handles=[Patch(facecolor="#e5e7eb", label="No matched coverage")],
        loc="lower center",
        frameon=False,
    )
    figure.savefig(FIGURES / "day4_anomaly_calendar_2020.png", dpi=180, bbox_inches="tight")
    plt.close(figure)

    axis = sns.barplot(
        data=spatial_transfer,
        x="heldout_region",
        y="wape",
        hue="method",
        palette="colorblind",
    )
    axis.set_title("Strict spatial transfer: train on the other study regions")
    axis.set_xlabel("Unseen 2020 region")
    axis.set_ylabel("Count WAPE")
    axis.figure.savefig(FIGURES / "day4_spatial_transfer_2020.png", dpi=180, bbox_inches="tight")
    plt.close(axis.figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, nargs="+", default=DEFAULT_YEARS)
    parser.add_argument("--grid-km", type=float, default=10.0)
    parser.add_argument(
        "--validation-start", type=date.fromisoformat, default=DEFAULT_VALIDATION_START
    )
    parser.add_argument("--test-start", type=date.fromisoformat, default=DEFAULT_TEST_START)
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args()
    ensure_directories()

    observations = load_years(args.years)
    pairs, matches = make_contemporaneous_grid_pairs(observations, args.grid_km)
    result = train_and_score(
        pairs,
        args.grid_km,
        args.test_start,
        args.bootstrap,
        args.validation_start,
    )
    calendar = build_calendar_ready(pairs, result.scored, args.years, args.test_start)
    spatial_transfer = run_spatial_transfer(pairs, args.grid_km, args.test_start)

    year_label = f"{min(args.years)}_{max(args.years)}"
    pairs.write_parquet(
        DATA_PROCESSED / f"contemporaneous_pairs_{year_label}_{args.grid_km:g}km.parquet"
    )
    result.scored.to_parquet(
        DATA_PROCESSED / f"year_holdout_scored_{year_label}_{args.grid_km:g}km.parquet",
        index=False,
    )
    tables = ROOT / "outputs" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    source_inventory = (
        observations.group_by(
            pl.col("acquired_at_utc").dt.year().alias("year"),
            "region_id",
            "source",
        )
        .agg(pl.len().alias("observations"))
        .sort("year", "region_id", "source")
    )
    source_inventory.write_csv(tables / "day4_source_inventory.csv")
    result.metrics.to_csv(tables / "day4_year_holdout_metrics.csv", index=False)
    result.bootstrap.to_csv(tables / "day4_year_holdout_bootstrap.csv", index=False)
    result.selection.to_csv(tables / "day4_validation_selection.csv", index=False)
    matches.to_csv(tables / "day4_pass_matches.csv", index=False)
    calendar.to_csv(tables / "day4_calendar_ready_2017_2020.csv", index=False)
    spatial_transfer.to_csv(tables / "day4_spatial_transfer_metrics.csv", index=False)
    make_figures(result.metrics, result.scored, calendar, spatial_transfer)

    print(f"observations={observations.height} matched_passes={len(matches)} pairs={pairs.height}")
    print(result.metrics[result.metrics["region_id"] == "all"].to_string(index=False))
    print(result.bootstrap.to_string(index=False))
    print(spatial_transfer.to_string(index=False))
    print(
        "calendar_coverage=",
        calendar.groupby("year")["has_matched_coverage"].mean().round(3).to_dict(),
    )


if __name__ == "__main__":
    main()
