
from __future__ import annotations

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
    / "victoria_2024_temporal_sensor_comparison"
)

PRODUCT_COLUMNS = {
    "MODIS_SP": "modis_detection_count",
    "VIIRS_NOAA20_SP": "noaa20_detection_count",
    "VIIRS_SNPP_SP": "snpp_detection_count",
}

SEASON_BY_MONTH = {
    12: "Summer",
    1: "Summer",
    2: "Summer",
    3: "Autumn",
    4: "Autumn",
    5: "Autumn",
    6: "Winter",
    7: "Winter",
    8: "Winter",
    9: "Spring",
    10: "Spring",
    11: "Spring",
}

SEASON_ORDER = ["Summer", "Autumn", "Winter", "Spring"]


# ---------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------

def load_daily_activity() -> pd.DataFrame:
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
        raise ValueError("Daily activity dataset is empty.")

    if df["date_utc"].isna().any():
        raise ValueError("Null dates found in dataset.")

    for column in PRODUCT_COLUMNS.values():
        if df[column].isna().any():
            raise ValueError(
                f"Null values found in {column}."
            )

        if (df[column] < 0).any():
            raise ValueError(
                f"Negative values found in {column}."
            )

    df["date_utc"] = pd.to_datetime(
        df["date_utc"],
        utc=True,
    )

    print(f"Loaded {len(df):,} cell-day records.")

    return df


# ---------------------------------------------------------
# Daily totals
# ---------------------------------------------------------

def calculate_daily_totals(
    df: pd.DataFrame,
) -> pd.DataFrame:

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

    daily["combined_detection_count"] = (
        daily[list(PRODUCT_COLUMNS.keys())]
        .sum(axis=1)
    )

    return daily


# ---------------------------------------------------------
# Monthly comparison
# ---------------------------------------------------------

def calculate_monthly_comparison(
    daily: pd.DataFrame,
) -> pd.DataFrame:

    monthly = (
        daily.assign(
            month=daily["date_utc"].dt.month
        )
        .groupby("month", as_index=False)[
            [
                *PRODUCT_COLUMNS.keys(),
                "combined_detection_count",
            ]
        ]
        .sum()
    )

    monthly["month_name"] = monthly["month"].apply(
        lambda month: pd.Timestamp(
            year=2024,
            month=month,
            day=1,
        ).strftime("%B")
    )

    monthly["total_product_detections"] = (
        monthly[list(PRODUCT_COLUMNS.keys())]
        .sum(axis=1)
    )

    for product in PRODUCT_COLUMNS:
        monthly[f"{product.lower()}_share_pct"] = (
            monthly[product]
            / monthly["total_product_detections"]
            * 100
        )

    return monthly


# ---------------------------------------------------------
# Seasonal comparison
# ---------------------------------------------------------

def calculate_seasonal_comparison(
    daily: pd.DataFrame,
) -> pd.DataFrame:

    seasonal = daily.copy()

    seasonal["month"] = (
        seasonal["date_utc"].dt.month
    )

    seasonal["season"] = seasonal["month"].map(
        SEASON_BY_MONTH
    )

    result = (
        seasonal.groupby("season", as_index=False)[
            [
                *PRODUCT_COLUMNS.keys(),
                "combined_detection_count",
            ]
        ]
        .sum()
    )

    result["season"] = pd.Categorical(
        result["season"],
        categories=SEASON_ORDER,
        ordered=True,
    )

    result = result.sort_values(
        "season"
    ).reset_index(drop=True)

    result["total_product_detections"] = (
        result[list(PRODUCT_COLUMNS.keys())]
        .sum(axis=1)
    )

    for product in PRODUCT_COLUMNS:
        result[f"{product.lower()}_share_pct"] = (
            result[product]
            / result["total_product_detections"]
            * 100
        )

    return result


# ---------------------------------------------------------
# Daily correlation
# ---------------------------------------------------------

def calculate_daily_correlations(
    daily: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    products = list(PRODUCT_COLUMNS.keys())

    pearson = daily[products].corr(
        method="pearson"
    )

    spearman = daily[products].corr(
        method="spearman"
    )

    pearson_long = (
        pearson.rename_axis("product_a")
        .reset_index()
        .melt(
            id_vars="product_a",
            var_name="product_b",
            value_name="pearson_correlation",
        )
    )

    spearman_long = (
        spearman.rename_axis("product_a")
        .reset_index()
        .melt(
            id_vars="product_a",
            var_name="product_b",
            value_name="spearman_correlation",
        )
    )

    correlations = pearson_long.merge(
        spearman_long,
        on=["product_a", "product_b"],
    )

    return pearson, correlations


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> None:

    print("=" * 65)
    print("QORVEX — Temporal Sensor Comparison")
    print("=" * 65)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nLoading daily activity dataset...")
    df = load_daily_activity()

    print("\n[1/4] Calculating daily totals...")
    daily = calculate_daily_totals(df)

    daily.to_csv(
        OUTPUT_DIR / "daily_sensor_totals.csv",
        index=False,
    )

    print(
        f"Saved daily totals for "
        f"{len(daily):,} represented dates."
    )

    print("\n[2/4] Calculating monthly comparison...")
    monthly = calculate_monthly_comparison(daily)

    monthly.to_csv(
        OUTPUT_DIR / "monthly_sensor_comparison.csv",
        index=False,
    )

    print(monthly.to_string(index=False))

    print("\n[3/4] Calculating seasonal comparison...")
    seasonal = calculate_seasonal_comparison(daily)

    seasonal.to_csv(
        OUTPUT_DIR / "seasonal_sensor_comparison.csv",
        index=False,
    )

    print(seasonal.to_string(index=False))

    print("\n[4/4] Calculating daily correlations...")

    pearson, correlations = (
        calculate_daily_correlations(daily)
    )

    pearson.to_csv(
        OUTPUT_DIR / "daily_pearson_correlation_matrix.csv"
    )

    correlations.to_csv(
        OUTPUT_DIR / "daily_sensor_correlations.csv",
        index=False,
    )

    print("\nPearson correlation matrix:")
    print(pearson.to_string())

    print("\nPairwise correlation results:")
    print(correlations.to_string(index=False))

    print("\n" + "=" * 65)
    print("TEMPORAL SENSOR COMPARISON COMPLETED")
    print("=" * 65)

    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
