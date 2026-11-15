from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path
import json

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")
OUTPUT_DIR = Path(r"C:\Users\Asus\data\controlled_candidate_comparison")

GRID_SIZE_KM = 5.0
MAX_DISTANCE_KM = 5.0
MAX_TIME_DIFFERENCE_MIN = 1440.0
EARTH_RADIUS_KM = 6371.0088
SAMPLE_LIMIT_PER_DIRECTION = 1000

PRODUCTS = {
    "MODIS_SP": "MODIS",
    "VIIRS_SNPP_SP": "SNPP",
    "VIIRS_NOAA20_SP": "NOAA20",
}

SOURCE_PAIRS = [
    ("Aqua", "NOAA20"),
    ("Aqua", "SNPP"),
    ("Terra", "NOAA20"),
    ("Terra", "SNPP"),
    ("Aqua", "Terra"),
    ("SNPP", "NOAA20"),
]

REQUIRED_COLUMNS = [
    "latitude", "longitude", "acq_date", "acq_time", "satellite"
]


# ============================================================
# LOAD ONCE; PRESERVE A COMMON SOURCE-RECORD ID
# ============================================================

def load_raw_data() -> pd.DataFrame:
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found directly in {DATA_DIR}")

    frames: list[pd.DataFrame] = []
    for number, path in enumerate(files, start=1):
        product = next((p for p in PRODUCTS if p in path.name), None)
        if product is None:
            continue

        frame = pd.read_csv(path)
        missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
        if missing:
            raise ValueError(f"{path.name} is missing required columns: {missing}")

        # CSV header is line 1, so first data record is row 2.
        frame["source_record_id"] = [
            f"{path.name}::row={row_number}"
            for row_number in range(2, len(frame) + 2)
        ]
        frame["source_file"] = path.name
        frame["product"] = product
        frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
        frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
        frames.append(frame)
        print(f"Loaded [{number}/{len(files)}] {path.name}: {len(frame):,} rows")

    if not frames:
        raise ValueError("No recognized FIRMS product files were loaded.")

    data = pd.concat(frames, ignore_index=True)
    if not data["source_record_id"].is_unique:
        raise AssertionError("Source-record IDs are not unique.")
    data = data.reset_index(drop=True)
    data["_record_idx"] = np.arange(len(data), dtype=np.int64)
    return data


# ============================================================
# REPRODUCE THE TWO TIMESTAMP PARSERS INDEPENDENTLY
# ============================================================

