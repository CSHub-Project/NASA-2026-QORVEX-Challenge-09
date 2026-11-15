
from pathlib import Path

import pandas as pd


DATA_PATH = Path(
    "data/processed/victoria_2024_filtered/daily_activity.parquet"
)

OUTPUT_PATH = Path(
    "reports/victoria_2024_filtered_exploratory_profile/"
    "top_20_dates_spatial_concentration.csv"
)

df = pd.read_parquet(DATA_PATH)

# Calculate daily totals and identify the 20 highest-count dates.
daily_totals = (
    df.groupby("date_utc")["combined_detection_count"]
    .sum()
    .sort_values(ascending=False)
    .head(20)
)

results = []

for date, total in daily_totals.items():

    day = df[df["date_utc"] == date].copy()

    day = day.sort_values(
        "combined_detection_count",
        ascending=False
    )

    active_cells = len(day)

    top_10 = day["combined_detection_count"].head(10).sum()
    top_20 = day["combined_detection_count"].head(20).sum()

    results.append({
        "date_utc": date,
        "total_detections": int(total),
        "active_h3_res7_cells": active_cells,
        "top_10_cells_share_pct": round(
            top_10 / total * 100, 2
        ),
        "top_20_cells_share_pct": round(
            top_20 / total * 100, 2
        ),
    })

result_df = pd.DataFrame(results)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
result_df.to_csv(OUTPUT_PATH, index=False)

print("\nTOP 20 DATES: SPATIAL CONCENTRATION\n")
print(result_df.to_string(index=False))

print(f"\nSaved to: {OUTPUT_PATH}")
