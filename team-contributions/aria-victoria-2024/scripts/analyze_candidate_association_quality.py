
from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path(
    r"C:\Users\Asus\data\cross_sensor_candidate_pairs_2024.csv"
)

OUTPUT_DIR = Path(r"C:\Users\Asus\data\candidate_quality_analysis")

MAX_DISTANCE_KM = 5.0
MAX_TIME_DIFFERENCE_MINUTES = 1440.0

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# COLUMN RESOLUTION
# ============================================================

def find_column(df, possible_names, description, required=True):
    """Find a column using a list of possible column names."""

    for name in possible_names:
        if name in df.columns:
            return name

    if required:
        raise ValueError(
            f"Could not find the column for: {description}\n"
            f"Expected one of: {possible_names}\n"
            f"Available columns: {list(df.columns)}"
        )

    return None


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("CROSS-SENSOR CANDIDATE ASSOCIATION QUALITY ANALYSIS")
print("=" * 70)

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE, low_memory=False)

print(f"\nLoaded candidate pairs: {len(df):,}")


# Resolve the important columns.
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
    ["distance_km", "distance", "distance_km_calculated"],
    "Spatial distance"
)

time_diff_col = find_column(
    df,
    [
        "time_diff_minutes",
        "time_difference_minutes",
        "time_difference_min",
        "time_diff_min"
    ],
    "Time difference in minutes",
    required=False
)

sensor_a_col = find_column(
    df,
    [
        "sensor_a",
        "satellite_a",
        "detection_a_satellite",
        "satellite_a_label"
    ],
    "Sensor A",
    required=False
)

sensor_b_col = find_column(
    df,
    [
        "sensor_b",
        "satellite_b",
        "detection_b_satellite",
        "satellite_b_label"
    ],
    "Sensor B",
    required=False
)

datetime_a_col = find_column(
    df,
    [
        "acq_datetime_a",
        "datetime_a",
        "acquisition_datetime_a",
        "timestamp_a"
    ],
    "Detection A acquisition timestamp",
    required=False
)

datetime_b_col = find_column(
    df,
    [
        "acq_datetime_b",
        "datetime_b",
        "acquisition_datetime_b",
        "timestamp_b"
    ],
    "Detection B acquisition timestamp",
    required=False
)


# ============================================================
# NORMALIZE AND VALIDATE
# ============================================================

df[id_a_col] = df[id_a_col].astype("string")
df[id_b_col] = df[id_b_col].astype("string")

df[distance_col] = pd.to_numeric(
    df[distance_col],
    errors="coerce"
)

if time_diff_col is not None:
    df[time_diff_col] = pd.to_numeric(
        df[time_diff_col],
        errors="coerce"
    )

elif datetime_a_col is not None and datetime_b_col is not None:
    datetime_a = pd.to_datetime(
        df[datetime_a_col],
        errors="coerce",
        utc=True
    )

    datetime_b = pd.to_datetime(
        df[datetime_b_col],
        errors="coerce",
        utc=True
    )

    df["time_diff_minutes_calculated"] = (
        (datetime_a - datetime_b).abs().dt.total_seconds() / 60
    )

    time_diff_col = "time_diff_minutes_calculated"

else:
    raise ValueError(
        "Cannot validate time differences. "
        "The CSV needs either a time-difference column or "
        "both acquisition timestamp columns."
    )


# Remove rows without usable detection identities.
missing_ids = (
    df[id_a_col].isna()
    | df[id_b_col].isna()
    | df[id_a_col].str.strip().eq("")
    | df[id_b_col].str.strip().eq("")
)

print(f"Rows with missing detection IDs: {missing_ids.sum():,}")

df = df.loc[~missing_ids].copy()

# Remove rows with invalid spatial or temporal measurements.
invalid_measurements = (
    df[distance_col].isna()
    | df[time_diff_col].isna()
    | (df[distance_col] < 0)
    | (df[time_diff_col] < 0)
)

print(
    "Rows with invalid distance/time measurements: "
    f"{invalid_measurements.sum():,}"
)

df = df.loc[~invalid_measurements].copy()


# ============================================================
# VALIDATE CANDIDATE CONSTRAINTS
# ============================================================

distance_violations = (
    df[distance_col] > MAX_DISTANCE_KM
)

