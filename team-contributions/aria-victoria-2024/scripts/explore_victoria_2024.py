
"""Generate a descriptive exploratory profile of QORVEX Victoria 2024 data."""

from pathlib import Path

import h3
import pandas as pd
import plotly.express as px
import pyarrow.parquet as pq


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DATA_DIR = Path("data/processed/victoria_2024_filtered")

OUTPUT_DIR = Path(
    "reports/victoria_2024_filtered_exploratory_profile"
)

INDEXED_PATH = DATA_DIR / "spatially_indexed_detections.parquet"
DAILY_PATH = DATA_DIR / "daily_activity.parquet"

PRODUCTS = {
    "MODIS_SP": "MODIS",
    "VIIRS_NOAA20_SP": "VIIRS NOAA-20",
    "VIIRS_SNPP_SP": "VIIRS SNPP",
}

SEASON_BY_MONTH = {
    12: "Summer",
    1: "Summer",
    2: "Summer",
    3: "Autumn",
    4: "Autumn",
    5: "Autumn",
    6: "Winter",
    7: "Winter",
    8: "Winter",
    9: "Spring",
    10: "Spring",
    11: "Spring",
}

SEASON_ORDER = ["Summer", "Autumn", "Winter", "Spring"]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def require(condition, message):
    if not condition:
        raise ValueError(message)


def save_table(dataframe, filename):
    path = OUTPUT_DIR / filename
    dataframe.to_csv(path, index=False)
    print(f"Saved table: {path}")


def save_chart(figure, filename):
    path = OUTPUT_DIR / filename
    figure.write_html(path)
    print(f"Saved chart: {path}")


def write_report(content):
    path = OUTPUT_DIR / "exploratory_profile.md"
    path.write_text(content, encoding="utf-8")
    print(f"Saved report: {path}")


def format_number(value):
    return f"{value:,.0f}"


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------


def load_datasets():
    """Load and validate the Victoria-filtered analytical datasets."""

    require(
        INDEXED_PATH.is_file(),
        f"Missing file: {INDEXED_PATH}"
    )

    require(
        DAILY_PATH.is_file(),
        f"Missing file: {DAILY_PATH}"
    )

    print("Loading spatially indexed detections...")
    indexed = pq.read_table(INDEXED_PATH).to_pandas()

    print("Loading daily activity...")
    daily = pq.read_table(DAILY_PATH).to_pandas()

    require(not indexed.empty, "Indexed dataset is empty.")
    require(not daily.empty, "Daily activity dataset is empty.")

    # Verify expected Victoria dataset size.
    require(
        len(indexed) == 57_305,
        f"Expected 57,305 indexed records, found {len(indexed):,}."
    )

    # Verify exact product distribution.
    expected_products = {
        "MODIS_SP": 6_161,
        "VIIRS_NOAA20_SP": 25_300,
        "VIIRS_SNPP_SP": 25_844,
    }

    actual_products = (
        indexed["source_product"]
        .value_counts()
        .to_dict()
    )

    require(
        actual_products == expected_products,
        "Source product distribution does not match "
        "the validated Victoria dataset."
    )

    # Verify daily aggregation.
    require(
        len(daily) == 14_230,
        f"Expected 14,230 daily groups, found {len(daily):,}."
    )

    require(
        int(daily["combined_detection_count"].sum())
        == len(indexed),
        "Daily detection counts do not reconcile "
        "with indexed records."
    )

    # Verify H3 resolution 7.
    require(
        "h3_res7" in indexed.columns,
        "Missing h3_res7 in indexed dataset."
    )

    require(
        "h3_res7" in daily.columns,
        "Missing h3_res7 in daily dataset."
    )

    require(
        indexed["h3_res7"].notna().all(),
        "Missing H3 resolution 7 indices in indexed dataset."
    )

    require(
        daily["h3_res7"].notna().all(),
        "Missing H3 resolution 7 indices in daily dataset."
    )

    # Prepare temporal attributes.
    indexed["timestamp_utc"] = pd.to_datetime(
        indexed["timestamp_utc"],
        utc=True
    )

    indexed["date_utc"] = indexed["timestamp_utc"].dt.date

    indexed["month_utc"] = (
        indexed["timestamp_utc"].dt.strftime("%Y-%m")
    )

    indexed["month_number"] = (
        indexed["timestamp_utc"].dt.month
    )

    indexed["season"] = (
        indexed["month_number"].map(SEASON_BY_MONTH)
    )

    daily["date_utc"] = pd.to_datetime(
        daily["date_utc"]
    )

    print("\nDataset validation passed.")

    print(f"Loaded {len(indexed):,} indexed detections.")
    print(f"Loaded {len(daily):,} daily activity rows.")

    print("\nProduct distribution:")
    print(indexed["source_product"].value_counts().to_string())

    print(
        "\nDistinct dates with recorded detections:",
        indexed["date_utc"].nunique()
    )

    print(
        "Distinct H3 resolution-7 cells:",
        indexed["h3_res7"].nunique()
    )

    return indexed, daily

