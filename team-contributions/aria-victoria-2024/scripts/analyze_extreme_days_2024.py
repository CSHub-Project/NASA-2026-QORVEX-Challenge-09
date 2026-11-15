
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
    / "victoria_2024_extreme_day_analysis"
)

PRODUCT_COLUMNS = {
    "MODIS_SP": "modis_detection_count",
    "VIIRS_NOAA20_SP": "noaa20_detection_count",
    "VIIRS_SNPP_SP": "snpp_detection_count",
}

TOP_N_VALUES = [5, 10]


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

    # This dataset contains only dates represented by
    # at least one recorded detection.
    daily = daily[
        daily["combined_detection_count"] > 0
    ].copy()

    return daily


# ---------------------------------------------------------
# Identify extreme days
# ---------------------------------------------------------

def identify_extreme_days(
    daily: pd.DataFrame,
) -> pd.DataFrame:

    products = list(PRODUCT_COLUMNS.keys())

    result = daily.copy()

    result = result.sort_values(
        "combined_detection_count",
        ascending=False,
    ).reset_index(drop=True)

    result["combined_detection_rank"] = (
        result.index + 1
    )

    for product in products:

        result[f"{product.lower()}_rank"] = (
            result[product]
            .rank(
                method="min",
                ascending=False,
            )
            .astype(int)
        )

    result["products_with_detections"] = (
        result[products].gt(0).sum(axis=1)
    )

    return result


# ---------------------------------------------------------
# Detection concentration
# ---------------------------------------------------------

def calculate_concentration(
    extreme_days: pd.DataFrame,
) -> pd.DataFrame:

    products = list(PRODUCT_COLUMNS.keys())

    annual_totals = (
        extreme_days[products].sum()
    )

    combined_annual_total = (
        extreme_days["combined_detection_count"].sum()
    )

    rows = []

    for n in TOP_N_VALUES:

        top_days = extreme_days.head(n)

        combined_top_total = (
            top_days["combined_detection_count"].sum()
        )

        row = {
            "top_n_days": n,
            "combined_detections": combined_top_total,
            "combined_annual_detections": (
                combined_annual_total
            ),
            "combined_share_pct": (
                combined_top_total
                / combined_annual_total
                * 100
            ),
        }

        for product in products:

            top_product_total = top_days[product].sum()

            row[f"{product.lower()}_detections"] = (
                top_product_total
            )

            row[f"{product.lower()}_annual_share_pct"] = (
                top_product_total
                / annual_totals[product]
                * 100
                if annual_totals[product] > 0
                else float("nan")
            )

        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# Correlation sensitivity
# ---------------------------------------------------------

def calculate_correlation_sensitivity(
    extreme_days: pd.DataFrame,
) -> pd.DataFrame:

    products = list(PRODUCT_COLUMNS.keys())

    scenarios = [
        ("All represented dates", set()),
    ]

    for n in TOP_N_VALUES:

        excluded_dates = set(
            extreme_days.head(n)["date_utc"]
        )

        scenarios.append(
            (
                f"Excluding top {n} combined-detection days",
                excluded_dates,
            )
        )

    rows = []

    for scenario_name, excluded_dates in scenarios:

        filtered = extreme_days[
            ~extreme_days["date_utc"].isin(
                excluded_dates
            )
        ]

        for i, product_a in enumerate(products):

            for product_b in products[i + 1:]:

                pearson = filtered[
                    [product_a, product_b]
                ].corr(method="pearson").iloc[0, 1]

                spearman = filtered[
                    [product_a, product_b]
                ].corr(method="spearman").iloc[0, 1]

                rows.append(
                    {
                        "scenario": scenario_name,
                        "dates_included": len(filtered),
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
    print("QORVEX — Extreme Daily Detection Analysis")
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

    print("\n[1/3] Identifying extreme detection days...")

    extreme_days = identify_extreme_days(daily)

    extreme_days.to_csv(
        OUTPUT_DIR / "ranked_daily_detections.csv",
        index=False,
    )

    display_columns = [
        "date_utc",
        "MODIS_SP",
        "VIIRS_NOAA20_SP",
        "VIIRS_SNPP_SP",
        "combined_detection_count",
        "products_with_detections",
        "combined_detection_rank",
    ]

    print("\nTop 10 dates by combined detections:")
    print(
        extreme_days.head(10)[
            display_columns
        ].to_string(index=False)
    )

    print(
        "\nSaved: ranked_daily_detections.csv"
    )

    print("\n[2/3] Calculating detection concentration...")

    concentration = calculate_concentration(
        extreme_days
    )

    concentration.to_csv(
        OUTPUT_DIR / "detection_concentration.csv",
        index=False,
    )

    print(concentration.to_string(index=False))

    print(
        "\nSaved: detection_concentration.csv"
    )

    print("\n[3/3] Testing correlation sensitivity...")

    sensitivity = calculate_correlation_sensitivity(
        extreme_days
    )

    sensitivity.to_csv(
        OUTPUT_DIR / "correlation_sensitivity.csv",
        index=False,
    )

    print(sensitivity.to_string(index=False))

    print(
        "\nSaved: correlation_sensitivity.csv"
    )

    print("\n" + "=" * 65)
    print("EXTREME DAY ANALYSIS COMPLETED")
    print("=" * 65)

    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