time_violations = (
    df[time_diff_col] > MAX_TIME_DIFFERENCE_MINUTES
)

print("\nCONSTRAINT VALIDATION")
print("-" * 70)

print(
    f"Distance violations (> {MAX_DISTANCE_KM} km): "
    f"{distance_violations.sum():,}"
)

print(
    f"Time violations (> {MAX_TIME_DIFFERENCE_MINUTES} min): "
    f"{time_violations.sum():,}"
)

print(
    f"Maximum observed distance: "
    f"{df[distance_col].max():.4f} km"
)

print(
    f"Maximum observed time difference: "
    f"{df[time_diff_col].max():.2f} minutes"
)

# Keep only rows satisfying the configured candidate constraints.
df = df.loc[
    ~distance_violations & ~time_violations
].copy()


# ============================================================
# DEFINE SATELLITE PAIRS
# ============================================================

if sensor_a_col is not None and sensor_b_col is not None:
    df["satellite_pair"] = (
        df[sensor_a_col].astype(str)
        + " - "
        + df[sensor_b_col].astype(str)
    )
else:
    # If the satellite columns are unavailable, use the IDs'
    # source metadata where possible, or one overall group.
    df["satellite_pair"] = "All candidate pairs"

print(f"\nCandidate pairs retained: {len(df):,}")
print(f"Satellite pair groups: {df['satellite_pair'].nunique():,}")


# ============================================================
# 1. DETECTION PARTICIPATION
# ============================================================

participation_rows = []

for pair_name, group in df.groupby("satellite_pair"):

    unique_a = group[id_a_col].nunique()
    unique_b = group[id_b_col].nunique()

    participation_rows.append({
        "satellite_pair": pair_name,
        "candidate_pairs": len(group),
        "unique_detections_a": unique_a,
        "unique_detections_b": unique_b,
        "total_unique_detections_sides": unique_a + unique_b
    })

participation = pd.DataFrame(participation_rows)

participation.to_csv(
    OUTPUT_DIR / "detection_participation.csv",
    index=False
)


# ============================================================
# 2. MATCHING AMBIGUITY
# ============================================================

ambiguity_rows = []

for pair_name, group in df.groupby("satellite_pair"):

    # Number of candidate partners for each A detection.
    count_a = (
        group.groupby(id_a_col)[id_b_col]
        .nunique()
    )

    # Number of candidate partners for each B detection.
    count_b = (
        group.groupby(id_b_col)[id_a_col]
        .nunique()
    )

    for side, counts in [
        ("A", count_a),
        ("B", count_b)
    ]:

        ambiguity_rows.append({
            "satellite_pair": pair_name,
            "side": side,
            "participating_detections": len(counts),
            "mean_candidate_partners": counts.mean(),
            "median_candidate_partners": counts.median(),
            "maximum_candidate_partners": counts.max(),
            "detections_with_1_candidate": (counts == 1).sum(),
            "detections_with_2_candidates": (counts == 2).sum(),
            "detections_with_3_to_5_candidates": (
                counts.between(3, 5)
            ).sum(),
            "detections_with_more_than_5_candidates": (
                counts > 5
            ).sum()
        })

ambiguity = pd.DataFrame(ambiguity_rows)

ambiguity.to_csv(
    OUTPUT_DIR / "matching_ambiguity.csv",
    index=False
)


# ============================================================
# 3. NEAREST SPATIAL CANDIDATE
# ============================================================

def select_nearest_candidates(group, primary_column, secondary_column):
    """
    Select one candidate for each detection.

    The primary criterion is minimized first.
    The secondary criterion breaks ties.
    """

    ordered = group.sort_values(
        [primary_column, secondary_column],
        ascending=[True, True]
    )

    return ordered.drop_duplicates(
        subset=["source_detection_id"],
        keep="first"
    )


