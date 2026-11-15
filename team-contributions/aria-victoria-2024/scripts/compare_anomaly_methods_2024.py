
"""Compare trailing and centered seasonal-reference anomaly methods.

This is a retrospective experiment. The centered reference window uses
future observations, so its results are not suitable for real-time alerts.
The existing production anomaly detector is not modified.
"""

from math import sqrt
from pathlib import Path
from statistics import median
import os

import pandas as pd

from qorvex.anomaly_detection import detect_high_activity


WINDOW_DAYS = 61
MIN_BASELINE_DAYS = 15

COUNT_COLUMNS = [
    "total_detections",
    "detections_MODIS_SP",
    "detections_VIIRS_NOAA20_SP",
    "detections_VIIRS_SNPP_SP",
]


def seasonal_reference(
    counts: pd.Series,
    *,
    window_days: int = WINDOW_DAYS,
    min_baseline_days: int = MIN_BASELINE_DAYS,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate centered reference baselines, thresholds, and flags."""
    if window_days < 3 or window_days % 2 == 0:
        raise ValueError("window_days must be an odd integer of at least 3.")

    if min_baseline_days < 1:
        raise ValueError("min_baseline_days must be at least 1.")

    values = pd.to_numeric(counts, errors="coerce")

    if values.isna().any() or (values < 0).any():
        raise ValueError("Detection counts must be valid and non-negative.")

    baselines = []
    thresholds = []
    flags = []
    half_window = window_days // 2

    for position, current_value in enumerate(values):
        start = max(0, position - half_window)
        end = min(len(values), position + half_window + 1)

        # Exclude the target day from its own reference sample.
        reference = values.iloc[start:end].drop(
            values.index[position]
        )

        if len(reference) < min_baseline_days:
            baselines.append(float("nan"))
            thresholds.append(float("nan"))
            flags.append(False)
            continue

        reference_values = reference.tolist()
        baseline = float(median(reference_values))
        mad = float(
            median(abs(value - baseline) for value in reference_values)
        )

        robust_spread = 3 * 1.4826 * mad
        count_margin = 3 * sqrt(baseline + 1)
        threshold = baseline + max(robust_spread, count_margin, 10.0)

        baselines.append(baseline)
        thresholds.append(threshold)
        flags.append(float(current_value) > threshold)

    return (
        pd.Series(baselines, index=counts.index, dtype="float64"),
        pd.Series(thresholds, index=counts.index, dtype="float64"),
        pd.Series(flags, index=counts.index, dtype="bool"),
    )


def main() -> None:
    data_dir = Path(
        os.environ.get("QORVEX_DATA_DIR", str(Path.home() / "data"))
    )
    activity_dir = data_dir / "activity_calendar"

    input_file = activity_dir / "victoria_daily_activity_2024.csv"
    output_file = activity_dir / "anomaly_method_comparison_2024.csv"

    if not input_file.is_file():
        raise FileNotFoundError(f"Daily calendar not found: {input_file}")

    daily = pd.read_csv(input_file)

    required = {"date", *COUNT_COLUMNS}
    missing = required - set(daily.columns)
    if missing:
        raise ValueError(
            "Daily calendar is missing columns: "
            + ", ".join(sorted(missing))
        )

    daily["date"] = pd.to_datetime(
        daily["date"], errors="coerce", utc=True
    )
    if daily["date"].isna().any():
        raise ValueError("The daily calendar contains invalid dates.")

    daily = daily.sort_values("date").reset_index(drop=True)

    if daily["date"].duplicated().any():
        raise ValueError("The daily calendar contains duplicate dates.")

    # Existing trailing method, unchanged.
    trailing = detect_high_activity(daily)

    # Keep its baselines, thresholds, and flags for a direct comparison.
    comparison = trailing.copy()

    for column in COUNT_COLUMNS:
        seasonal_baseline, seasonal_threshold, seasonal_flag = (
            seasonal_reference(comparison[column])
        )

        comparison[f"seasonal_baseline_{column}"] = (
            seasonal_baseline.round(2)
        )
        comparison[f"seasonal_threshold_{column}"] = (
            seasonal_threshold.round(2)
        )
        comparison[f"seasonal_is_anomaly_{column}"] = seasonal_flag

        comparison[f"trailing_is_anomaly_{column}"] = (
            trailing[f"is_anomaly_{column}"].astype(bool)
        )

        comparison[f"methods_agree_{column}"] = (
            comparison[f"trailing_is_anomaly_{column}"]
            == comparison[f"seasonal_is_anomaly_{column}"]
        )

    trailing_flag_columns = [
        f"trailing_is_anomaly_{column}" for column in COUNT_COLUMNS
    ]
    seasonal_flag_columns = [
        f"seasonal_is_anomaly_{column}" for column in COUNT_COLUMNS
    ]

    comparison["trailing_any_anomaly"] = (
        comparison[trailing_flag_columns].any(axis=1)
    )
    comparison["seasonal_any_anomaly"] = (
        comparison[seasonal_flag_columns].any(axis=1)
    )

    comparison["method_comparison"] = "neither flags anomaly"
    comparison.loc[
        comparison["trailing_any_anomaly"]
        & comparison["seasonal_any_anomaly"],
        "method_comparison",
    ] = "both flag anomaly"
    comparison.loc[
        comparison["trailing_any_anomaly"]
        & ~comparison["seasonal_any_anomaly"],
        "method_comparison",
    ] = "trailing only"
    comparison.loc[
        ~comparison["trailing_any_anomaly"]
        & comparison["seasonal_any_anomaly"],
        "method_comparison",
    ] = "seasonal only"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_file, index=False)

    trailing_any = comparison["trailing_any_anomaly"]
    seasonal_any = comparison["seasonal_any_anomaly"]
    both = trailing_any & seasonal_any

    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print(f"Daily records: {len(comparison)}")
    print()
    print("Overall anomaly comparison")
    print(f"  Trailing method flags: {int(trailing_any.sum())}")
    print(f"  Seasonal method flags: {int(seasonal_any.sum())}")
    print(f"  Both methods flag:     {int(both.sum())}")
    print(f"  Trailing only:         {int((trailing_any & ~seasonal_any).sum())}")
    print(f"  Seasonal only:         {int((seasonal_any & ~trailing_any).sum())}")
    print()

    print("Per-series comparison")
    for column in COUNT_COLUMNS:
        trailing_column = f"trailing_is_anomaly_{column}"
        seasonal_column = f"seasonal_is_anomaly_{column}"

        trailing_count = int(comparison[trailing_column].sum())
        seasonal_count = int(comparison[seasonal_column].sum())
        overlap = int(
            (
                comparison[trailing_column]
                & comparison[seasonal_column]
            ).sum()
        )

        print(
            f"  {column}: trailing={trailing_count}, "
            f"seasonal={seasonal_count}, both={overlap}"
        )

    print()
    print("Largest overall count disagreements")
    disagreements = comparison.loc[
        comparison["trailing_any_anomaly"]
        != comparison["seasonal_any_anomaly"],
        [
            "date",
            "total_detections",
            "baseline_total_detections",
            "threshold_total_detections",
            "seasonal_baseline_total_detections",
            "seasonal_threshold_total_detections",
            "method_comparison",
        ],
    ].copy()

    if disagreements.empty:
        print("  No disagreement in overall anomaly flags.")
    else:
        disagreements = disagreements.sort_values(
            "total_detections", ascending=False
        )
        print(disagreements.head(15).to_string(index=False))

    print()
    print(
        "These methods are heuristics; the comparison does not establish "
        "accuracy against confirmed fire events."
    )
    print(
        "The centered method uses future observations and is intended "
        "for retrospective analysis only."
    )


if __name__ == "__main__":
    main()
