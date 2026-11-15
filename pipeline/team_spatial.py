"""Validate and package the QORVEX Victoria 2024 spatial pilot."""

from __future__ import annotations

from pathlib import Path

import h3
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "team" / "qorvex_victoria_2024"
SOURCE_REPOSITORY = "https://github.com/CSHub-Project/NASA-2026-QORVEX-Challenge-09"
SOURCE_BRANCH = "feat/firms-pipeline-migration"
SOURCE_COMMIT = "4829811c19de"

PRODUCT_PATH = DATA_DIR / "product_contribution.csv"
MONTHLY_PATH = DATA_DIR / "monthly_detections.csv"
TOP_CELLS_PATH = DATA_DIR / "top_100_h3_cells.csv"
SPATIAL_SUMMARY_PATH = DATA_DIR / "spatial_summary.csv"
OVERLAP_PATH = DATA_DIR / "sensor_pairwise_overlap.csv"
FRP_PATH = DATA_DIR / "frp_statistics_by_product.csv"
POINTS_PATH = DATA_DIR / "victoria_2024_bbox_points.parquet"
SOURCE_PATHS = [PRODUCT_PATH, MONTHLY_PATH, TOP_CELLS_PATH, SPATIAL_SUMMARY_PATH, OVERLAP_PATH, FRP_PATH]


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def build_qorvex_spatial_payload() -> dict[str, object]:
    """Return browser-ready data only after cross-file scientific checks pass."""
    products = pd.read_csv(PRODUCT_PATH)
    monthly_long = pd.read_csv(MONTHLY_PATH)
    top_cells = pd.read_csv(TOP_CELLS_PATH)
    spatial = pd.read_csv(SPATIAL_SUMMARY_PATH).iloc[0]
    overlap = pd.read_csv(OVERLAP_PATH)
    frp = pd.read_csv(FRP_PATH)

    expected = {"MODIS_SP", "VIIRS_SNPP_SP", "VIIRS_NOAA20_SP"}
    if set(products["source_product"]) != expected:
        raise ValueError("Victoria product inventory must contain exactly three reviewed products")
    total = int(products["detection_count"].sum())
    if total != 57_305 or int(spatial["total_recorded_detections"]) != total:
        raise ValueError("Victoria totals differ across reviewed reports")
    if abs(float(products["percentage"].sum()) - 100.0) > 1e-6:
        raise ValueError("Victoria product shares do not sum to 100%")

    monthly_long["month"] = monthly_long["month_utc"].str[-2:].astype(int)
    monthly = (
        monthly_long.pivot(index="month", columns="source_product", values="detection_count")
        .fillna(0).astype(int).reset_index()
    )
    if list(monthly["month"]) != list(range(1, 13)) or int(monthly[list(expected)].to_numpy().sum()) != total:
        raise ValueError("Filtered monthly series must cover 12 months and agree with product totals")

    if len(top_cells) != 100 or int(top_cells.iloc[0]["detection_count"]) != 995:
        raise ValueError("Reviewed top-100 H3 ranking changed")
    cell_records: list[dict[str, object]] = []
    for row in top_cells.itertuples(index=False):
        cell = str(row.h3_res7)
        if not h3.is_valid_cell(cell) or h3.get_resolution(cell) != 7:
            raise ValueError(f"Invalid H3 resolution-7 cell: {cell}")
        center_lat, center_lon = h3.cell_to_latlng(cell)
        if abs(center_lat - float(row.latitude)) > 1e-6 or abs(center_lon - float(row.longitude)) > 1e-6:
            raise ValueError(f"Stored H3 center differs from computed center: {cell}")
        boundary = [[round(lon, 6), round(lat, 6)] for lat, lon in h3.cell_to_boundary(cell)]
        boundary.append(boundary[0])
        cell_records.append({
            "h3": cell,
            "count": int(row.detection_count),
            "center": [round(center_lon, 6), round(center_lat, 6)],
            "boundary": boundary,
        })

    if len(overlap) != 3 or not overlap["jaccard_similarity"].between(0, 1).all():
        raise ValueError("Pairwise sensor-overlap report is incomplete or invalid")

    return {
        "schemaVersion": 1,
        "title": "QORVEX Victoria multi-sensor spatial pilot",
        "scope": {"place": "Victoria, Australia", "year": 2024, "h3Resolution": 7},
        "source": {
            "repository": SOURCE_REPOSITORY,
            "branch": SOURCE_BRANCH,
            "commit": SOURCE_COMMIT,
            "license": "MIT",
            "contributor": "Aria Fazlollah",
        },
        "totalRecordedDetections": total,
        "activeH3Cells": int(spatial["active_h3_res7_cells"]),
        "products": _records(products),
        "monthly": _records(monthly),
        "topCells": cell_records,
        "pairwiseOverlap": _records(overlap),
        "frpSummary": _records(frp),
        "calendarSemantics": {
            "allowsMissingAsZero": False,
            "anomalyReady": False,
            "unit": "FIRMS detection record",
            "boundary": (
                "Descriptive filtered FIRMS records only. Cell-day co-occurrence does not identify "
                "a unique fire, demonstrate full satellite coverage, or support anomaly labels."
            ),
        },
    }