def calculate_nearest_candidates(group, criterion):
    """Calculate nearest candidates from both sides."""

    working = group.copy()

    if criterion == "spatial":
        primary = distance_col
        secondary = time_diff_col

    elif criterion == "temporal":
        primary = time_diff_col
        secondary = distance_col

    else:
        raise ValueError("Unknown criterion.")

    # A -> B
    a_to_b = working.rename(
        columns={
            id_a_col: "source_detection_id",
            id_b_col: "candidate_detection_id"
        }
    )

    nearest_a = select_nearest_candidates(
        a_to_b,
        primary,
        secondary
    )

    nearest_a["source_side"] = "A"

    # B -> A
    b_to_a = working.rename(
        columns={
            id_b_col: "source_detection_id",
            id_a_col: "candidate_detection_id"
        }
    )

    nearest_b = select_nearest_candidates(
        b_to_a,
        primary,
        secondary
    )

    nearest_b["source_side"] = "B"

    result = pd.concat(
        [nearest_a, nearest_b],
        ignore_index=True
    )

    result["selection_criterion"] = criterion

    return result


nearest_spatial_parts = []
nearest_temporal_parts = []

for pair_name, group in df.groupby("satellite_pair"):

    spatial = calculate_nearest_candidates(
        group,
        "spatial"
    )

    temporal = calculate_nearest_candidates(
        group,
        "temporal"
    )

    spatial["satellite_pair"] = pair_name
    temporal["satellite_pair"] = pair_name

    nearest_spatial_parts.append(spatial)
    nearest_temporal_parts.append(temporal)


nearest_spatial = pd.concat(
    nearest_spatial_parts,
    ignore_index=True
)

nearest_temporal = pd.concat(
    nearest_temporal_parts,
    ignore_index=True
)

nearest_spatial.to_csv(
    OUTPUT_DIR / "nearest_spatial_candidates.csv",
    index=False
)

nearest_temporal.to_csv(
    OUTPUT_DIR / "nearest_temporal_candidates.csv",
    index=False
)


# ============================================================
# 4. MUTUAL NEAREST NEIGHBOURS
# ============================================================

def get_mutual_nearest_pairs(nearest):
    """
    A pair is mutual if:
      - A selects B as its nearest candidate.
      - B also selects A as its nearest candidate.

    The test is performed separately for each satellite pair.
    """

    selected_a = nearest.loc[
        nearest["source_side"] == "A",
        ["satellite_pair", "source_detection_id",
         "candidate_detection_id"]
    ].rename(
        columns={
            "source_detection_id": "detection_a_id",
            "candidate_detection_id": "detection_b_id"
        }
    )

    selected_b = nearest.loc[
        nearest["source_side"] == "B",
        ["satellite_pair", "source_detection_id",
         "candidate_detection_id"]
    ].rename(
        columns={
            "source_detection_id": "detection_b_id",
            "candidate_detection_id": "detection_a_id"
        }
    )

    mutual = selected_a.merge(
        selected_b,
        on=[
            "satellite_pair",
            "detection_a_id",
            "detection_b_id"
        ],
        how="inner"
    )

    return mutual.drop_duplicates()


mutual_spatial = get_mutual_nearest_pairs(
    nearest_spatial
)

mutual_temporal = get_mutual_nearest_pairs(
    nearest_temporal
)


# Add original candidate measurements.
candidate_lookup = df[
    [
        "satellite_pair",
        id_a_col,
        id_b_col,
        distance_col,
        time_diff_col
    ]
].drop_duplicates(
    subset=["satellite_pair", id_a_col, id_b_col]
).rename(
    columns={
        id_a_col: "detection_a_id",
        id_b_col: "detection_b_id"
    }
)

mutual_spatial = mutual_spatial.merge(
    candidate_lookup,
    on=[
        "satellite_pair",
        "detection_a_id",
        "detection_b_id"
    ],
    how="left"
)

mutual_temporal = mutual_temporal.merge(
    candidate_lookup,
    on=[
        "satellite_pair",
        "detection_a_id",
        "detection_b_id"
    ],
    how="left"
)

mutual_spatial.to_csv(
    OUTPUT_DIR / "mutual_nearest_spatial_pairs.csv",
    index=False
)

mutual_temporal.to_csv(
    OUTPUT_DIR / "mutual_nearest_temporal_pairs.csv",
    index=False
)


# ============================================================
# 5. MUTUAL NEAREST SUMMARY
# ============================================================

mutual_summary_rows = []

