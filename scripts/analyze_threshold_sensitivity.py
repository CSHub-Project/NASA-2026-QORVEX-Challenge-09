
from pathlib import Path

import pandas as pd
import numpy as np


# ============================================================
# 1. CONFIGURATION
# ============================================================

INPUT_FILE = Path(
    r"C:\Users\Asus\data\cross_sensor_candidate_pairs_2024.csv"
)

OUTPUT_DIR = Path(
    r"C:\Users\Asus\data\threshold_sensitivity_analysis"
)

DISTANCE_THRESHOLDS_KM = [
    0.5,
    1.0,
    2.0,
    3.0,
    5.0
]

TIME_THRESHOLDS_MINUTES = [
    15,
    30,
    60,
    180,
    360,
    720,
    1440
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. COLUMN RESOLUTION
# ============================================================

def find_column(df, possible_names, description):

    for name in possible_names:
        if name in df.columns:
            return name

    raise ValueError(
        f"Could not find {description}.\n"
        f"Expected one of: {possible_names}\n"
        f"Available columns: {list(df.columns)}"
    )


# ============================================================
# 3. LOAD CANDIDATE PAIRS
# ============================================================

print("=" * 75)
print("THRESHOLD SENSITIVITY ANALYSIS")
print("=" * 75)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}"
    )

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

print(f"\nLoaded candidate pairs: {len(df):,}")


id_a_col = find_column(
    df,
    ["detection_a_id"],
    "Detection A ID"
)

id_b_col = find_column(
    df,
    ["detection_b_id"],
    "Detection B ID"
)

distance_col = find_column(
    df,
    [
        "distance_km",
        "distance",
        "distance_km_calculated"
    ],
    "Distance"
)

time_diff_col = find_column(
    df,
    [
        "time_diff_minutes",
        "time_difference_minutes",
        "time_difference_min",
        "time_diff_min"
    ],
    "Time difference"
)

sensor_a_col = find_column(
    df,
    [
        "sensor_a",
        "satellite_a",
        "detection_a_satellite",
        "satellite_a_label"
    ],
    "Sensor A"
)

sensor_b_col = find_column(
    df,
    [
        "sensor_b",
        "satellite_b",
        "detection_b_satellite",
        "satellite_b_label"
    ],
    "Sensor B"
)


# ============================================================
# 4. NORMALIZE DATA
# ============================================================

df[id_a_col] = df[id_a_col].astype("string")
df[id_b_col] = df[id_b_col].astype("string")

df[distance_col] = pd.to_numeric(
    df[distance_col],
    errors="coerce"
)

df[time_diff_col] = pd.to_numeric(
    df[time_diff_col],
    errors="coerce"
)

df = df.dropna(
    subset=[
        id_a_col,
        id_b_col,
        distance_col,
        time_diff_col
    ]
).copy()

df = df.loc[
    (df[id_a_col].str.strip() != "")
    & (df[id_b_col].str.strip() != "")
    & (df[distance_col] >= 0)
    & (df[time_diff_col] >= 0)
].copy()

df["satellite_pair"] = (
    df[sensor_a_col].astype(str)
    + " - "
    + df[sensor_b_col].astype(str)
)

print(f"Valid candidate pairs: {len(df):,}")

print("\nSatellite combinations:")
print(
    df["satellite_pair"]
    .value_counts()
    .to_string()
)


# ============================================================
# 5. NEAREST-NEIGHBOUR FUNCTION
# ============================================================

