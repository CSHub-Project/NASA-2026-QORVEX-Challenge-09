
"""Generate Victoria's 2024 fire-detection activity calendar."""

import os
from pathlib import Path

from qorvex.activity_calendar import generate_calendar_from_csv


DATA_DIR = Path(
    os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data")
)

INPUT_FILE = DATA_DIR / "victoria_fires_2024.csv"
OUTPUT_DIR = DATA_DIR / "activity_calendar"


def main() -> None:
    daily_path, monthly_path = generate_calendar_from_csv(
        INPUT_FILE,
        OUTPUT_DIR,
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    import pandas as pd

    daily = pd.read_csv(daily_path)
    monthly = pd.read_csv(monthly_path)

    print("Calendar generation complete.")
    print(f"Daily calendar:   {daily_path}")
    print(f"Monthly summary:  {monthly_path}")
    print(f"Calendar days:    {len(daily)}")
    print(f"Months:           {len(monthly)}")
    print(f"Annual detections: {daily['total_detections'].sum():,}")

    print("\nMonthly activity:")
    print(monthly.to_string(index=False))

    print("\nFive days with the highest detection counts:")
    print(
        daily.nlargest(5, "total_detections")[
            ["date", "total_detections"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
