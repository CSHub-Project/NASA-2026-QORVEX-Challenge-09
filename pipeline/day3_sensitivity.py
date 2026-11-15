from __future__ import annotations

import argparse
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
import seaborn as sns

from pipeline.common import DATA_PROCESSED, FIGURES, ROOT, ensure_directories
from pipeline.day3_harmonize import make_contemporaneous_grid_pairs, train_and_score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--grids", type=float, nargs="+", default=[5.0, 10.0, 25.0])
    parser.add_argument("--test-start", type=date.fromisoformat, default=date(2019, 10, 1))
    parser.add_argument("--bootstrap", type=int, default=100)
    args = parser.parse_args()
    ensure_directories()

    observations = pl.read_parquet(DATA_PROCESSED / f"overlap_observations_{args.year}.parquet")
    metric_frames: list[pd.DataFrame] = []
    bootstrap_frames: list[pd.DataFrame] = []
    coverage_rows: list[dict[str, object]] = []
    for grid_km in args.grids:
        pairs, matches = make_contemporaneous_grid_pairs(observations, grid_km)
        result = train_and_score(pairs, grid_km, args.test_start, args.bootstrap)
        overall = result.metrics[
            (result.metrics["region_id"] == "all") & (result.metrics["model"] != "model")
        ].copy()
        overall.insert(0, "grid_km", grid_km)
        metric_frames.append(overall)
        bootstrap = result.bootstrap.copy()
        bootstrap.insert(0, "grid_km", grid_km)
        bootstrap_frames.append(bootstrap)
        coverage_rows.append(
            {
                "grid_km": grid_km,
                "matched_passes": len(matches),
                "paired_cell_passes": len(pairs),
            }
        )
        print(f"grid={grid_km:g}km matched_passes={len(matches)} rows={len(pairs)}", flush=True)

    metrics = pd.concat(metric_frames, ignore_index=True)
    bootstrap = pd.concat(bootstrap_frames, ignore_index=True)
    coverage = pd.DataFrame(coverage_rows)
    tables = ROOT / "outputs" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(tables / f"day3_grid_sensitivity_metrics_{args.year}.csv", index=False)
    bootstrap.to_csv(tables / f"day3_grid_sensitivity_bootstrap_{args.year}.csv", index=False)
    coverage.to_csv(tables / f"day3_grid_sensitivity_coverage_{args.year}.csv", index=False)

    sns.set_theme(style="whitegrid")
    chart = sns.relplot(
        data=metrics,
        x="grid_km",
        y="wape",
        hue="model",
        col="metric",
        kind="line",
        marker="o",
        facet_kws={"sharey": False},
        height=4,
        aspect=1.1,
        palette="colorblind",
    )
    chart.set_axis_labels("Equal-area grid size (km)", "Holdout WAPE")
    chart.fig.suptitle("Grid-size sensitivity using scale-normalized error", y=1.04)
    chart.savefig(FIGURES / "day3_grid_sensitivity_2019.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
