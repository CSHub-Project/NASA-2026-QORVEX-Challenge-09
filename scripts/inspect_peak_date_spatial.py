
from pathlib import Path

import pandas as pd


DATA_PATH = Path(
    "data/processed/victoria_2024_filtered/daily_activity.parquet"
)

TARGET_DATE = "2024-04-15"

df = pd.read_parquet(DATA_PATH)

# Select the target date.
peak = df[df["date_utc"].astype(str) == TARGET_DATE].copy()

if peak.empty:
    raise ValueError(f"No records found for {TARGET_DATE}")

# Sort H3 cells by their combined detection counts.
peak = peak.sort_values(
    "combined_detection_count",
    ascending=False
)

total_detections = int(
    peak["combined_detection_count"].sum()
)

print(f"\nDate: {TARGET_DATE}")
print(f"Number of active H3 res7 cells: {len(peak)}")
print(f"Total recorded detections: {total_detections}")

print("\nTop 20 H3 cells:")

columns = [
    "h3_res7",
    "modis_detection_count",
    "noaa20_detection_count",
    "snpp_detection_count",
    "combined_detection_count",
    "active_product_count",
]

print(
    peak[columns]
    .head(20)
    .to_string(index=False)
)

print("\nSpatial concentration:")

for n in [1, 5, 10, 20]:
    top_sum = int(
        peak["combined_detection_count"]
        .head(n)
        .sum()
    )

    percentage = top_sum / total_detections * 100

    print(
        f"Top {n} cells: {top_sum:,} detections "
        f"({percentage:.2f}%)"
    )
