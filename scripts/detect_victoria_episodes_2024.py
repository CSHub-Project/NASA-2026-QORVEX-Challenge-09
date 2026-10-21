
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

    print("Anomaly episode analysis complete.")
    print(f"Episodes identified: {len(episodes):,}")
    print(f"Report saved to:     {OUTPUT_FILE}")

    if episodes.empty:
        print("\nNo anomaly episodes were identified.")
        return

    print("\nEpisodes ordered by start date:")
    print(episodes.to_string(index=False))

    print("\nLongest episodes:")
    longest = episodes.sort_values(
        ["duration_days", "total_detections"],
        ascending=[False, False],
    ).head(10)

    print(
        longest[
            [
                "episode_id",
                "start_date",
                "end_date",
                "duration_days",
                "total_detections",
                "peak_daily_detections",
                "peak_date",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
