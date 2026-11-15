
"""Detect unusually high daily fire-detection activity."""

from math import sqrt
from pathlib import Path
from statistics import median

import pandas as pd


DEFAULT_WINDOW_DAYS = 29
MIN_BASELINE_DAYS = 15


def _rolling_median_absolute_deviation(
    values: pd.Series,
    *,
    window_days: int,
    min_periods: int,
) -> pd.Series:
    """Calculate the rolling MAD using preceding observations."""
    def calculate_mad(window_values) -> float:
        center = median(window_values)
        return float(
            median(abs(value - center) for value in window_values)
        )

    return values.rolling(
        window=window_days,
        min_periods=min_periods,
    ).apply(calculate_mad, raw=True)


def detect_high_activity(
    daily_calendar: pd.DataFrame,
    *,
    date_col: str = "date",
    total_col: str = "total_detections",
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> pd.DataFrame:
    """Flag unusually high counts relative to the preceding days.

    Each count series receives its own trailing baseline. The current
    day is excluded from its baseline.

    A flag indicates statistically unusual detection activity, not a
    confirmed severe fire event.
    """
    if window_days < MIN_BASELINE_DAYS or window_days % 2 == 0:
        raise ValueError(
            f"window_days must be an odd integer of at least "
            f"{MIN_BASELINE_DAYS}."
        )

    if date_col not in daily_calendar.columns:
        raise ValueError(f"Missing date column: {date_col}")

    if total_col not in daily_calendar.columns:
        raise ValueError(f"Missing total-count column: {total_col}")

    result = daily_calendar.copy()
    result[date_col] = pd.to_datetime(
        result[date_col], errors="coerce", utc=True
    )

    if result[date_col].isna().any():
        raise ValueError("The calendar contains invalid dates.")

    result = result.sort_values(date_col).reset_index(drop=True)

    if result[date_col].duplicated().any():
        raise ValueError("The daily calendar contains duplicate dates.")

    count_columns = [
        column
        for column in result.columns
        if column == total_col or column.startswith("detections_")
    ]

    if not count_columns:
        raise ValueError("No detection-count columns were found.")

    for column in count_columns:
        counts = pd.to_numeric(result[column], errors="coerce")

        if counts.isna().any() or (counts < 0).any():
            raise ValueError(
                f"Column {column!r} contains missing or negative counts."
            )

        # Shift by one day so today's count cannot influence today's baseline.
        prior_counts = counts.shift(1)

        baseline = prior_counts.rolling(
            window=window_days,
            min_periods=MIN_BASELINE_DAYS,
        ).median()

        mad = _rolling_median_absolute_deviation(
            prior_counts,
            window_days=window_days,
            min_periods=MIN_BASELINE_DAYS,
        )

        robust_spread = 3 * 1.4826 * mad
        count_margin = baseline.map(
            lambda value: (
                3 * sqrt(value + 1)
                if pd.notna(value)
                else float("nan")
            )
        )

        margin = pd.concat(
            [
                robust_spread,
                count_margin,
                pd.Series(10.0, index=result.index),
            ],
            axis=1,
        ).max(axis=1)

        threshold = baseline + margin
        flag = counts > threshold

        result[f"baseline_{column}"] = baseline.round(2)
        result[f"threshold_{column}"] = threshold.round(2)
        result[f"excess_{column}"] = (counts - baseline).round(2)
        result[f"is_anomaly_{column}"] = flag.fillna(False)

    flag_columns = [
        column
        for column in result.columns
        if column.startswith("is_anomaly_")
    ]

    result["any_anomaly"] = result[flag_columns].any(axis=1)

    def explain_flags(row: pd.Series) -> str:
        reasons = []

        for flag_column in flag_columns:
            if bool(row[flag_column]):
                metric = flag_column.removeprefix("is_anomaly_")

                if metric == total_col:
                    reasons.append("overall")
                elif metric.startswith("detections_"):
                    reasons.append(metric.removeprefix("detections_"))

        return "; ".join(reasons)

    result["anomaly_reasons"] = result.apply(explain_flags, axis=1)

    return result


def detect_high_activity_from_csv(
    input_file: str | Path,
    output_file: str | Path,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> pd.DataFrame:
    """Load the daily calendar, detect anomalies, and save a report."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Daily calendar not found: {input_path}"
        )

    daily_calendar = pd.read_csv(input_path)

    report = detect_high_activity(
        daily_calendar,
        window_days=window_days,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False)

    return report
