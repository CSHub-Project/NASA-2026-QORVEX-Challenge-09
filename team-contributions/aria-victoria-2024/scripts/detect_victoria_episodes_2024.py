
"""Create strict anomaly episodes for Victoria during 2024."""

import os
from pathlib import Path

from qorvex.episode_detection import detect_anomaly_episodes_from_csv


DATA_DIR = Path(
    os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data")
)

INPUT_FILE = (
    DATA_DIR
    / "activity_calendar"
    / "victoria_anomaly_report_2024.csv"
)

OUTPUT_FILE = (
    DATA_DIR
    / "activity_calendar"
    / "victoria_anomaly_episodes_2024.csv"
)


def main() -> None:
    episodes = detect_anomaly_episodes_from_csv(
        INPUT_FILE,
        OUTPUT_FILE,
    )

    print("Cross-sensor episode analysis complete.")
    print(f"Episodes identified: {len(episodes):,}")
    print(f"Report saved to:     {OUTPUT_FILE}")

    if episodes.empty:
        print("\nNo anomaly episodes were identified.")
        return

    columns = [
        "episode_id",
        "start_date",
        "end_date",
        "duration_days",
        "total_detections",
        "peak_daily_detections",
        "overall_anomaly_days",
        "modis_anomaly_days",
        "viirs_noaa20_anomaly_days",
        "viirs_snpp_anomaly_days",
        "multi_product_anomaly_days",
        "multi_product_support_pct",
    ]

    print("\nEpisode evidence summary:")
    print(episodes[columns].to_string(index=False))

    print("\nEpisodes with the strongest multi-product support:")
    strongest = episodes.sort_values(
        [
            "multi_product_support_pct",
            "multi_product_anomaly_days",
            "total_detections",
        ],
        ascending=[False, False, False],
    ).head(10)

    print(
        strongest[
            [
                "episode_id",
                "start_date",
                "end_date",
                "duration_days",
                "multi_product_anomaly_days",
                "multi_product_support_pct",
                "total_detections",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
