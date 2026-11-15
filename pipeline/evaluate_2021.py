"""Predeclared, independent Western Iberia year test of the frozen 2019 selection."""

from __future__ import annotations

from datetime import date

import pandas as pd
import polars as pl

from pipeline.common import DATA_PROCESSED, ROOT
from pipeline.day3_harmonize import make_contemporaneous_grid_pairs, train_and_score


TRAIN_YEARS = (2017, 2018, 2019)
TEST_YEAR = 2021
REGION_ID = "western_iberia"
GRID_KM = 10.0
VALIDATION_START = date(2019, 1, 1)
TEST_START = date(2021, 1, 1)
BOOTSTRAP_REPLICATES = 500


def load_observations() -> pl.DataFrame:
    frames = []
    for year in (*TRAIN_YEARS, TEST_YEAR):
        path = DATA_PROCESSED / f"overlap_observations_{year}.parquet"
        if not path.is_file():
            raise FileNotFoundError(path)
        frame = pl.read_parquet(path)
        if year == TEST_YEAR:
            frame = frame.filter(pl.col("region_id") == REGION_ID)
            if frame.is_empty():
                raise ValueError(f"No {TEST_YEAR} observations for {REGION_ID}")
        frames.append(frame)
    return pl.concat(frames, how="diagonal_relaxed")


def assert_frozen_selection(actual: pd.DataFrame) -> None:
    expected = pd.read_csv(ROOT / "outputs" / "tables" / "day4_validation_selection.csv")
    keys = ["region_id", "daynight", "metric"]
    columns = keys + ["validation_rows", "selected_method"]
    actual = actual[columns].sort_values(keys).reset_index(drop=True)
    expected = expected[columns].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(actual, expected)


def main() -> None:
    observations = load_observations()
    pairs, matches = make_contemporaneous_grid_pairs(observations, GRID_KM)
    result = train_and_score(
        pairs,
        GRID_KM,
        TEST_START,
        BOOTSTRAP_REPLICATES,
        VALIDATION_START,
    )
    assert_frozen_selection(result.selection)
    if set(result.scored["region_id"]) != {REGION_ID}:
        raise AssertionError("The 2021 score contains a region outside the sealed pilot")
    if set(pd.to_datetime(result.scored["observation_date"]).dt.year) != {TEST_YEAR}:
        raise AssertionError("The 2021 score includes a different year")

    output = ROOT / "outputs" / "tables"
    output.mkdir(parents=True, exist_ok=True)
    result.metrics.to_csv(output / "independent_2021_western_iberia_metrics.csv", index=False)
    result.bootstrap.to_csv(output / "independent_2021_western_iberia_bootstrap.csv", index=False)
    matches[matches["observation_date"].map(lambda day: day.year == TEST_YEAR)].to_csv(
        output / "independent_2021_western_iberia_pass_matches.csv", index=False
    )
    result.scored.to_parquet(
        DATA_PROCESSED / "independent_2021_western_iberia_scored.parquet", index=False
    )
    print(f"2021 scored cell-passes={len(result.scored)}")
    print(result.metrics[result.metrics["region_id"].isin(["all", REGION_ID])].to_string(index=False))
    print(result.bootstrap.to_string(index=False))


if __name__ == "__main__":
    main()
