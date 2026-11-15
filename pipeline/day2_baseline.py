from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
import seaborn as sns
from scipy.stats import spearmanr

from pipeline.common import DATA_PROCESSED, FIGURES, ROOT, ensure_directories


EARTH_RADIUS_M = 6_371_008.8
DEFAULT_GRID_KM = 10.0
DEFAULT_TEST_START = date(2019, 10, 1)
PAIR_KEYS = ["region_id", "observation_date", "daynight", "cell_x", "cell_y"]


def add_equal_area_cells(frame: pl.DataFrame, grid_km: float) -> pl.DataFrame:
    """Assign global Lambert cylindrical equal-area cells.

    x = R * longitude and y = R * sin(latitude) preserve area globally. Integer
    cell indices avoid treating decimal-degree cells as equal area.
    """
    grid_m = grid_km * 1_000.0
    lon_rad = pl.col("longitude") * (np.pi / 180.0)
    lat_rad = pl.col("latitude") * (np.pi / 180.0)
    return frame.with_columns(
        ((EARTH_RADIUS_M * lon_rad) / grid_m).floor().cast(pl.Int32).alias("cell_x"),
        ((EARTH_RADIUS_M * lat_rad.sin()) / grid_m).floor().cast(pl.Int32).alias("cell_y"),
        pl.col("acquired_at_utc").dt.date().alias("observation_date"),
    )


def make_sensor_pairs(frame: pl.DataFrame, grid_km: float = DEFAULT_GRID_KM) -> pl.DataFrame:
    # Aqua is the orbitally closest MODIS platform to S-NPP; Terra is excluded
    # from calibration pairs but remains in the immutable observation dataset.
    calibration = frame.filter(
        (pl.col("sensor_family") == "VIIRS")
        | ((pl.col("sensor_family") == "MODIS") & (pl.col("satellite") == "Aqua"))
    )
    gridded = add_equal_area_cells(calibration, grid_km)
    aggregated = gridded.group_by(PAIR_KEYS + ["sensor_family"]).agg(
        pl.len().alias("detections"),
        pl.col("frp").sum().alias("frp_sum_mw"),
    )

    modis = aggregated.filter(pl.col("sensor_family") == "MODIS").drop("sensor_family").rename(
        {"detections": "modis_count", "frp_sum_mw": "modis_frp_mw"}
    )
    viirs = aggregated.filter(pl.col("sensor_family") == "VIIRS").drop("sensor_family").rename(
        {"detections": "viirs_count", "frp_sum_mw": "viirs_frp_mw"}
    )
    return (
        modis.join(viirs, on=PAIR_KEYS, how="full", coalesce=True)
        .with_columns(
            pl.col("modis_count").fill_null(0).cast(pl.Int32),
            pl.col("viirs_count").fill_null(0).cast(pl.Int32),
            pl.col("modis_frp_mw").fill_null(0.0),
            pl.col("viirs_frp_mw").fill_null(0.0),
        )
        .sort(PAIR_KEYS)
    )


def fit_fixed_ratios(pairs: pl.DataFrame, test_start: date) -> pl.DataFrame:
    train = pairs.filter(pl.col("observation_date") < test_start)
    return (
        train.group_by("region_id", "daynight")
        .agg(
            pl.col("modis_count").sum().alias("train_modis_count"),
            pl.col("viirs_count").sum().alias("train_viirs_count"),
            pl.col("modis_frp_mw").sum().alias("train_modis_frp_mw"),
            pl.col("viirs_frp_mw").sum().alias("train_viirs_frp_mw"),
            pl.len().alias("train_cell_days"),
        )
        .with_columns(
            (pl.col("train_modis_count") / pl.col("train_viirs_count")).alias("count_ratio"),
            (pl.col("train_modis_frp_mw") / pl.col("train_viirs_frp_mw")).alias("frp_ratio"),
        )
        .sort("region_id", "daynight")
    )