def calculate_mutual_nearest(group, primary, secondary):
    """
    Calculate mutual nearest-neighbour pairs.

    A detection selects one candidate by minimizing:
        primary criterion
        secondary criterion

    A pair is mutual if both detections select each other.

    Stable sorting provides deterministic tie handling
    based on the original candidate-pair order.
    """

    # --------------------------------------------------------
    # A selects B
    # --------------------------------------------------------

    a_candidates = group[
        [
            id_a_col,
            id_b_col,
            distance_col,
            time_diff_col
        ]
    ].copy()

    a_candidates = a_candidates.rename(
        columns={
            id_a_col: "source_id",
            id_b_col: "candidate_id"
        }
    )

    a_candidates = a_candidates.sort_values(
        [primary, secondary],
        ascending=[True, True],
        kind="mergesort"
    )

    a_nearest = a_candidates.drop_duplicates(
        subset="source_id",
        keep="first"
    )

    # --------------------------------------------------------
    # B selects A
    # --------------------------------------------------------

    b_candidates = group[
        [
            id_a_col,
            id_b_col,
            distance_col,
            time_diff_col
        ]
    ].copy()

    b_candidates = b_candidates.rename(
        columns={
            id_b_col: "source_id",
            id_a_col: "candidate_id"
        }
    )

    b_candidates = b_candidates.sort_values(
        [primary, secondary],
        ascending=[True, True],
        kind="mergesort"
    )

    b_nearest = b_candidates.drop_duplicates(
        subset="source_id",
        keep="first"
    )

    # --------------------------------------------------------
    # Identify reciprocal selections
    # --------------------------------------------------------

    a_selected = set(
        zip(
            a_nearest["source_id"],
            a_nearest["candidate_id"]
        )
    )

    b_selected = set(
        zip(
            b_nearest["candidate_id"],
            b_nearest["source_id"]
        )
    )

    mutual_pairs = a_selected.intersection(
        b_selected
    )

    return mutual_pairs


# ============================================================
# 6. ANALYZE ONE THRESHOLD COMBINATION
# ============================================================

