
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "victoria_2024"
    / "daily_activity.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "victoria_2024_within_month_correlation"
)

PRODUCT_COLUMNS = {
    "MODIS_SP": "modis_detection_count",
    "VIIRS_NOAA20_SP": "noaa20_detection_count",
    "VIIRS_SNPP_SP": "snpp_detection_count",
}


# ---------------------------------------------------------
# Load and validate data
# ---------------------------------------------------------

def load_daily_totals() -> pd.DataFrame:

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    df = pd.read_parquet(INPUT_FILE)

    required_columns = [
        "date_utc",
        *PRODUCT_COLUMNS.values(),
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    if df.empty:
        raise ValueError("Input dataset is empty.")

    if df["date_utc"].isna().any():
        raise ValueError("Null dates found.")

    df["date_utc"] = pd.to_datetime(
        df["date_utc"],
        utc=True,
    )

    for column in PRODUCT_COLUMNS.values():

        if df[column].isna().any():
            raise ValueError(
                f"Null values found in {column}."
            )

        if (df[column] < 0).any():
            raise ValueError(
                f"Negative values found in {column}."
            )

    daily = (
        df.groupby("date_utc", as_index=False)[
            list(PRODUCT_COLUMNS.values())
        ]
        .sum()
        .sort_values("date_utc")
        .reset_index(drop=True)
    )

    daily = daily.rename(
        columns={
            value: key
            for key, value in PRODUCT_COLUMNS.items()
        }
    )

    products = list(PRODUCT_COLUMNS.keys())

    daily["combined_detection_count"] = (
        daily[products].sum(axis=1)
    )

    # Retain only dates represented by at least one
    # recorded detection, consistent with prior analyses.
    daily = daily[
        daily["combined_detection_count"] > 0
    ].copy()

    daily["month"] = daily["date_utc"].dt.month

    return daily


# ---------------------------------------------------------
# Calculate within-month deviations
# ---------------------------------------------------------

def calculate_monthly_deviations(
    daily: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    products = list(PRODUCT_COLUMNS.keys())

    result = daily.copy()

    monthly_means = (
        result.groupby("month")[products]
        .mean()
        .add_suffix("_monthly_mean")
    )

    result = result.join(
        monthly_means,
        on="month",
    )

    for product in products:

        mean_column = f"{product}_monthly_mean"
        deviation_column = f"{product}_monthly_deviation"

        result[deviation_column] = (
            result[product] - result[mean_column]
        )

    deviation_columns = [
        f"{product}_monthly_deviation"
        for product in products
    ]

    return result, deviation_columns


# ---------------------------------------------------------
# Correlation calculation
# ---------------------------------------------------------

def calculate_correlations(
    data: pd.DataFrame,
    columns: list[str],
    scenario: str,
) -> pd.DataFrame:

    rows = []

    for product_a, product_b in combinations(columns, 2):

        pair = data[[product_a, product_b]].dropna()

        if len(pair) < 3:
            pearson = float("nan")
            spearman = float("nan")
        else:
            pearson = pair.corr(
                method="pearson"
            ).iloc[0, 1]

            spearman = pair.corr(
                method="spearman"
            ).iloc[0, 1]

        rows.append(
            {
                "scenario": scenario,
                "dates_included": len(pair),
                "product_a": product_a,
                "product_b": product_b,
                "pearson_correlation": pearson,
                "spearman_correlation": spearman,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> None:

    print("=" * 65)
    print("QORVEX — Within-Month Correlation Analysis")
    print("=" * 65)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nLoading daily activity dataset...")

    daily = load_daily_totals()

    print(
        f"Loaded {len(daily):,} represented dates."
    )

    print(
        f"Months represented: "
        f"{daily['month'].nunique()}"
    )

    print("\n[1/3] Calculating monthly deviations...")

    deviations, deviation_columns = (
        calculate_monthly_deviations(daily)
    )

    deviations.to_csv(
        OUTPUT_DIR / "daily_monthly_deviations.csv",
        index=False,
    )

    print(
        "Saved: daily_monthly_deviations.csv"
    )

    print("\n[2/3] Calculating original correlations...")

    products = list(PRODUCT_COLUMNS.keys())

    original = calculate_correlations(
        daily,
        products,
        "Original daily counts",
    )

    print("\n[3/3] Calculating within-month correlations...")

    within_month = calculate_correlations(
        deviations,
        deviation_columns,
        "Within-month deviations",
    )

    # Replace internal column names with readable
    # product names in the output.
    name_mapping = {
        f"{product}_monthly_deviation": product
        for product in products
    }

    within_month["product_a"] = (
        within_month["product_a"].map(name_mapping)
    )

    within_month["product_b"] = (
        within_month["product_b"].map(name_mapping)
    )

    results = pd.concat(
        [original, within_month],
        ignore_index=True,
    )

    results.to_csv(
        OUTPUT_DIR / "correlation_comparison.csv",
        index=False,
    )

    print("\nCorrelation comparison:")
    print(results.to_string(index=False))

    print("\n" + "=" * 65)
    print("WITHIN-MONTH CORRELATION ANALYSIS COMPLETED")
    print("=" * 65)

    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