# ---------------------------------------------------------------------
# 1. Product contribution
# ---------------------------------------------------------------------

def analyze_products(indexed):
    summary = (
        indexed.groupby("source_product")
        .size()
        .rename("detection_count")
        .reset_index()
    )

    summary["percentage"] = (
        summary["detection_count"] / len(indexed) * 100
    )

    summary["product_name"] = summary["source_product"].map(PRODUCTS)

    summary = summary.sort_values(
        "detection_count", ascending=False
    )

    save_table(summary, "product_contribution.csv")

    figure = px.bar(
        summary,
        x="product_name",
        y="detection_count",
        title="Recorded detections by satellite product",
        labels={
            "product_name": "Satellite product",
            "detection_count": "Recorded detections",
        },
        text="detection_count",
    )

    save_chart(figure, "product_contribution.html")

    return summary


# ---------------------------------------------------------------------
# 2. Temporal distribution
# ---------------------------------------------------------------------

def analyze_temporal_distribution(indexed):
    monthly = (
        indexed.groupby(["month_utc", "source_product"])
        .size()
        .rename("detection_count")
        .reset_index()
    )

    monthly["product_name"] = monthly["source_product"].map(PRODUCTS)

    save_table(monthly, "monthly_detections.csv")

    figure = px.line(
        monthly,
        x="month_utc",
        y="detection_count",
        color="product_name",
        markers=True,
        title="Monthly recorded detections by satellite product",
        labels={
            "month_utc": "UTC month",
            "detection_count": "Recorded detections",
            "product_name": "Satellite product",
        },
    )

    save_chart(figure, "monthly_detections.html")

    seasonal = (
        indexed.groupby(["season", "source_product"])
        .size()
        .rename("detection_count")
        .reset_index()
    )

    seasonal["product_name"] = seasonal["source_product"].map(PRODUCTS)

    seasonal["season"] = pd.Categorical(
        seasonal["season"],
        categories=SEASON_ORDER,
        ordered=True,
    )

    seasonal = seasonal.sort_values(["season", "source_product"])

    save_table(seasonal, "seasonal_detections.csv")

    figure = px.bar(
        seasonal,
        x="season",
        y="detection_count",
        color="product_name",
        barmode="group",
        category_orders={"season": SEASON_ORDER},
        title="Recorded detections by Southern Hemisphere season",
        labels={
            "season": "Season",
            "detection_count": "Recorded detections",
            "product_name": "Satellite product",
        },
    )

    save_chart(figure, "seasonal_detections.html")

    # Daily totals include only dates with at least one recorded detection.
    daily_totals = (
        indexed.groupby("date_utc")
        .size()
        .rename("detection_count")
        .reset_index()
    )

    save_table(daily_totals, "daily_recorded_detections.csv")

    daily_stats = daily_totals["detection_count"].describe().to_frame(
        name="detection_count"
    )

    save_table(daily_stats.reset_index(names="statistic"),
               "daily_detection_statistics.csv")

    return monthly, seasonal, daily_totals


# ---------------------------------------------------------------------
# 3. Spatial distribution
# ---------------------------------------------------------------------

def analyze_spatial_distribution(indexed):
    spatial = (
        indexed.groupby("h3_res7")
        .size()
        .rename("detection_count")
        .reset_index()
    )

    spatial = spatial.sort_values(
        "detection_count", ascending=False
    )

    spatial["latitude"], spatial["longitude"] = zip(
        *spatial["h3_res7"].map(h3.cell_to_latlng)
    )

    spatial["latitude"] = spatial["latitude"].astype(float)
    spatial["longitude"] = spatial["longitude"].astype(float)

    save_table(spatial, "spatial_detection_counts_res7.csv")

    top_cells = spatial.head(100).copy()
    save_table(top_cells, "top_100_h3_cells.csv")

    map_cells = spatial.head(500)

    figure = px.scatter_geo(
        map_cells,
        lat="latitude",
        lon="longitude",
        size="detection_count",
        color="detection_count",
        hover_name="h3_res7",
        hover_data={
            "latitude": ":.4f",
            "longitude": ":.4f",
            "detection_count": True,
        },
        scope="oceania",
        title="Spatial distribution of recorded detections — H3 resolution 7",
        labels={"detection_count": "Recorded detections"},
    )

    save_chart(figure, "spatial_distribution_res7.html")

    spatial_summary = pd.DataFrame(
        [
            {
                "active_h3_res7_cells": len(spatial),
                "total_recorded_detections": len(indexed),
                "mean_detections_per_active_cell": spatial[
                    "detection_count"
                ].mean(),
                "median_detections_per_active_cell": spatial[
                    "detection_count"
                ].median(),
                "maximum_detections_in_one_cell": spatial[
                    "detection_count"
                ].max(),
            }
        ]
    )

    save_table(spatial_summary, "spatial_summary.csv")

    return spatial, spatial_summary


