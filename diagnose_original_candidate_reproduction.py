from __future__ import annotations
import gc
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent
ORIGINAL_SCRIPT = REPO_ROOT / "scripts" / "analyze_cross_sensor_candidates.py"
CONTROLLED_SCRIPT = REPO_ROOT / "compare_firms_candidate_methods.py"
OUTPUT_DIR = Path(r"C:\Users\Asus\data\original_engine_reproduction_diagnostic")
PAIR_ORDER = [
    ("Aqua", "NOAA20"), ("Aqua", "SNPP"),
    ("Terra", "NOAA20"), ("Terra", "SNPP"),
    ("Aqua", "Terra"), ("SNPP", "NOAA20"),
]
MAX_ORIGINAL_PAIRS_PER_COMPARISON = 5_000_000

def import_script(name: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot find {path}. Put this diagnostic script in the repository root "
            "and check that both source scripts are at the configured paths."
        )
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def make_original_groups(original):
    groups = {}
    for product, sensor in original.PRODUCTS.items():
        data = original.load_product(product, sensor)
        if sensor == "MODIS":
            for satellite in ("Aqua", "Terra"):
                subset = data[
                    data["satellite"].astype(str).str.strip() == satellite
                ].copy()
                subset["sensor_group"] = satellite
                groups[satellite] = subset.reset_index(drop=True)
        else:
            groups[sensor] = data.reset_index(drop=True)
        print(f"Loaded {sensor}: {len(data):,} valid rows")
    return groups

def numpy_pairs_on_same_original_input(controlled, ga, gb):
    a, b = ga.copy().reset_index(drop=True), gb.copy().reset_index(drop=True)
    for frame in (a, b):
        frame["old_x"] = frame["x_km"].to_numpy(dtype=float)
        frame["old_y"] = frame["y_km"].to_numpy(dtype=float)
        frame["timestamp_old"] = frame["timestamp_utc"]
    result = controlled.generate_pairs(
        a, b, "old_x", "old_y", "timestamp_old", "old_time_then_distance"
    )
    ids_a = a["source_record_id"].astype(str).to_numpy()
    ids_b = b["source_record_id"].astype(str).to_numpy()
    width_a = max(1, int(a["source_record_id"].astype(str).str.len().max()))
    width_b = max(1, int(b["source_record_id"].astype(str).str.len().max()))
    pairs = np.empty(len(result["keys"]), dtype=[("a", f"U{width_a}"), ("b", f"U{width_b}")])
    pairs["a"] = ids_a[result["a_idx"]]
    pairs["b"] = ids_b[result["b_idx"]]
    return pairs

