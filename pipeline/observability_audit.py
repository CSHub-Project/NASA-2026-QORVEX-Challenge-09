"""Quantify the positive-detection cells a VIIRS-only map could never locate."""

from __future__ import annotations

import polars as pl

from pipeline.common import DATA_PROCESSED, ROOT
from pipeline.day3_harmonize import make_contemporaneous_grid_pairs


def summarize(pairs: pl.DataFrame) -> pl.DataFrame:
    required = {"region_id", "observation_date", "daynight", "modis_count", "viirs_count"}
    if not required.issubset(pairs.columns):
        raise ValueError(f"Missing pair fields: {sorted(required - set(pairs.columns))}")
    if pairs.filter((pl.col("modis_count") < 0) | (pl.col("viirs_count") < 0)).height:
        raise ValueError("Detection counts must be nonnegative")
    if pairs.filter((pl.col("modis_count") == 0) & (pl.col("viirs_count") == 0)).height:
        raise ValueError("A union cell-pass cannot be empty on both sensors")
    source = pairs.with_columns(
        pl.col("observation_date").dt.year().alias("year"),
        ((pl.col("modis_count") > 0) & (pl.col("viirs_count") == 0)).alias("modis_only"),
        ((pl.col("viirs_count") > 0) & (pl.col("modis_count") == 0)).alias("viirs_only"),
        ((pl.col("modis_count") > 0) & (pl.col("viirs_count") > 0)).alias("shared_positive"),
    )
    return (
        source.group_by("year", "region_id", "daynight")
        .agg(
            pl.len().alias("union_cell_passes"),
            pl.col("modis_only").sum().alias("modis_only_cell_passes"),
            pl.col("viirs_only").sum().alias("viirs_only_cell_passes"),
            pl.col("shared_positive").sum().alias("shared_positive_cell_passes"),
            pl.col("modis_count").sum().alias("modis_detections"),
            pl.col("viirs_count").sum().alias("viirs_detections"),
            pl.when(pl.col("modis_only"))
            .then(pl.col("modis_count"))
            .otherwise(0)
            .sum()
            .alias("modis_detections_without_viirs_cell"),
        )
        .with_columns(
            (
                pl.col("shared_positive_cell_passes")
                / (pl.col("shared_positive_cell_passes") + pl.col("modis_only_cell_passes"))
            ).alias("viirs_positive_cell_recall_of_modis"),
            (
                pl.col("modis_detections_without_viirs_cell") / pl.col("modis_detections")
            ).alias("modis_detection_fraction_without_viirs_cell"),
        )
        .sort("year", "region_id", "daynight")
    )


def build() -> pl.DataFrame:
    historical = pl.read_parquet(DATA_PROCESSED / "contemporaneous_pairs_2017_2020_10km.parquet")
    frames = [historical]
    for year in (2021, 2022, 2023):
        observations = pl.read_parquet(DATA_PROCESSED / f"overlap_observations_{year}.parquet")
        if set(observations["region_id"].unique().to_list()) != {"western_iberia"}:
            raise ValueError(f"Unexpected regions in the {year} source")
        later, _ = make_contemporaneous_grid_pairs(observations, 10.0)
        frames.append(later)
    pairs = pl.concat(frames, how="vertical")
    return summarize(pairs)


def main() -> None:
    output = ROOT / "outputs" / "tables" / "detection_support_audit_2017_2023.csv"
    result = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    result.write_csv(output)
    print(result.filter((pl.col("region_id") == "western_iberia") & (pl.col("year") >= 2020)).to_pandas().to_string(index=False))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
