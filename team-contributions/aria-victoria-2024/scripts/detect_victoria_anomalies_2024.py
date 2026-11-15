
"""Detect unusual daily fire-detection activity in Victoria during 2024."""

import os
from pathlib import Path

from qorvex.anomaly_detection import detect_high_activity_from_csv


DATA_DIR = Path(
    os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data")
)

INPUT_FILE = (
    DATA_DIR
    / "activity_calendar"
    / "victoria_daily_activity_2024.csv"
)

OUTPUT_FILE = (
    DATA_DIR
    / "activity_calendar"
    / "victoria_anomaly_report_2024.csv"
)


def main() -> None:
    report = detect_high_activity_from_csv(
        INPUT_FILE,
        OUTPUT_FILE,
        window_days=29,
    )

    overall_flag = "is_anomaly_total_detections"
    product_flags = [
        column
        for column in report.columns
        if column.startswith("is_anomaly_detections_")
    ]

    flagged = report[report[overall_flag]].copy()

    print("Anomaly analysis complete.")
    print(f"Daily records analyzed: {len(report):,}")
    print(f"Days flagged overall:   {len(flagged):,}")
    print(f"Report saved to:        {OUTPUT_FILE}")

    print("\nTop 10 days by total detections:")
    print(
        report.nlargest(10, "total_detections")[
            [
                "date",
                "total_detections",
                "baseline_total_detections",
                "threshold_total_detections",
                overall_flag,
                "anomaly_reasons",
            ]
        ].to_string(index=False)
    )

    print("\nDays flagged by overall activity:")
    if flagged.empty:
        print("No days exceeded the overall threshold.")
    else:
        print(
            flagged[
                [
                    "date",
                    "total_detections",
                    "baseline_total_detections",
                    "threshold_total_detections",
                    "excess_total_detections",
                    "anomaly_reasons",
                ]
            ].to_string(index=False)
        )

    print("\nAnomaly flags by source product:")
    for column in product_flags:
        product = column.removeprefix("is_anomaly_detections_")
        print(f"{product}: {int(report[column].sum())} flagged days")


if __name__ == "__main__":
    main()