def structured_pairs_from_original(results, ga, gb):
    width_a = max(1, int(ga["source_record_id"].astype(str).str.len().max()))
    width_b = max(1, int(gb["source_record_id"].astype(str).str.len().max()))
    pairs = np.empty(len(results), dtype=[("a", f"U{width_a}"), ("b", f"U{width_b}")])
    for i, item in enumerate(results):
        pairs[i] = (str(item["detection_a_id"]), str(item["detection_b_id"]))
    return pairs

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 76)
    print("ORIGINAL CANDIDATE ENGINE REPRODUCTION DIAGNOSTIC")
    print("=" * 76)

    original = import_script("original_candidates", ORIGINAL_SCRIPT)
    controlled = import_script("controlled_candidates", CONTROLLED_SCRIPT)

    if Path(original.DATA_DIR) != Path(controlled.DATA_DIR):
        raise AssertionError("The original and controlled scripts use different data directories.")
    for name, x, y in (
        ("grid size", original.GRID_SIZE_KM, controlled.GRID_SIZE_KM),
        ("maximum distance", original.MAX_DISTANCE_KM, controlled.MAX_DISTANCE_KM),
        ("maximum time (minutes)", original.MAX_TIME_HOURS * 60, controlled.MAX_TIME_DIFFERENCE_MIN),
    ):
        if not np.isclose(x, y):
            raise AssertionError(f"Configuration mismatch for {name}: {x} vs {y}")

    groups = make_original_groups(original)
    summary, samples = [], []

    for sa, sb in PAIR_ORDER:
        pair_name = f"{sa}__{sb}"
        ga, gb = groups[sa], groups[sb]
        print(f"\n{pair_name}: A={len(ga):,}; B={len(gb):,}")

        # Call the original function directly, without modifying it.
        print("  Calling original.compare_groups()...")
        original_results = original.compare_groups(ga, gb)
        if len(original_results) > MAX_ORIGINAL_PAIRS_PER_COMPARISON:
            raise MemoryError(
                f"{pair_name} returned {len(original_results):,} pairs; "
                "the safety ceiling was exceeded."
            )
        original_ids = structured_pairs_from_original(original_results, ga, gb)
        del original_results
        gc.collect()
        original_ids.sort(order=("a", "b"))

        # Run the controlled engine on exactly the same loaded rows.
        print("  Calling controlled.generate_pairs() on the same DataFrames...")
        numpy_ids = numpy_pairs_on_same_original_input(controlled, ga, gb)
        numpy_ids.sort(order=("a", "b"))

        orig_idx = pd.MultiIndex.from_arrays([original_ids["a"], original_ids["b"]])
        numpy_idx = pd.MultiIndex.from_arrays([numpy_ids["a"], numpy_ids["b"]])
        original_only = orig_idx.difference(numpy_idx)
        numpy_only = numpy_idx.difference(orig_idx)
        common = len(orig_idx.intersection(numpy_idx))

        exact = (
            len(original_ids) == len(numpy_ids)
            and len(original_only) == 0
            and len(numpy_only) == 0
        )
        summary.append({
            "pair": pair_name,
            "group_a_rows": len(ga),
            "group_b_rows": len(gb),
            "original_compare_groups_pairs": len(original_ids),
            "controlled_numpy_pairs_same_input": len(numpy_ids),
            "common_pairs": common,
            "original_only_pairs": len(original_only),
            "numpy_only_pairs": len(numpy_only),
            "exact_match": exact,
        })
        print(
            f"  Original={len(original_ids):,} | NumPy={len(numpy_ids):,} | "
            f"Common={common:,} | Original-only={len(original_only):,} | "
            f"NumPy-only={len(numpy_only):,} | Exact={exact}"
        )

        for label, index in (("original_only", original_only), ("numpy_only", numpy_only)):
            for aid, bid in list(index[:100]):
                samples.append({
                    "pair": pair_name,
                    "present_only_in": label,
                    "detection_a_id": str(aid),
                    "detection_b_id": str(bid),
                })

        del original_ids, numpy_ids, orig_idx, numpy_idx, original_only, numpy_only
        gc.collect()

    summary_df = pd.DataFrame(summary)
    summary_path = OUTPUT_DIR / "01_original_vs_numpy_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    sample_path = OUTPUT_DIR / "02_pair_identity_discrepancy_samples.csv"
    pd.DataFrame(samples).to_csv(sample_path, index=False)

    metadata = {
        "original_script": str(ORIGINAL_SCRIPT),
        "controlled_script": str(CONTROLLED_SCRIPT),
        "data_directory": str(original.DATA_DIR),
        "grid_size_km": original.GRID_SIZE_KM,
        "maximum_distance_km": original.MAX_DISTANCE_KM,
        "maximum_time_difference_minutes": original.MAX_TIME_HOURS * 60,
        "method": "Direct original.compare_groups() versus controlled.generate_pairs() on identical original-loader DataFrames.",
        "candidate_pairs_are_confirmed_fire_matches": False,
    }
    metadata_path = OUTPUT_DIR / "00_run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("\n" + "=" * 76)
    print("SUMMARY")
    print("=" * 76)
    print(summary_df.to_string(index=False))
    print(f"\nSaved outputs to: {OUTPUT_DIR}")
    print(f"  {metadata_path.name}")
    print(f"  {summary_path.name}")
    print(f"  {sample_path.name}")
    if summary_df["exact_match"].all():
        print("\nCONCLUSION: The NumPy engine exactly reproduces the original function.")
    else:
        print("\nCONCLUSION: The engines differ on identical original input DataFrames.")

if __name__ == "__main__":
    main()