# ---------------------------------------------------------------------
# 4. FRP distribution
# ---------------------------------------------------------------------

def analyze_frp(indexed):
    frp = (
        indexed.groupby("source_product")["frp_mw"]
        .agg(
            record_count="count",
            mean_mw="mean",
            median_mw="median",
            standard_deviation_mw="std",
            minimum_mw="min",
            q25_mw=lambda values: values.quantile(0.25),
            q75_mw=lambda values: values.quantile(0.75),
            q90_mw=lambda values: values.quantile(0.90),
            q95_mw=lambda values: values.quantile(0.95),
            maximum_mw="max",
        )
        .reset_index()
    )

    frp["product_name"] = frp["source_product"].map(PRODUCTS)

    save_table(frp, "frp_statistics_by_product.csv")

    figure = px.box(
        indexed,
        x="source_product",
        y="frp_mw",
        color="source_product",
        points=False,
        title="FRP distribution by satellite product",
        labels={
            "source_product": "Satellite product",
            "frp_mw": "FRP (MW)",
        },
    )

    save_chart(figure, "frp_distribution.html")

    return frp


# ---------------------------------------------------------------------
# 5. Cross-product spatial-temporal co-occurrence
# ---------------------------------------------------------------------

def analyze_product_cooccurrence(daily):
    product_columns = {
        "MODIS_SP": "modis_detection_count",
        "VIIRS_NOAA20_SP": "noaa20_detection_count",
        "VIIRS_SNPP_SP": "snpp_detection_count",
    }

    def identify_combination(row):
        active = [
            product
            for product, column in product_columns.items()
            if row[column] > 0
        ]

        names = [PRODUCTS[product] for product in active]

        return " + ".join(names)

    daily = daily.copy()
    daily["product_combination"] = daily.apply(
        identify_combination,
        axis=1,
    )

    cooccurrence = (
        daily.groupby("product_combination")
        .agg(
            cell_day_count=("h3_res7", "size"),
            distinct_h3_cells=("h3_res7", "nunique"),
            distinct_dates=("date_utc", "nunique"),
            detection_count=("combined_detection_count", "sum"),
        )
        .reset_index()
    )

    cooccurrence["percentage_of_cell_days"] = (
        cooccurrence["cell_day_count"] / len(daily) * 100
    )

    cooccurrence = cooccurrence.sort_values(
        "cell_day_count", ascending=False
    )

    save_table(cooccurrence, "product_cooccurrence.csv")

    figure = px.bar(
        cooccurrence,
        x="product_combination",
        y="cell_day_count",
        title="Satellite product co-occurrence by H3 cell and UTC day",
        labels={
            "product_combination": "Products with recorded detections",
            "cell_day_count": "H3 cell-days",
        },
        text="cell_day_count",
    )

    save_chart(figure, "product_cooccurrence.html")

    return cooccurrence


# ---------------------------------------------------------------------
# 6. Generate Markdown report
# ---------------------------------------------------------------------