def analyze_threshold(
    group,
    satellite_pair,
    distance_threshold,
    time_threshold
):

    filtered = group.loc[
        (group[distance_col] <= distance_threshold)
        & (group[time_diff_col] <= time_threshold)
    ].copy()

    candidate_count = len(filtered)

    # Empty-result handling
    if candidate_count == 0:

        return {
            "satellite_pair": satellite_pair,
            "distance_threshold_km": distance_threshold,
            "time_threshold_minutes": time_threshold,
            "candidate_pairs": 0,

            "unique_detections_a": 0,
            "unique_detections_b": 0,

            "mean_candidates_per_a": np.nan,
            "median_candidates_per_a": np.nan,
            "mean_candidates_per_b": np.nan,
            "median_candidates_per_b": np.nan,

            "a_detections_with_multiple_candidates": 0,
            "b_detections_with_multiple_candidates": 0,

            "mutual_spatial_pairs": 0,
            "mutual_temporal_pairs": 0,

            "spatial_mutual_rate_a_pct": np.nan,
            "spatial_mutual_rate_b_pct": np.nan,

            "temporal_mutual_rate_a_pct": np.nan,
            "temporal_mutual_rate_b_pct": np.nan,

            "median_distance_km": np.nan,
            "p90_distance_km": np.nan,

            "median_time_minutes": np.nan,
            "p90_time_minutes": np.nan
        }

    # --------------------------------------------------------
    # Detection participation
    # --------------------------------------------------------

    unique_a = filtered[id_a_col].nunique()
    unique_b = filtered[id_b_col].nunique()

    # --------------------------------------------------------
    # Matching ambiguity
    # --------------------------------------------------------

    counts_a = (
        filtered.groupby(id_a_col)[id_b_col]
        .nunique()
    )

    counts_b = (
        filtered.groupby(id_b_col)[id_a_col]
        .nunique()
    )

    mean_a = counts_a.mean()
    median_a = counts_a.median()

    mean_b = counts_b.mean()
    median_b = counts_b.median()

    multiple_a = (counts_a > 1).sum()
    multiple_b = (counts_b > 1).sum()

    # --------------------------------------------------------
    # Mutual nearest spatial pairs
    # --------------------------------------------------------

    mutual_spatial = calculate_mutual_nearest(
        filtered,
        distance_col,
        time_diff_col
    )

    # --------------------------------------------------------
    # Mutual nearest temporal pairs
    # --------------------------------------------------------

    mutual_temporal = calculate_mutual_nearest(
        filtered,
        time_diff_col,
        distance_col
    )

    # --------------------------------------------------------
    # Detection-level mutual matching rates
    # --------------------------------------------------------

    matched_a_spatial = len(
        {pair[0] for pair in mutual_spatial}
    )

    matched_b_spatial = len(
        {pair[1] for pair in mutual_spatial}
    )

    matched_a_temporal = len(
        {pair[0] for pair in mutual_temporal}
    )

    matched_b_temporal = len(
        {pair[1] for pair in mutual_temporal}
    )

    spatial_rate_a = (
        matched_a_spatial / unique_a * 100
        if unique_a else np.nan
    )

    spatial_rate_b = (
        matched_b_spatial / unique_b * 100
        if unique_b else np.nan
    )

    temporal_rate_a = (
        matched_a_temporal / unique_a * 100
        if unique_a else np.nan
    )

    temporal_rate_b = (
        matched_b_temporal / unique_b * 100
        if unique_b else np.nan
    )

    # --------------------------------------------------------
    # Spatial and temporal distributions
    # --------------------------------------------------------

    return {
        "satellite_pair": satellite_pair,

        "distance_threshold_km": distance_threshold,
        "time_threshold_minutes": time_threshold,

        "candidate_pairs": candidate_count,

        "unique_detections_a": unique_a,
        "unique_detections_b": unique_b,

        "mean_candidates_per_a": mean_a,
        "median_candidates_per_a": median_a,

        "mean_candidates_per_b": mean_b,
        "median_candidates_per_b": median_b,

        "a_detections_with_multiple_candidates": multiple_a,
        "b_detections_with_multiple_candidates": multiple_b,

        "mutual_spatial_pairs": len(mutual_spatial),
        "mutual_temporal_pairs": len(mutual_temporal),

        "spatial_mutual_rate_a_pct": spatial_rate_a,
        "spatial_mutual_rate_b_pct": spatial_rate_b,

        "temporal_mutual_rate_a_pct": temporal_rate_a,
        "temporal_mutual_rate_b_pct": temporal_rate_b,

        "median_distance_km": filtered[distance_col].median(),
        "p90_distance_km": filtered[distance_col].quantile(0.90),

        "median_time_minutes": filtered[time_diff_col].median(),
        "p90_time_minutes": filtered[time_diff_col].quantile(0.90)
    }


# ============================================================
# 7. RUN ALL 35 THRESHOLD COMBINATIONS
# ============================================================

print("\n" + "=" * 75)
print("RUNNING THRESHOLD EXPERIMENTS")
print("=" * 75)

total_experiments = (
    len(DISTANCE_THRESHOLDS_KM)
    * len(TIME_THRESHOLDS_MINUTES)
)

results = []

experiment_number = 0

for satellite_pair, group in df.groupby("satellite_pair"):

    print(f"\nSatellite pair: {satellite_pair}")

    for distance_threshold in DISTANCE_THRESHOLDS_KM:

        for time_threshold in TIME_THRESHOLDS_MINUTES:

            experiment_number += 1

            result = analyze_threshold(
                group,
                satellite_pair,
                distance_threshold,
                time_threshold
            )

            results.append(result)

            print(
                f"  [{experiment_number:03d}] "
                f"Distance <= {distance_threshold:4.1f} km | "
                f"Time <= {time_threshold:4d} min | "
                f"Candidates: {result['candidate_pairs']:,}"
            )


results_df = pd.DataFrame(results)


# ============================================================
# 8. SORT AND SAVE MAIN RESULTS
# ============================================================

results_df = results_df.sort_values(
    [
        "satellite_pair",
        "distance_threshold_km",
        "time_threshold_minutes"
    ]
)

