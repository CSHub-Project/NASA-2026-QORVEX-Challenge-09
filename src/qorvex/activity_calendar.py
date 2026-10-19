
"""Generate daily and monthly fire-detection activity summaries."""

from pathlib import Path

import pandas as pd


def generate_activity_calendar(
    detections: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    timestamp_col: str = "timestamp_utc",
    product_col: str = "source_product",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate daily and monthly detection-count summaries.

    Every calendar day in the requested date range is included,
    even if no detections occurred on that day.
    """
    required_columns = {timestamp_col, product_col}
    missing = required_columns - set(detections.columns)

    if missing:
        raise ValueError(
            f"Input dataset is missing required columns: {sorted(missing)}"
        )

    start = pd.Timestamp(start_date, tz="UTC").normalize()
    end = pd.Timestamp(end_date, tz="UTC").normalize()

    if end < start:
        raise ValueError("end_date must be on or after start_date.")

    data = detections[[timestamp_col, product_col]].copy()
    data[timestamp_col] = pd.to_datetime(
        data[timestamp_col], errors="coerce", utc=True
    )
    data = data.dropna(subset=[timestamp_col])

    # Include the entire end date, but exclude the following midnight.
    data = data[
        data[timestamp_col].between(
            start, end + pd.Timedelta(days=1), inclusive="left"
        )
    ].copy()

    data["date"] = data[timestamp_col].dt.floor("D")

    dates = pd.date_range(start, end, freq="D")
    products = sorted(detections[product_col].dropna().unique().tolist())

    full_index = pd.MultiIndex.from_product(
        [dates, products],
        names=["date", product_col],
    )

    daily_by_product = (
        data.groupby(["date", product_col], observed=True)
        .size()
        .reindex(full_index, fill_value=0)
        .rename("detection_count")
        .reset_index()
    )

    daily_total = (
        daily_by_product.groupby("date", as_index=False)["detection_count"]
        .sum()
        .rename(columns={"detection_count": "total_detections"})
    )

    product_pivot = (
        daily_by_product.pivot(
            index="date",
            columns=product_col,
            values="detection_count",
        )
        .add_prefix("detections_")
        .reset_index()
    )

    daily = daily_total.merge(product_pivot, on="date", how="left")

    # Format the UTC date as YYYY-MM without converting to Period.
    daily["month"] = daily["date"].dt.strftime("%Y-%m")

    monthly = (
        daily.groupby("month", as_index=False)
        .agg(
            total_detections=("total_detections", "sum"),
            active_days=("total_detections", lambda s: int((s > 0).sum())),
            calendar_days=("date", "count"),
            mean_daily_detections=("total_detections", "mean"),
            peak_daily_detections=("total_detections", "max"),
        )
    )

    monthly["mean_daily_detections"] = monthly[
        "mean_daily_detections"
    ].round(2)

    return daily, monthly


def generate_calendar_from_csv(
    input_file: str | Path,
    output_directory: str | Path,
    *,
    start_date: str,
    end_date: str,
) -> tuple[Path, Path]:
    """Read detections from CSV and write daily and monthly summaries."""
    input_path = Path(input_file)
    output_dir = Path(output_directory)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input dataset not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    detections = pd.read_csv(input_path)

    daily, monthly = generate_activity_calendar(
        detections,
        start_date=start_date,
        end_date=end_date,
    )

    daily_path = output_dir / "victoria_daily_activity_2024.csv"
    monthly_path = output_dir / "victoria_monthly_activity_2024.csv"

    daily.to_csv(daily_path, index=False)
    monthly.to_csv(monthly_path, index=False)

    return daily_path, monthly_path