def generate_report(
    indexed,
    daily,
    product_summary,
    monthly,
    seasonal,
    daily_totals,
    spatial_summary,
    frp,
    cooccurrence,
):
    start_date = indexed["timestamp_utc"].min().date()
    end_date = indexed["timestamp_utc"].max().date()

    top_month = (
        monthly.groupby("month_utc")["detection_count"]
        .sum()
        .idxmax()
    )

    top_season = (
        seasonal.groupby("season", observed=False)["detection_count"]
        .sum()
        .idxmax()
    )

    top_cell = (
        pd.read_csv(OUTPUT_DIR / "top_100_h3_cells.csv")
        .iloc[0]
    )

    product_lines = "\n".join(
        f"- {row.product_name}: {format_number(row.detection_count)} "
        f"({row.percentage:.2f}%)"
        for row in product_summary.itertuples()
    )

    frp_lines = "\n".join(
        f"- {row.product_name}: mean {row.mean_mw:.2f} MW, "
        f"median {row.median_mw:.2f} MW, "
        f"maximum {row.maximum_mw:.2f} MW"
        for row in frp.itertuples()
    )

    cooccurrence_lines = "\n".join(
        f"- {row.product_combination}: "
        f"{format_number(row.cell_day_count)} cell-days "
        f"({row.percentage_of_cell_days:.2f}%)"
        for row in cooccurrence.itertuples()
    )

    spatial = spatial_summary.iloc[0]

    report = f"""# QORVEX — Victoria 2024 Exploratory Profile

## 1. Dataset scope

- Geographic scope: Victoria, Australia
- First recorded detection: {start_date}
- Last recorded detection: {end_date}
- Spatially indexed detection records: {len(indexed):,}
- Daily H3 resolution-7 activity groups: {len(daily):,}
- Active H3 resolution-7 cells: {int(spatial.active_h3_res7_cells):,}

This report describes recorded FIRMS hotspot detections. It does not
represent a complete record of all fire activity or satellite observation
coverage.

## 2. Satellite product contribution

{product_lines}

## 3. Temporal distribution

- Month with the highest recorded detection count: {top_month}
- Season with the highest recorded detection count: {top_season}
- Dates with at least one recorded detection: {len(daily_totals):,}
- Mean detections per date with recorded detections:
  {daily_totals["detection_count"].mean():.2f}
- Median detections per date with recorded detections:
  {daily_totals["detection_count"].median():.2f}

Monthly and seasonal values are based on UTC acquisition dates.

The seasonal grouping uses Southern Hemisphere seasons:
Summer (December–February), Autumn (March–May),
Winter (June–August), and Spring (September–November).

Dates without a detection record are not treated as confirmed
zero-activity or observed-zero days.

## 4. Spatial distribution

- Active H3 resolution-7 cells: {int(spatial.active_h3_res7_cells):,}
- Mean detections per active cell: {spatial.mean_detections_per_active_cell:.2f}
- Median detections per active cell: {spatial.median_detections_per_active_cell:.2f}
- Maximum detections in one cell: {int(spatial.maximum_detections_in_one_cell):,}
- H3 cell with the highest recorded count: {top_cell["h3_res7"]}

Spatial counts describe the distribution of recorded detections,
not the number of unique fires.

## 5. Fire Radiative Power (FRP)

{frp_lines}

FRP is reported in MW. These statistics are product-specific.
MODIS and VIIRS FRP values should not be assumed to be directly
equivalent merely because they share the same unit.

A sum of recorded FRP values is not a measurement of total energy
released by a unique fire.

## 6. Cross-product spatial-temporal co-occurrence

{cooccurrence_lines}

A cell-day combination means that one or more products recorded
detections within the same H3 resolution-7 cell on the same UTC date.

Co-occurrence does not establish that different satellites observed
the same physical fire.

## 7. Methodological limitations

1. FIRMS hotspot records are detections, not unique fire events.
2. Absence of a detection record does not establish zero fire activity.
3. This dataset does not independently describe valid observation
   coverage for every cell and date.
4. Sensor spatial resolution, overpass timing, detection algorithms,
   and measurement characteristics differ.
5. FRP statistics are kept separate by product.
6. This one-year regional dataset is not sufficient for the planned
   five-year Historical Detection Anomaly baseline.
7. The results are descriptive and do not constitute fire probability,
   severity classification, prediction, or causal explanation.

## 8. Generated outputs

The accompanying CSV tables and interactive HTML charts provide
the detailed results behind this report.
"""

    write_report(report)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    print("=" * 65)
    print("QORVEX — Victoria 2024 Exploratory Data Analysis")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    indexed, daily = load_datasets()

    print("\n[1/5] Product contribution...")
    product_summary = analyze_products(indexed)

    print("\n[2/5] Temporal distribution...")
    monthly, seasonal, daily_totals = analyze_temporal_distribution(
        indexed
    )

    print("\n[3/5] Spatial distribution...")
    _, spatial_summary = analyze_spatial_distribution(indexed)

    print("\n[4/5] FRP distribution...")
    frp = analyze_frp(indexed)

    print("\n[5/5] Cross-product co-occurrence...")
    cooccurrence = analyze_product_cooccurrence(daily)

    print("\nGenerating Markdown report...")

    generate_report(
        indexed,
        daily,
        product_summary,
        monthly,
        seasonal,
        daily_totals,
        spatial_summary,
        frp,
        cooccurrence,
    )

    print("\n" + "=" * 65)
    print("EXPLORATORY PROFILE GENERATED SUCCESSFULLY")
    print("=" * 65)
    print(f"Output directory: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