main_output = (
    OUTPUT_DIR
    / "threshold_sensitivity_results.csv"
)

results_df.to_csv(
    main_output,
    index=False
)


# ============================================================
# 9. CREATE PIVOT TABLES
# ============================================================

metrics = [
    "candidate_pairs",
    "unique_detections_a",
    "unique_detections_b",
    "median_candidates_per_a",
    "median_candidates_per_b",
    "mutual_spatial_pairs",
    "mutual_temporal_pairs",
    "spatial_mutual_rate_a_pct",
    "spatial_mutual_rate_b_pct",
    "temporal_mutual_rate_a_pct",
    "temporal_mutual_rate_b_pct"
]

for metric in metrics:

    pivot = results_df.pivot_table(
        index=[
            "satellite_pair",
            "distance_threshold_km"
        ],
        columns="time_threshold_minutes",
        values=metric,
        aggfunc="first"
    )

    pivot.to_csv(
        OUTPUT_DIR / f"pivot_{metric}.csv"
    )


# ============================================================
# 10. PRINT KEY RESULTS
# ============================================================

print("\n" + "=" * 75)
print("THRESHOLD SENSITIVITY ANALYSIS COMPLETED")
print("=" * 75)

print(f"\nExperiments completed: {len(results_df):,}")

print(
    f"Expected experiments: "
    f"{len(df['satellite_pair'].unique()) * total_experiments:,}"
)

print("\nMAIN RESULTS")
print("-" * 75)

display_columns = [
    "satellite_pair",
    "distance_threshold_km",
    "time_threshold_minutes",
    "candidate_pairs",
    "unique_detections_a",
    "unique_detections_b",
    "mutual_spatial_pairs",
    "spatial_mutual_rate_a_pct",
    "spatial_mutual_rate_b_pct"
]

print(
    results_df[display_columns]
    .to_string(index=False)
)


# ============================================================
# 11. SAVE EXPERIMENT METADATA
# ============================================================

metadata = pd.DataFrame([
    {
        "parameter": "input_candidate_pairs",
        "value": len(df)
    },
    {
        "parameter": "satellite_pair_groups",
        "value": df["satellite_pair"].nunique()
    },
    {
        "parameter": "distance_thresholds",
        "value": ", ".join(
            map(str, DISTANCE_THRESHOLDS_KM)
        )
    },
    {
        "parameter": "time_thresholds_minutes",
        "value": ", ".join(
            map(str, TIME_THRESHOLDS_MINUTES)
        )
    },
    {
        "parameter": "threshold_combinations_per_satellite_pair",
        "value": total_experiments
    },
    {
        "parameter": "total_experiments",
        "value": len(results_df)
    },
    {
        "parameter": "nearest_spatial_definition",
        "value": "Minimize distance, then time difference"
    },
    {
        "parameter": "nearest_temporal_definition",
        "value": "Minimize time difference, then distance"
    },
    {
        "parameter": "mutual_nearest_definition",
        "value": "Both detections select each other"
    }
])

metadata.to_csv(
    OUTPUT_DIR / "experiment_metadata.csv",
    index=False
)


# ============================================================
# 12. COMPLETION
# ============================================================

print("\n" + "=" * 75)
print("OUTPUT FILES")
print("=" * 75)

for file in sorted(OUTPUT_DIR.glob("*.csv")):
    print(f"  {file.name}")

print("\nOutput directory:")
print(OUTPUT_DIR)

print("\nINTERPRETATION REMINDER")
print("-" * 75)

print(
    "Mutual nearest-neighbour pairs are candidate associations, "
    "not confirmed common fire events."
)

print(
    "Detection-level mutual matching rates describe reciprocal "
    "candidate selection among participating detections."
)

print(
    "Higher matching rates do not automatically imply higher "
    "matching accuracy."
)

print(
    "Threshold selection requires balancing ambiguity, spatial "
    "proximity, temporal proximity, and detection coverage."
)
