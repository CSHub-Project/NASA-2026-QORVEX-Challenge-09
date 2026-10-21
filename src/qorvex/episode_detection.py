
"""Group consecutive anomalous days into strict activity episodes."""

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "any_anomaly",
    "total_detections",
    "anomaly_reasons",
}


def _parse_boolean_column(values: pd.Series) -> pd.Series:
    """Convert common CSV boolean representations to actual booleans."""
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)

    normalized = values.astype("string").str.strip().str.lower()
    valid_values = {"true", "false", "1", "0"}

    unexpected = normalized.dropna()[~normalized.dropna().isin(valid_values)]
    if not unexpected.empty:
        raise ValueError(
            "The any_anomaly column contains unrecognized boolean values."
        )

    if normalized.isna().any():
        raise ValueError("The any_anomaly column contains missing values.")

    return normalized.isin({"true", "1"})


def detect_anomaly_episodes(
    anomaly_report: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize consecutive days flagged by any_anomaly.

    A normal day or a missing calendar day ends an episode.
    Episodes describe anomalous detection activity, not confirmed fires.
    """
    missing_columns = REQUIRED_COLUMNS - set(anomaly_report.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Anomaly report is missing required columns: {missing}")

    daily = anomaly_report[list(REQUIRED_COLUMNS)].copy()

    daily["date"] = pd.to_datetime(
        daily["date"], errors="coerce", utc=True
    )

    if daily["date"].isna().any():
        raise ValueError("The anomaly report contains invalid dates.")

    # Compare calendar days, rather than timestamps or time zones.
    daily["date"] = daily["date"].dt.floor("D")

    if daily["date"].duplicated().any():
        raise ValueError("The anomaly report contains duplicate dates.")

    daily["any_anomaly"] = _parse_boolean_column(daily["any_anomaly"])
    daily["total_detections"] = pd.to_numeric(
        daily["total_detections"], errors="coerce"
    )

    if (
        daily["total_detections"].isna().any()
        or (daily["total_detections"] < 0).any()
    ):
        raise ValueError(
            "The report contains missing or negative detection counts."
        )

    daily["anomaly_reasons"] = (
        daily["anomaly_reasons"].fillna("").astype(str).str.strip()
    )

    daily = daily.sort_values("date").reset_index(drop=True)

    episodes = []
    current_days = []

    def save_current_episode() -> None:
        if not current_days:
            return

        episode = pd.DataFrame(current_days)
        peak_index = episode["total_detections"].idxmax()
        peak_row = episode.loc[peak_index]

        reasons = []
        for value in episode["anomaly_reasons"]:
            for reason in value.split(";"):
                reason = reason.strip()
                if reason and reason not in reasons:
                    reasons.append(reason)

        episode_number = len(episodes) + 1

        episodes.append(
            {
                "episode_id": f"E{episode_number:03d}",
                "start_date": episode["date"].min().strftime("%Y-%m-%d"),
                "end_date": episode["date"].max().strftime("%Y-%m-%d"),
                "duration_days": len(episode),
                "total_detections": int(
                    episode["total_detections"].sum()
                ),
                "peak_daily_detections": int(
                    peak_row["total_detections"]
                ),
                "peak_date": peak_row["date"].strftime("%Y-%m-%d"),
                "anomaly_reasons": "; ".join(reasons),
            }
        )

        current_days.clear()

    previous_date = None

    for row in daily.to_dict(orient="records"):
        current_date = row["date"]

        consecutive = (
            previous_date is not None
            and (current_date - previous_date).days == 1
        )

        if not row["any_anomaly"]:
            save_current_episode()
        else:
            if current_days and not consecutive:
                save_current_episode()

            current_days.append(row)

        previous_date = current_date

    save_current_episode()

    columns = [
        "episode_id",
        "start_date",
        "end_date",
        "duration_days",
        "total_detections",
        "peak_daily_detections",
        "peak_date",
        "anomaly_reasons",
    ]

    return pd.DataFrame(episodes, columns=columns)


def detect_anomaly_episodes_from_csv(
    input_file: str | Path,
    output_file: str | Path,
) -> pd.DataFrame:
    """Read an anomaly report, summarize episodes, and save the result."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Anomaly report not found: {input_path}"
        )

    anomaly_report = pd.read_csv(input_path)
    episodes = detect_anomaly_episodes(anomaly_report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    episodes.to_csv(output_path, index=False)

    return episodes
