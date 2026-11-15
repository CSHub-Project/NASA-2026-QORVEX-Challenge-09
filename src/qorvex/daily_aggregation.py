
"""Aggregate spatially indexed FIRMS detections into daily activity records."""

import h3
import pandas as pd


PRODUCTS = {
    "MODIS_SP": "modis",
    "VIIRS_NOAA20_SP": "noaa20",
    "VIIRS_SNPP_SP": "snpp",
}

OUTPUT_COLUMNS = [
    "date_utc",
    "h3_res7",
    "modis_detection_count",
    "noaa20_detection_count",
    "snpp_detection_count",
    "combined_detection_count",
    "modis_frp_mean_mw",
    "modis_frp_max_mw",
    "modis_frp_sum_mw",
    "noaa20_frp_mean_mw",
    "noaa20_frp_max_mw",
    "noaa20_frp_sum_mw",
    "snpp_frp_mean_mw",
    "snpp_frp_max_mw",
    "snpp_frp_sum_mw",
    "active_product_count",
    "first_detection_utc",
    "last_detection_utc",
]

REQUIRED_COLUMNS = {
    "timestamp_utc",
    "h3_res7",
    "source_product",
    "frp_mw",
}


def aggregate_daily_activity(detections: pd.DataFrame) -> pd.DataFrame:
    """Aggregate detections by H3 resolution 7 cell and UTC calendar date."""

    missing_columns = REQUIRED_COLUMNS - set(detections.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if detections.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    data = detections.copy()

    data["timestamp_utc"] = pd.to_datetime(
        data["timestamp_utc"],
        utc=True,
        errors="raise",
    )

    if data["timestamp_utc"].isna().any():
        raise ValueError("Detection timestamps cannot be missing.")

    if data["source_product"].isna().any():
        raise ValueError("Source product identifiers cannot be missing.")

    unknown_products = set(data["source_product"]) - set(PRODUCTS)

    if unknown_products:
        raise ValueError(
            f"Unsupported source products: {sorted(unknown_products)}"
        )

    valid_cells = data["h3_res7"].map(
        lambda cell: (
            isinstance(cell, str)
            and h3.is_valid_cell(cell)
            and h3.get_resolution(cell) == 7
        )
    )

    if not valid_cells.all():
        raise ValueError(
            "All h3_res7 values must be valid resolution 7 cells."
        )

    data["frp_mw"] = pd.to_numeric(
        data["frp_mw"],
        errors="raise",
    )

    if (data["frp_mw"].dropna() < 0).any():
        raise ValueError("FRP values cannot be negative.")

    data["date_utc"] = data["timestamp_utc"].dt.date

    results = []

    for (date_utc, h3_res7), group in data.groupby(
        ["date_utc", "h3_res7"],
        sort=True,
    ):
        result = {
            "date_utc": date_utc,
            "h3_res7": h3_res7,
        }

        active_product_count = 0

        for product, prefix in PRODUCTS.items():
            product_records = group[
                group["source_product"] == product
            ]

            detection_count = len(product_records)

            result[f"{prefix}_detection_count"] = detection_count

            if detection_count:
                active_product_count += 1
                frp = product_records["frp_mw"]

                result[f"{prefix}_frp_mean_mw"] = frp.mean()
                result[f"{prefix}_frp_max_mw"] = frp.max()
                result[f"{prefix}_frp_sum_mw"] = frp.sum(min_count=1)
            else:
                result[f"{prefix}_frp_mean_mw"] = None
                result[f"{prefix}_frp_max_mw"] = None
                result[f"{prefix}_frp_sum_mw"] = None

        result["combined_detection_count"] = len(group)
        result["active_product_count"] = active_product_count
        result["first_detection_utc"] = group["timestamp_utc"].min()
        result["last_detection_utc"] = group["timestamp_utc"].max()

        results.append(result)

    return pd.DataFrame(results, columns=OUTPUT_COLUMNS)
