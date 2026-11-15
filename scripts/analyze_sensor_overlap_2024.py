
"""Analyze pairwise and three-way sensor co-occurrence in QORVEX."""

from itertools import combinations
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DATA_PATH = Path(
    "data/processed/victoria_2024/daily_activity.parquet"
)

OUTPUT_DIR = Path(
    "reports/victoria_2024_sensor_comparison"
)

PRODUCT_COLUMNS = {
    "MODIS_SP": "modis_detection_count",
    "VIIRS_NOAA20_SP": "noaa20_detection_count",
    "VIIRS_SNPP_SP": "snpp_detection_count",
}

CELL_DAY_COLUMNS = ["date_utc", "h3_res7"]


# ---------------------------------------------------------------------
# Load and validate data
# ---------------------------------------------------------------------

def load_daily_activity():
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    daily = pq.read_table(DATA_PATH).to_pandas()

    required_columns = (
        CELL_DAY_COLUMNS + list(PRODUCT_COLUMNS.values())
    )

    missing = set(required_columns) - set(daily.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if daily.empty:
        raise ValueError("Daily activity dataset is empty.")

    if daily[CELL_DAY_COLUMNS].isnull().any().any():
        raise ValueError("Null date or H3 cell found.")

    if daily.duplicated(subset=CELL_DAY_COLUMNS).any():
        raise ValueError("Duplicate date/H3 cell-day groups found.")

    for column in PRODUCT_COLUMNS.values():
        if daily[column].isnull().any():
            raise ValueError(f"Null values found in {column}.")

        if (daily[column] < 0).any():
            raise ValueError(f"Negative counts found in {column}.")

    print(f"Loaded {len(daily):,} cell-day records.")

    return daily


# ---------------------------------------------------------------------
# Identify product presence
# ---------------------------------------------------------------------

def add_product_presence(daily):
    result = daily.copy()

    presence_columns = {}

    for product, count_column in PRODUCT_COLUMNS.items():
        presence_column = f"{product.lower()}_present"

        result[presence_column] = result[count_column] > 0
        presence_columns[product] = presence_column

    return result, presence_columns


# ---------------------------------------------------------------------
# Pairwise overlap analysis
# ---------------------------------------------------------------------

def calculate_pairwise_overlap(daily, presence_columns):
    rows = []

    for product_a, product_b in combinations(
        PRODUCT_COLUMNS.keys(), 2
    ):
        column_a = presence_columns[product_a]
        column_b = presence_columns[product_b]

        present_a = daily[column_a]
        present_b = daily[column_b]

        shared = present_a & present_b
        a_only = present_a & ~present_b
        b_only = ~present_a & present_b
        union = present_a | present_b

        count_a = int(present_a.sum())
        count_b = int(present_b.sum())
        shared_count = int(shared.sum())
        a_only_count = int(a_only.sum())
        b_only_count = int(b_only.sum())
        union_count = int(union.sum())

        jaccard = (
            shared_count / union_count
            if union_count > 0
            else None
        )

        rows.append(
            {
                "product_a": product_a,
                "product_b": product_b,
                "product_a_cell_days": count_a,
                "product_b_cell_days": count_b,
                "shared_cell_days": shared_count,
                "product_a_only_cell_days": a_only_count,
                "product_b_only_cell_days": b_only_count,
                "union_cell_days": union_count,
                "jaccard_similarity": jaccard,
            }
        )

        # Internal consistency checks.
        assert count_a == shared_count + a_only_count
        assert count_b == shared_count + b_only_count
        assert union_count == (
            shared_count + a_only_count + b_only_count
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Three-product overlap analysis
# ---------------------------------------------------------------------

def calculate_three_way_overlap(daily, presence_columns):
    presence = pd.DataFrame(
        {
            product: daily[column]
            for product, column in presence_columns.items()
        }
    )

    all_three = presence.all(axis=1)
    exactly_two = presence.sum(axis=1) == 2
    exactly_one = presence.sum(axis=1) == 1

    no_product = presence.sum(axis=1) == 0

    result = pd.DataFrame(
        [
            {
                "category": "All three products",
                "cell_day_count": int(all_three.sum()),
            },
            {
                "category": "Exactly two products",
                "cell_day_count": int(exactly_two.sum()),
            },
            {
                "category": "Exactly one product",
                "cell_day_count": int(exactly_one.sum()),
            },
            {
                "category": "No product",
                "cell_day_count": int(no_product.sum()),
            },
        ]
    )

    result["percentage_of_dataset"] = (
        result["cell_day_count"] / len(daily) * 100
    )

    assert result["cell_day_count"].sum() == len(daily)

    return result


# ---------------------------------------------------------------------
# Product-level cell-day totals
# ---------------------------------------------------------------------

def calculate_product_totals(daily, presence_columns):
    rows = []

    for product, column in presence_columns.items():
        rows.append(
            {
                "product": product,
                "cell_days_with_detections": int(
                    daily[column].sum()
                ),
                "total_detection_records": int(
                    daily[PRODUCT_COLUMNS[product]].sum()
                ),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    print("=" * 65)
    print("QORVEX — Sensor Pairwise Overlap Analysis")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    daily = load_daily_activity()

    daily, presence_columns = add_product_presence(daily)

    print("\n[1/3] Calculating pairwise overlap...")

    pairwise = calculate_pairwise_overlap(
        daily,
        presence_columns,
    )

    pairwise_path = OUTPUT_DIR / "sensor_pairwise_overlap.csv"
    pairwise.to_csv(pairwise_path, index=False)

    print(pairwise.to_string(index=False))
    print(f"\nSaved: {pairwise_path}")

    print("\n[2/3] Calculating three-product overlap...")

    three_way = calculate_three_way_overlap(
        daily,
        presence_columns,
    )

    three_way_path = OUTPUT_DIR / "sensor_three_way_overlap.csv"
    three_way.to_csv(three_way_path, index=False)

    print(three_way.to_string(index=False))
    print(f"\nSaved: {three_way_path}")

    print("\n[3/3] Calculating product cell-day totals...")

    totals = calculate_product_totals(
        daily,
        presence_columns,
    )

    totals_path = OUTPUT_DIR / "sensor_cell_day_totals.csv"
    totals.to_csv(totals_path, index=False)

    print(totals.to_string(index=False))
    print(f"\nSaved: {totals_path}")

    print("\n" + "=" * 65)
    print("SENSOR OVERLAP ANALYSIS COMPLETED")
    print("=" * 65)

    print(f"Output directory: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