for pair_name, group in df.groupby("satellite_pair"):

    mutual_s = mutual_spatial.loc[
        mutual_spatial["satellite_pair"] == pair_name
    ]

    mutual_t = mutual_temporal.loc[
        mutual_temporal["satellite_pair"] == pair_name
    ]

    mutual_summary_rows.append({
        "satellite_pair": pair_name,
        "candidate_pairs": len(group),
        "mutual_nearest_spatial_pairs": len(mutual_s),
        "mutual_nearest_temporal_pairs": len(mutual_t),
        "spatial_mutual_percentage_of_candidates": (
            len(mutual_s) / len(group) * 100
            if len(group) else 0
        ),
        "temporal_mutual_percentage_of_candidates": (
            len(mutual_t) / len(group) * 100
            if len(group) else 0
        )
    })

mutual_summary = pd.DataFrame(
    mutual_summary_rows
)

mutual_summary.to_csv(
    OUTPUT_DIR / "mutual_nearest_summary.csv",
    index=False
)


# ============================================================
# 6. CANDIDATE DISTANCE AND TIME DISTRIBUTIONS
# ============================================================

distribution_rows = []

for pair_name, group in df.groupby("satellite_pair"):

    distribution_rows.append({
        "satellite_pair": pair_name,
        "candidate_pairs": len(group),

        "distance_median_km": group[distance_col].median(),
        "distance_mean_km": group[distance_col].mean(),
        "distance_90th_percentile_km": (
            group[distance_col].quantile(0.90)
        ),

        "time_median_minutes": group[time_diff_col].median(),
        "time_mean_minutes": group[time_diff_col].mean(),
        "time_90th_percentile_minutes": (
            group[time_diff_col].quantile(0.90)
        )
    })

distribution = pd.DataFrame(distribution_rows)

distribution.to_csv(
    OUTPUT_DIR / "candidate_distance_time_distribution.csv",
    index=False
)


# ============================================================
# 7. FINAL CONSOLE REPORT
# ============================================================

print("\n" + "=" * 70)
print("DETECTION PARTICIPATION")
print("=" * 70)

print(
    participation.to_string(index=False)
)

print("\n" + "=" * 70)
print("MATCHING AMBIGUITY")
print("=" * 70)

print(
    ambiguity.to_string(index=False)
)

print("\n" + "=" * 70)
print("MUTUAL NEAREST-NEIGHBOUR SUMMARY")
print("=" * 70)

print(
    mutual_summary.to_string(index=False)
)

print("\n" + "=" * 70)
print("CANDIDATE DISTANCE AND TIME DISTRIBUTION")
print("=" * 70)

print(
    distribution.to_string(index=False)
)


# ============================================================
# 8. SAVE OVERALL VALIDATION REPORT
# ============================================================

validation = pd.DataFrame([
    {
        "metric": "candidate_pairs_after_cleaning",
        "value": len(df)
    },
    {
        "metric": "unique_detection_ids_A",
        "value": df[id_a_col].nunique()
    },
    {
        "metric": "unique_detection_ids_B",
        "value": df[id_b_col].nunique()
    },
    {
        "metric": "satellite_pair_groups",
        "value": df["satellite_pair"].nunique()
    },
    {
        "metric": "maximum_distance_km",
        "value": df[distance_col].max()
    },
    {
        "metric": "maximum_time_difference_minutes",
        "value": df[time_diff_col].max()
    },
    {
        "metric": "mutual_nearest_spatial_pairs",
        "value": len(mutual_spatial)
    },
    {
        "metric": "mutual_nearest_temporal_pairs",
        "value": len(mutual_temporal)
    }
])

validation.to_csv(
    OUTPUT_DIR / "overall_validation_report.csv",
    index=False
)


# ============================================================
# COMPLETION
# ============================================================

print("\n" + "=" * 70)
print("ANALYSIS COMPLETED")
print("=" * 70)

print(f"\nOutput directory:\n{OUTPUT_DIR}")

print("\nGenerated files:")

for file in sorted(OUTPUT_DIR.glob("*.csv")):
    print(f"  - {file.name}")

print("\nImportant interpretation:")
print(
    "Mutual nearest-neighbour pairs are candidate associations, "
    "not confirmed common fire events."
)

print(
    "Nearest spatial and nearest temporal associations are "
    "different selection strategies."
)

print(
    "All counts represent detection records and candidate pairs, "
    "not unique fires."
)
