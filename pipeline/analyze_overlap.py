from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
import seaborn as sns

from pipeline.common import DATA_PROCESSED, DATA_RAW, FIGURES, ensure_directories, load_regions
from pipeline.fetch_firms import iter_chunks


def expected_partition_names(year: int) -> set[str]:
    return {f"{start.isoformat()}_{days}d.csv" for start, days in iter_chunks(year)}


def read_source(files: list[Path], source: str, region_id: str) -> pl.DataFrame:
    if not files:
        raise FileNotFoundError(f"No raw files found for {region_id}/{source}")

    frames: list[pl.DataFrame] = []
    for path in files:
        try:
            frame = pl.read_csv(path, infer_schema_length=10_000, ignore_errors=True)
        except pl.exceptions.NoDataError:
            continue
        if frame.height:
            frames.append(frame)
    if not frames:
        return pl.DataFrame()

    frame = pl.concat(frames, how="diagonal_relaxed")
    columns = {column.lower(): column for column in frame.columns}
    frame = frame.rename({original: lower for lower, original in columns.items()})

    required = {"latitude", "longitude", "acq_date", "acq_time", "frp", "daynight"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{source} is missing required columns: {sorted(missing)}")

    sensor_family = "MODIS" if source.startswith("MODIS") else "VIIRS"
    return (
        frame.with_columns(
            pl.col("acq_time").cast(pl.String).str.zfill(4).alias("acq_time_hhmm"),
            pl.lit(source).alias("source"),
            pl.lit(sensor_family).alias("sensor_family"),
            pl.lit(region_id).alias("region_id"),
            pl.col("daynight").cast(pl.String).str.to_uppercase(),
            pl.col("frp").cast(pl.Float64, strict=False),
        )
        .with_columns(
            (
                pl.col("acq_date").cast(pl.String)
                + pl.lit(" ")
                + pl.col("acq_time_hhmm").str.slice(0, 2)
                + pl.lit(":")
                + pl.col("acq_time_hhmm").str.slice(2, 2)
            )
            .str.to_datetime("%Y-%m-%d %H:%M", strict=False, time_zone="UTC")
            .alias("acquired_at_utc")
        )
        .with_columns(pl.col("acquired_at_utc").dt.truncate("1mo").alias("month"))
    )


def aggregate_monthly(frame: pl.DataFrame) -> pl.DataFrame:
    return (
        frame.group_by("region_id", "month", "sensor_family", "daynight")
        .agg(
            pl.len().alias("raw_count"),
            pl.col("frp").sum().alias("frp_sum_mw"),
            pl.col("frp").median().alias("frp_median_mw"),
        )
        .sort("region_id", "month", "sensor_family", "daynight")
    )


def plot_metric(
    monthly: pd.DataFrame,
    region_id: str,
    metric: str,
    ylabel: str,
    year: int,
) -> None:
    data = monthly[monthly["region_id"] == region_id].copy()
    sns.set_theme(style="whitegrid")
    chart = sns.relplot(
        data=data,
        x="month",
        y=metric,
        hue="sensor_family",
        style="daynight",
        kind="line",
        markers=True,
        height=5,
        aspect=1.8,
    )
    chart.set_axis_labels("Month (UTC)", ylabel)
    chart.fig.suptitle(f"{year} raw overlap — {region_id}", y=1.03)
    chart.fig.autofmt_xdate()
    chart.savefig(FIGURES / f"{region_id}_{metric}_{year}.png", dpi=180, bbox_inches="tight")
    plt.close(chart.fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--region", action="append", help="Region id; repeat to select several")
    parser.add_argument("--regions-file", type=Path, help="Alternative versioned region JSON")
    parser.add_argument("--dataset-label", help="Suffix for processed outputs")
    args = parser.parse_args()
    ensure_directories()

    regions = load_regions(args.regions_file)
    if args.region:
        requested = set(args.region)
        regions = [region for region in regions if region.id in requested]
        unknown = requested - {region.id for region in regions}
        if unknown:
            raise SystemExit(f"Unknown region ids: {sorted(unknown)}")
    all_frames: list[pl.DataFrame] = []
    expected_files = expected_partition_names(args.year)
    for region in regions:
        for source in ("MODIS_SP", "VIIRS_SNPP_SP"):
            files = sorted((DATA_RAW / str(args.year) / region.id / source).glob("*.csv"))
            actual_files = {path.name for path in files}
            if actual_files != expected_files:
                missing = len(expected_files - actual_files)
                extra = len(actual_files - expected_files)
                raise FileNotFoundError(
                    f"Incomplete {args.year}/{region.id}/{source}: "
                    f"missing={missing}, unexpected={extra}. Resume pipeline.fetch_firms."
                )
            frame = read_source(files, source, region.id)
            if frame.height:
                all_frames.append(frame)

    if not all_frames:
        raise SystemExit("No observations found. Run pipeline.fetch_firms first.")

    observations = pl.concat(all_frames, how="diagonal_relaxed")
    monthly = aggregate_monthly(observations)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.dataset_label}" if args.dataset_label else ""
    observations.write_parquet(
        DATA_PROCESSED / f"overlap_observations_{args.year}{suffix}.parquet"
    )
    monthly.write_parquet(DATA_PROCESSED / f"monthly_raw_{args.year}{suffix}.parquet")

    monthly_pd = monthly.to_pandas()
    for region in regions:
        plot_metric(monthly_pd, region.id, "raw_count", "Raw hotspot detections", args.year)
        plot_metric(monthly_pd, region.id, "frp_sum_mw", "Monthly FRP sum (MW)", args.year)

    print(f"year={args.year} observations={observations.height} monthly_rows={monthly.height}")


if __name__ == "__main__":
    main()