def add_timestamp_variants(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    # Older script: stringify, remove a trailing .0, zfill, then HH:MM.
    old_time_text = (
        data["acq_time"].astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(4)
    )
    old_timestamp_text = (
        data["acq_date"].astype(str) + " "
        + old_time_text.str[:2] + ":" + old_time_text.str[2:4]
    )
    data["timestamp_old"] = pd.to_datetime(
        old_timestamp_text,
        format="%Y-%m-%d %H:%M",
        errors="coerce",
        utc=True,
    )

    # Newer script: numeric validation, integer conversion, HHMM parsing.
    numeric_time = pd.to_numeric(data["acq_time"], errors="coerce")
    valid_numeric_time = (
        numeric_time.notna()
        & numeric_time.ge(0)
        & numeric_time.le(2359)
        & numeric_time.mod(100).lt(60)
    )
    new_time_text = (
        numeric_time.fillna(-1).astype(int).astype(str).str.zfill(4)
    )
    new_timestamp_text = (
        data["acq_date"].astype(str).str.strip() + " " + new_time_text
    )
    data["timestamp_new"] = pd.to_datetime(
        new_timestamp_text,
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True,
    )
    data["valid_new_time"] = valid_numeric_time & data["timestamp_new"].notna()
    return data


# ============================================================
# REPRODUCE THE TWO SATELLITE CLASSIFIERS
# ============================================================

def add_source_variants(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    # Older script: MODIS satellite must equal Aqua/Terra after strip.
    satellite_text = data["satellite"].astype(str).str.strip()
    old_source = np.where(
        data["product"].eq("MODIS_SP") & satellite_text.eq("Aqua"), "Aqua",
        np.where(
            data["product"].eq("MODIS_SP") & satellite_text.eq("Terra"), "Terra",
            np.where(data["product"].eq("VIIRS_SNPP_SP"), "SNPP",
                     np.where(data["product"].eq("VIIRS_NOAA20_SP"), "NOAA20", "UNKNOWN"))
        )
    )
    data["source_old"] = old_source

    # Newer script: case-insensitive substring match for MODIS satellite field.
    sat_lower = data["satellite"].astype(str).str.strip().str.lower()
    new_source = np.where(
        data["product"].eq("VIIRS_SNPP_SP"), "SNPP",
        np.where(
            data["product"].eq("VIIRS_NOAA20_SP"), "NOAA20",
            np.where(
                sat_lower.str.contains("aqua", na=False), "Aqua",
                np.where(sat_lower.str.contains("terra", na=False), "Terra", "UNKNOWN")
            )
        )
    )
    data["source_new"] = new_source
    return data


# ============================================================
# REPRODUCE THE TWO PROJECTIONS
# ============================================================

def add_projection_variants(
    data: pd.DataFrame, new_projection_mask: pd.Series
) -> tuple[pd.DataFrame, dict]:
    data = data.copy()

    # Older script: fixed reference latitude, uncentred coordinates.
    reference_latitude = -36.5
    data["old_x"] = (
        data["longitude"] * 111.320
        * np.cos(np.radians(reference_latitude))
    )
    data["old_y"] = data["latitude"] * 110.574

    # Newer script: equirectangular projection centred on data mean.
    projection_rows = data.loc[new_projection_mask]
    if projection_rows.empty:
        raise ValueError("No valid rows available for the newer projection reference.")
    mean_latitude = float(projection_rows["latitude"].mean())
    mean_longitude = float(projection_rows["longitude"].mean())
    lat0_rad = np.radians(mean_latitude)
    data["new_x"] = (
        EARTH_RADIUS_KM
        * np.radians(data["longitude"] - mean_longitude)
        * np.cos(lat0_rad)
    )
    data["new_y"] = (
        EARTH_RADIUS_KM
        * np.radians(data["latitude"] - mean_latitude)
    )

    metadata = {
        "old_reference_latitude": reference_latitude,
        "new_reference_latitude_mean": mean_latitude,
        "new_reference_longitude_mean": mean_longitude,
    }
    return data, metadata


# ============================================================
# COMMON SPATIAL-HASH CANDIDATE ENGINE
# Each mode uses its own coordinates and timestamps, but the
# same source records and same grid/filter thresholds.
# ============================================================

def generate_pairs(
    data_a: pd.DataFrame,
    data_b: pd.DataFrame,
    x_col: str,
    y_col: str,
    time_col: str,
    filter_order: str,
) -> dict[str, np.ndarray]:
    a = data_a.reset_index(drop=True)
    b = data_b.reset_index(drop=True)

    bx = b[x_col].to_numpy(dtype=float)
    by = b[y_col].to_numpy(dtype=float)
    ax = a[x_col].to_numpy(dtype=float)
    ay = a[y_col].to_numpy(dtype=float)
    # Explicitly convert timestamps to nanosecond resolution
    # before converting their underlying values to integers.
    bt = (
        b[time_col]
        .dt.as_unit("ns")
        .astype("int64")
        .to_numpy(dtype=np.int64)
    ) / 1e9

    at = (
        a[time_col]
        .dt.as_unit("ns")
        .astype("int64")
        .to_numpy(dtype=np.int64)
    ) / 1e9

    # Match the 5 km grid and surrounding 3x3 cells used by both scripts.
    spatial_hash: dict[tuple[int, int], list[int]] = defaultdict(list)
    for j in range(len(b)):
        cell = (int(np.floor(bx[j] / GRID_SIZE_KM)),
                int(np.floor(by[j] / GRID_SIZE_KM)))
        spatial_hash[cell].append(j)

    a_indices: list[np.ndarray] = []
    b_indices: list[np.ndarray] = []
    distances_all: list[np.ndarray] = []
    times_all: list[np.ndarray] = []

    max_seconds = MAX_TIME_DIFFERENCE_MIN * 60.0
    max_distance_squared = MAX_DISTANCE_KM ** 2

    for i in range(len(a)):
        gx = int(np.floor(ax[i] / GRID_SIZE_KM))
        gy = int(np.floor(ay[i] / GRID_SIZE_KM))
        chunks = [
            spatial_hash[(gx + dx, gy + dy)]
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (gx + dx, gy + dy) in spatial_hash
        ]
        if not chunks:
            continue
        candidate_indices = np.fromiter(
            (j for chunk in chunks for j in chunk), dtype=np.int64
        )

        if filter_order == "old_time_then_distance":
            time_seconds = np.abs(bt[candidate_indices] - at[i])
            temporal_mask = time_seconds <= max_seconds
            candidate_indices = candidate_indices[temporal_mask]
            time_seconds = time_seconds[temporal_mask]
            if candidate_indices.size == 0:
                continue

            dx = bx[candidate_indices] - ax[i]
            dy = by[candidate_indices] - ay[i]
            distance_squared = dx * dx + dy * dy
            spatial_mask = distance_squared <= max_distance_squared
            candidate_indices = candidate_indices[spatial_mask]
            time_seconds = time_seconds[spatial_mask]
            distance_squared = distance_squared[spatial_mask]
        elif filter_order == "new_distance_then_time":
            dx = bx[candidate_indices] - ax[i]
            dy = by[candidate_indices] - ay[i]
            distance_squared = dx * dx + dy * dy
            spatial_mask = distance_squared <= max_distance_squared
            candidate_indices = candidate_indices[spatial_mask]
            distance_squared = distance_squared[spatial_mask]
            if candidate_indices.size == 0:
                continue

            time_seconds = np.abs(bt[candidate_indices] - at[i])
            temporal_mask = time_seconds <= max_seconds
            candidate_indices = candidate_indices[temporal_mask]
            distance_squared = distance_squared[temporal_mask]
            time_seconds = time_seconds[temporal_mask]
        else:
            raise ValueError(f"Unknown filter order: {filter_order}")

        if candidate_indices.size == 0:
            continue

        a_indices.append(np.full(candidate_indices.size, i, dtype=np.int64))
        b_indices.append(candidate_indices)
        distances_all.append(np.sqrt(distance_squared))
        times_all.append(time_seconds / 60.0)

    if not a_indices:
        empty_i = np.array([], dtype=np.int64)
        empty_f = np.array([], dtype=float)
        return {"keys": empty_i, "a_idx": empty_i, "b_idx": empty_i,
                "distances": empty_f, "times": empty_f}

    ai = np.concatenate(a_indices)
    bi = np.concatenate(b_indices)
    distances = np.concatenate(distances_all)
    times = np.concatenate(times_all)

    # Compact, collision-free key for a pair of row indices in these two groups.
    keys = ai * np.int64(len(b)) + bi
    order = np.argsort(keys)
    keys = keys[order]
    if keys.size > 1 and np.any(keys[1:] == keys[:-1]):
        raise AssertionError("Duplicate candidate pair keys generated.")

    return {
        "keys": keys,
        "a_idx": ai[order],
        "b_idx": bi[order],
        "distances": distances[order],
        "times": times[order],
    }


def compare_candidate_sets(old: dict, new: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    common = np.intersect1d(old["keys"], new["keys"], assume_unique=True)
    old_only = np.setdiff1d(old["keys"], new["keys"], assume_unique=True)
    new_only = np.setdiff1d(new["keys"], old["keys"], assume_unique=True)
    return common, old_only, new_only


def candidate_sample(
    keys: np.ndarray,
    method: dict,
    a: pd.DataFrame,
    b: pd.DataFrame,
    method_name: str,
    pair_name: str,
    limit: int,
) -> list[dict]:
    if keys.size == 0:
        return []
    sample_keys = keys[:limit]
    positions = np.searchsorted(method["keys"], sample_keys)
    rows: list[dict] = []
    for key, pos in zip(sample_keys, positions):
        ai = int(method["a_idx"][pos])
        bi = int(method["b_idx"][pos])
        rows.append({
            "pair": pair_name,
            "present_only_in": method_name,
            "detection_a_id": a.iloc[ai]["source_record_id"],
            "detection_b_id": b.iloc[bi]["source_record_id"],
            "distance_km_in_that_method": float(method["distances"][pos]),
            "time_difference_min_in_that_method": float(method["times"][pos]),
        })
    return rows


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("CONTROLLED FIRMS CANDIDATE-METHOD COMPARISON")
    print("=" * 78)
    print(f"Input directory: {DATA_DIR}")

    data = load_raw_data()
    data = add_timestamp_variants(data)

    coordinate_valid = (
        data["latitude"].between(-90, 90)
        & data["longitude"].between(-180, 180)
    )
    data = data.loc[coordinate_valid].copy()
    data = add_source_variants(data)

    # Retain rows each implementation would accept for its own run.
    old_valid = data["timestamp_old"].notna() & data["source_old"].ne("UNKNOWN")
    new_valid = data["valid_new_time"] & data["source_new"].ne("UNKNOWN")
    data, projection_metadata = add_projection_variants(data, new_valid)

    old_data = data.loc[old_valid].copy()
    new_data = data.loc[new_valid].copy()

    # Reconciliation by original source-record ID.
    old_ids = set(old_data["source_record_id"])
    new_ids = set(new_data["source_record_id"])
    common_ids = old_ids & new_ids
    old_only_ids = old_ids - new_ids
    new_only_ids = new_ids - old_ids

    common = data[data["source_record_id"].isin(common_ids)].copy()
    timestamp_mismatch = common["timestamp_old"].ne(common["timestamp_new"])
    source_mismatch = common["source_old"].ne(common["source_new"])

    input_reconciliation = pd.DataFrame([{
        "raw_rows_after_coordinate_filter": len(data),
        "old_valid_rows": len(old_data),
        "new_valid_rows": len(new_data),
        "common_valid_source_records": len(common_ids),
        "valid_only_old": len(old_only_ids),
        "valid_only_new": len(new_only_ids),
        "timestamp_mismatches_among_common": int(timestamp_mismatch.sum()),
        "source_classification_mismatches_among_common": int(source_mismatch.sum()),
        "old_timestamp_invalid_rows": int(data["timestamp_old"].isna().sum()),
        "new_timestamp_invalid_rows": int((~data["valid_new_time"]).sum()),
    }])
    input_reconciliation.to_csv(OUTPUT_DIR / "01_input_reconciliation.csv", index=False)

    # Save record-level discrepancies, if any.
    discrepancy_mask = (
        data["timestamp_old"].isna()
        | data["timestamp_new"].isna()
        | data["timestamp_old"].ne(data["timestamp_new"])
        | data["source_old"].ne(data["source_new"])
    )
    discrepancy_cols = [
        "source_record_id", "source_file", "product", "satellite", "acq_date", "acq_time",
        "timestamp_old", "timestamp_new", "valid_new_time", "source_old", "source_new",
    ]
    data.loc[discrepancy_mask, discrepancy_cols].to_csv(
        OUTPUT_DIR / "02_input_record_discrepancies.csv", index=False
    )

    print("\nINPUT RECONCILIATION")
    print(input_reconciliation.to_string(index=False))
    print("\nProjection parameters:")
    print(json.dumps(projection_metadata, indent=2))

    summary_rows: list[dict] = []
    sample_rows: list[dict] = []
    metric_rows: list[dict] = []

    for source_a, source_b in SOURCE_PAIRS:
        pair_name = f"{source_a}__{source_b}"
        print(f"\nComparing {pair_name}...")

        a_old = old_data.loc[old_data["source_old"].eq(source_a)].copy().reset_index(drop=True)
        b_old = old_data.loc[old_data["source_old"].eq(source_b)].copy().reset_index(drop=True)
        a_new = new_data.loc[new_data["source_new"].eq(source_a)].copy().reset_index(drop=True)
        b_new = new_data.loc[new_data["source_new"].eq(source_b)].copy().reset_index(drop=True)

        old_candidates = generate_pairs(
            a_old, b_old, "old_x", "old_y", "timestamp_old", "old_time_then_distance"
        )
        new_candidates = generate_pairs(
            a_new, b_new, "new_x", "new_y", "timestamp_new", "new_distance_then_time"
        )

        # Convert each method's local group indices to stable global integer IDs.
        # This avoids building millions of Python string-pair objects in memory.
        old_global_a = a_old.iloc[old_candidates["a_idx"]]["_record_idx"].to_numpy(dtype=np.int64)
        old_global_b = b_old.iloc[old_candidates["b_idx"]]["_record_idx"].to_numpy(dtype=np.int64)
        new_global_a = a_new.iloc[new_candidates["a_idx"]]["_record_idx"].to_numpy(dtype=np.int64)
        new_global_b = b_new.iloc[new_candidates["b_idx"]]["_record_idx"].to_numpy(dtype=np.int64)
        record_count = len(data)
        old_keys = old_global_a * np.int64(record_count) + old_global_b
        new_keys = new_global_a * np.int64(record_count) + new_global_b

        old_order = np.argsort(old_keys)
        new_order = np.argsort(new_keys)
        old_keys = old_keys[old_order]
        new_keys = new_keys[new_order]
        old_distances = old_candidates["distances"][old_order]
        new_distances = new_candidates["distances"][new_order]
        old_times = old_candidates["times"][old_order]
        new_times = new_candidates["times"][new_order]

        if old_keys.size > 1 and np.any(old_keys[1:] == old_keys[:-1]):
            raise AssertionError("Older method generated duplicate stable pairs.")
        if new_keys.size > 1 and np.any(new_keys[1:] == new_keys[:-1]):
            raise AssertionError("Newer method generated duplicate stable pairs.")

        common_keys = np.intersect1d(old_keys, new_keys, assume_unique=True)
        old_only_keys = np.setdiff1d(old_keys, new_keys, assume_unique=True)
        new_only_keys = np.setdiff1d(new_keys, old_keys, assume_unique=True)

        old_count = int(old_keys.size)
        new_count = int(new_keys.size)
        common_count = int(common_keys.size)
        union_count = old_count + new_count - common_count

        summary_rows.append({
            "pair": pair_name,
            "old_candidates": old_count,
            "new_candidates": new_count,
            "common_candidates": common_count,
            "old_only_candidates": int(old_only_keys.size),
            "new_only_candidates": int(new_only_keys.size),
            "jaccard_similarity": (common_count / union_count) if union_count else 1.0,
            "old_group_a_rows": len(a_old),
            "old_group_b_rows": len(b_old),
            "new_group_a_rows": len(a_new),
            "new_group_b_rows": len(b_new),
        })

        print(
            f"  old={old_count:,} | new={new_count:,} | common={common_count:,} "
            f"| old-only={old_only_keys.size:,} | new-only={new_only_keys.size:,}"
        )

        # Save a bounded sample of pairs exclusive to each implementation.
        for method_name, only_keys, method_keys, method_distances, method_times in [
            ("older_method", old_only_keys, old_keys, old_distances, old_times),
            ("newer_method", new_only_keys, new_keys, new_distances, new_times),
        ]:
            sample_keys = only_keys[:SAMPLE_LIMIT_PER_DIRECTION]
            positions = np.searchsorted(method_keys, sample_keys)
            for key, pos in zip(sample_keys, positions):
                global_a = int(key // record_count)
                global_b = int(key % record_count)
                sample_rows.append({
                    "pair": pair_name,
                    "present_only_in": method_name,
                    "detection_a_id": data.iloc[global_a]["source_record_id"],
                    "detection_b_id": data.iloc[global_b]["source_record_id"],
                    "distance_km": float(method_distances[pos]),
                    "time_difference_min": float(method_times[pos]),
                })

        # Compare distances and time differences for exactly the same pairs.
        if common_count:
            old_common_pos = np.searchsorted(old_keys, common_keys)
            new_common_pos = np.searchsorted(new_keys, common_keys)
            distance_abs_diff = np.abs(
                old_distances[old_common_pos] - new_distances[new_common_pos]
            )
            time_abs_diff = np.abs(
                old_times[old_common_pos] - new_times[new_common_pos]
            )
            metric_rows.append({
                "pair": pair_name,
                "common_pairs": common_count,
                "max_absolute_distance_difference_km": float(distance_abs_diff.max()),
                "median_absolute_distance_difference_km": float(np.median(distance_abs_diff)),
                "max_absolute_time_difference_min": float(time_abs_diff.max()),
                "median_absolute_time_difference_min": float(np.median(time_abs_diff)),
            })
        else:
            metric_rows.append({
                "pair": pair_name,
                "common_pairs": 0,
                "max_absolute_distance_difference_km": np.nan,
                "median_absolute_distance_difference_km": np.nan,
                "max_absolute_time_difference_min": np.nan,
                "median_absolute_time_difference_min": np.nan,
            })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUTPUT_DIR / "03_candidate_set_reconciliation.csv", index=False)
    pd.DataFrame(sample_rows).to_csv(OUTPUT_DIR / "04_exclusive_candidate_samples.csv", index=False)
    pd.DataFrame(metric_rows).to_csv(OUTPUT_DIR / "05_common_pair_metric_comparison.csv", index=False)

    metadata = {
        "data_directory": str(DATA_DIR),
        "output_directory": str(OUTPUT_DIR),
        "grid_size_km": GRID_SIZE_KM,
        "maximum_distance_km": MAX_DISTANCE_KM,
        "maximum_time_difference_minutes": MAX_TIME_DIFFERENCE_MIN,
        "sample_limit_per_direction_per_pair": SAMPLE_LIMIT_PER_DIRECTION,
        "method_reproductions": {
            "older": "fixed-latitude projection; older string timestamp parser; temporal filter then distance filter; 5 km spatial hash and 3x3 neighbours",
            "newer": "mean-centred equirectangular projection; newer numeric HHMM timestamp parser; distance filter then temporal filter; 5 km spatial hash and 3x3 neighbours",
        },
        "note": "Candidate pairs are spatial-temporal candidates, not confirmed same-fire matches.",
    }
    (OUTPUT_DIR / "00_run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 78)
    print("FINAL RECONCILIATION")
    print("=" * 78)
    print(summary_df.to_string(index=False))
    print(f"\nOutputs saved to: {OUTPUT_DIR}")
    for path in sorted(OUTPUT_DIR.iterdir()):
        print(f"  {path.name} ({path.stat().st_size:,} bytes)")
    print("\nCompleted.")


if __name__ == "__main__":
    main()