def score_holdout(pairs: pl.DataFrame, ratios: pl.DataFrame, test_start: date) -> tuple[pl.DataFrame, pl.DataFrame]:
    scored = (
        pairs.filter(pl.col("observation_date") >= test_start)
        .join(ratios.select("region_id", "daynight", "count_ratio", "frp_ratio"), on=["region_id", "daynight"])
        .with_columns(
            (pl.col("viirs_count") * pl.col("count_ratio")).alias("pred_modis_count"),
            (pl.col("viirs_frp_mw") * pl.col("frp_ratio")).alias("pred_modis_frp_mw"),
        )
    )
    rows: list[dict[str, object]] = []
    pdf = scored.to_pandas()
    groups = [("all", "all", pdf), *[(r, d, g) for (r, d), g in pdf.groupby(["region_id", "daynight"])]]
    for region_id, daynight, group in groups:
        for metric in ("count", "frp_mw"):
            observed = group[f"modis_{metric}"].to_numpy(dtype=float)
            predicted = group[f"pred_modis_{metric}"].to_numpy(dtype=float)
            error = predicted - observed
            correlation = spearmanr(observed, predicted).statistic if len(group) > 1 else np.nan
            rows.append(
                {
                    "region_id": region_id,
                    "daynight": daynight,
                    "metric": metric,
                    "test_cell_days": len(group),
                    "mae": float(np.mean(np.abs(error))),
                    "median_ae": float(np.median(np.abs(error))),
                    "signed_bias": float(np.mean(error)),
                    "spearman": float(correlation) if np.isfinite(correlation) else None,
                }
            )
    return scored, pl.DataFrame(rows)


def make_figures(scored: pl.DataFrame) -> None:
    pdf = scored.to_pandas()
    sns.set_theme(style="whitegrid")

    sample = pdf.sample(min(len(pdf), 30_000), random_state=42)
    chart = sns.relplot(
        data=sample,
        x="modis_count",
        y="pred_modis_count",
        col="region_id",
        hue="daynight",
        kind="scatter",
        alpha=0.35,
        facet_kws={"sharex": False, "sharey": False},
        height=4,
        aspect=1,
    )
    for axis in chart.axes.flat:
        ceiling = max(axis.get_xlim()[1], axis.get_ylim()[1])
        axis.plot([0, ceiling], [0, ceiling], linestyle="--", color="black", linewidth=1)
    chart.set_axis_labels("Observed Aqua MODIS detections", "Predicted MODIS-equivalent detections")
    chart.fig.suptitle("Fixed-ratio baseline — Oct–Dec 2019 temporal holdout", y=1.04)
    chart.savefig(FIGURES / "day2_fixed_ratio_scatter_2019.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)

    monthly = (
        pdf.assign(month=pd.to_datetime(pdf["observation_date"]).dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "region_id"], as_index=False)[
            ["modis_count", "viirs_count", "pred_modis_count"]
        ]
        .sum()
        .melt(
            id_vars=["month", "region_id"],
            var_name="series",
            value_name="detections",
        )
    )
    chart = sns.relplot(
        data=monthly,
        x="month",
        y="detections",
        col="region_id",
        hue="series",
        kind="line",
        marker="o",
        facet_kws={"sharey": False},
        height=4,
        aspect=1.1,
    )
    chart.set_axis_labels("Holdout month (UTC)", "Daily-cell aggregated detections")
    chart.fig.suptitle("Raw VIIRS versus fixed-ratio MODIS-equivalent baseline", y=1.04)
    chart.fig.autofmt_xdate()
    chart.savefig(FIGURES / "day2_holdout_monthly_2019.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--grid-km", type=float, default=DEFAULT_GRID_KM)
    parser.add_argument("--test-start", type=date.fromisoformat, default=DEFAULT_TEST_START)
    args = parser.parse_args()
    ensure_directories()

    observations_path = DATA_PROCESSED / f"overlap_observations_{args.year}.parquet"
    if not observations_path.exists():
        raise SystemExit(f"Missing {observations_path}; run pipeline.analyze_overlap first.")

    observations = pl.read_parquet(observations_path)
    pairs = make_sensor_pairs(observations, args.grid_km)
    ratios = fit_fixed_ratios(pairs, args.test_start)
    scored, metrics = score_holdout(pairs, ratios, args.test_start)

    pairs.write_parquet(DATA_PROCESSED / f"paired_grid_{args.year}_{args.grid_km:g}km.parquet")
    scored.write_parquet(DATA_PROCESSED / f"baseline_scored_{args.year}_{args.grid_km:g}km.parquet")
    tables = ROOT / "outputs" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    ratios.write_csv(tables / f"day2_fixed_ratios_{args.year}.csv")
    metrics.write_csv(tables / f"day2_baseline_metrics_{args.year}.csv")
    make_figures(scored)
    print(ratios)
    print(metrics.filter(pl.col("region_id") == "all"))


if __name__ == "__main__":
    main()