def build_victoria_point_payload() -> dict[str, object]:
    """Package the frozen three-product FIRMS point archive for date filtering."""
    points = pd.read_parquet(POINTS_PATH)
    required = {"date", "minute_utc", "latitude", "longitude", "product", "daynight", "frp_mw", "source_partition"}
    if set(points.columns) != required:
        raise ValueError("Victoria map-point schema changed")
    expected_products = {"M": 10_582, "N": 39_314, "S": 41_369}
    if len(points) != 91_265 or points["product"].value_counts().to_dict() != expected_products:
        raise ValueError("Victoria map-point product totals differ from the reviewed raw archive")
    if not points["daynight"].isin(["D", "N"]).all():
        raise ValueError("Victoria map-point archive contains an unknown day/night code")
    origin = pd.Timestamp("2024-01-01")
    dates = pd.to_datetime(points["date"], format="%Y-%m-%d", errors="raise")
    day_index = (dates - origin).dt.days
    if not day_index.between(0, 365).all():
        raise ValueError("Victoria map-point archive extends beyond leap year 2024")
    daily = (
        points.assign(date_value=dates)
        .groupby("date_value", as_index=False)
        .agg(records=("product", "size"), day_records=("daynight", lambda values: int((values == "D").sum())), night_records=("daynight", lambda values: int((values == "N").sum())))
        .sort_values("date_value")
    )
    rows = [
        [
            int(day), int(row.minute_utc), round(float(row.latitude), 5), round(float(row.longitude), 5),
            row.product, row.daynight, None if pd.isna(row.frp_mw) else round(float(row.frp_mw), 2),
        ]
        for day, row in zip(day_index, points.itertuples(index=False))
    ]
    return {
        "schemaVersion": 1,
        "columns": ["dayIndex", "minuteUtc", "latitude", "longitude", "productCode", "daynight", "frpMw"],
        "scope": {
            "name": "Victoria 2024 study window",
            "bbox": [140.9, -39.2, 150.1, -33.9],
            "startDate": "2024-01-01",
            "endDate": "2024-12-31",
            "boundaryMeaning": "Rectangular FIRMS study window, not the political boundary of Victoria",
            "processing": "NASA FIRMS Standard Processing",
        },
        "products": {
            "M": {"id": "MODIS_SP", "label": "MODIS", "records": 10_582},
            "N": {"id": "VIIRS_NOAA20_SP", "label": "NOAA-20 VIIRS", "records": 39_314},
            "S": {"id": "VIIRS_SNPP_SP", "label": "S-NPP VIIRS", "records": 41_369},
        },
        "totalRecords": len(points),
        "sourcePartitions": 222,
        "contributingPartitions": int(points["source_partition"].nunique()),
        "daily": [
            [row.date_value.strftime("%Y-%m-%d"), int(row.records), int(row.day_records), int(row.night_records)]
            for row in daily.itertuples(index=False)
        ],
        "rows": rows,
        "semantics": {
            "unit": "FIRMS active-fire detection record",
            "allowsMissingAsZero": False,
            "uniqueFireCount": False,
            "operationalAlert": False,
        },
    }
