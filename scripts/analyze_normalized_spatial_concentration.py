
from pathlib import Path
import math

import pandas as pd


DATA_PATH = Path(
    "data/processed/victoria_2024_filtered/daily_activity.parquet"
)

OUTPUT_PATH = Path(
    "reports/victoria_2024_filtered_exploratory_profile/"
    "top_20_dates_normalized_spatial_concentration.csv"
)

df = pd.read_parquet(DATA_PATH)

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

    # Number of cells representing the highest-count 10%.
    top_10_percent_count = max(
        1,
        math.ceil(active_cells * 0.10)
    )

    top_cells_sum = day[
        "combined_detection_count"
    ].head(top_10_percent_count).sum()

    results.append({
        "date_utc": date,
        "total_detections": int(total),
        "active_h3_res7_cells": active_cells,
        "top_10_percent_cell_count": top_10_percent_count,
        "top_10_percent_detection_share_pct": round(
            top_cells_sum / total * 100, 2
        ),
    })

result_df = pd.DataFrame(results)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
result_df.to_csv(OUTPUT_PATH, index=False)

print("\nNORMALIZED SPATIAL CONCENTRATION\n")
print(result_df.to_string(index=False))

print(f"\nSaved to: {OUTPUT_PATH}")
