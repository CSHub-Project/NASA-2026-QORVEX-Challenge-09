
"""Group consecutive anomalous days into strict activity episodes."""

from pathlib import Path

import pandas as pd


BASE_COLUMNS = {
    "date",
    "any_anomaly",
    "total_detections",
    "anomaly_reasons",
}

PRODUCTS = {
    "MODIS_SP": "is_anomaly_detections_MODIS_SP",
    "VIIRS_NOAA20_SP": "is_anomaly_detections_VIIRS_NOAA20_SP",
    "VIIRS_SNPP_SP": "is_anomaly_detections_VIIRS_SNPP_SP",
}

EVIDENCE_CATEGORIES = {
    "overall_and_multiple_products": (
        "Overall + multiple products"
    ),
    "overall_with_limited_product_support": (
        "Overall + limited product support"
    ),
    "multiple_products_only": "Multiple products only",
    "single_product_only": "Single product only",
    "no_anomaly": "No anomaly",
}


def _parse_boolean_column(values: pd.Series) -> pd.Series:
    """Convert common CSV boolean representations to actual booleans."""
    if pd.api.types.is_bool_dtype(values):
        if values.isna().any():
            raise ValueError("A boolean column contains missing values.")
        return values.astype(bool)

    normalized = values.astype("string").str.strip().str.lower()
    valid_values = {"true", "false", "1", "0"}

    unexpected = normalized.dropna()
    unexpected = unexpected[~unexpected.isin(valid_values)]

    if not unexpected.empty or normalized.isna().any():
        raise ValueError(
            "A boolean column contains missing or unrecognized values."
        )

    return normalized.isin({"true", "1"})


def _classify_daily_evidence(
    overall_anomaly: bool,
    product_flag_count: int,
) -> str:
    """Classify the pattern of daily anomaly flags, not fire severity."""
    if overall_anomaly and product_flag_count >= 2:
        return "overall_and_multiple_products"

    if overall_anomaly:
        return "overall_with_limited_product_support"

    if product_flag_count >= 2:
        return "multiple_products_only"

    if product_flag_count == 1:
        return "single_product_only"

    return "no_anomaly"


def detect_anomaly_episodes(
    anomaly_report: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize strict episodes and their cross-product anomaly evidence.

    An episode is a consecutive run of days for which any_anomaly is True.
    A normal or missing calendar day ends an episode.

    Evidence categories summarize which anomaly flags were raised.
    They are not fire-severity classifications or confirmation of a
    wildfire. Cross-product agreement is supporting evidence only.
    """
    required_columns = BASE_COLUMNS | set(PRODUCTS.values())
    missing_columns = required_columns - set(anomaly_report.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Anomaly report is missing columns: {missing}")

    daily = anomaly_report[
        list(BASE_COLUMNS | set(PRODUCTS.values()))
    ].copy()

    daily["date"] = pd.to_datetime(
        daily["date"], errors="coerce", utc=True
    )

    if daily["date"].isna().any():
        raise ValueError("The anomaly report contains invalid dates.")

    daily["date"] = daily["date"].dt.floor("D")

    if daily["date"].duplicated().any():
        raise ValueError("The anomaly report contains duplicate dates.")

    daily["any_anomaly"] = _parse_boolean_column(daily["any_anomaly"])

    for flag_column in PRODUCTS.values():
        daily[flag_column] = _parse_boolean_column(daily[flag_column])

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

    product_flag_columns = list(PRODUCTS.values())
    daily["product_flag_count"] = daily[product_flag_columns].sum(axis=1)
    daily["multi_product_flag"] = daily["product_flag_count"] >= 2

    daily["evidence_category"] = [
        _classify_daily_evidence(
            overall_anomaly=overall,
            product_flag_count=int(product_count),
        )
        for overall, product_count in zip(
            daily["any_anomaly"],
            daily["product_flag_count"],
        )
    ]

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

        duration = len(episode)
        multi_product_days = int(episode["multi_product_flag"].sum())

        record = {
            "episode_id": f"E{len(episodes) + 1:03d}",
            "start_date": episode["date"].min().strftime("%Y-%m-%d"),
            "end_date": episode["date"].max().strftime("%Y-%m-%d"),
            "duration_days": duration,
            "total_detections": int(episode["total_detections"].sum()),
            "peak_daily_detections": int(
                peak_row["total_detections"]
            ),
            "peak_date": peak_row["date"].strftime("%Y-%m-%d"),
            "overall_anomaly_days": int(episode["any_anomaly"].sum()),
            "multi_product_anomaly_days": multi_product_days,
            "multi_product_support_pct": round(
                100 * multi_product_days / duration, 2
            ),
            "anomaly_reasons": "; ".join(reasons),
        }

        for product, flag_column in PRODUCTS.items():
            output_column = {
                "MODIS_SP": "modis_anomaly_days",
                "VIIRS_NOAA20_SP": "viirs_noaa20_anomaly_days",
                "VIIRS_SNPP_SP": "viirs_snpp_anomaly_days",
            }[product]

            record[output_column] = int(episode[flag_column].sum())

        # Count the daily evidence categories within this episode.
        category_counts = episode["evidence_category"].value_counts()

        for category in EVIDENCE_CATEGORIES:
            record[f"{category}_days"] = int(
                category_counts.get(category, 0)
            )

        # Keep all categories visible rather than forcing a mixed episode
        # into a single potentially misleading label.
        record["evidence_profile"] = "; ".join(
            f"{EVIDENCE_CATEGORIES[category]}: {count}"
            for category, count in category_counts.items()
        )

        episodes.append(record)
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
        "overall_anomaly_days",
        "modis_anomaly_days",
        "viirs_noaa20_anomaly_days",
        "viirs_snpp_anomaly_days",
        "multi_product_anomaly_days",
        "multi_product_support_pct",
        "anomaly_reasons",
        *[f"{category}_days" for category in EVIDENCE_CATEGORIES],
        "evidence_profile",
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
