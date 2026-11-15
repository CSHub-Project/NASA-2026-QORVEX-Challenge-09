
from pathlib import Path
import hashlib
import pandas as pd

# ============================================================
# 1. CONFIGURATION
# ============================================================

DATA_DIR = Path(r"C:\Users\Asus\data\firms_2024_raw")

OUTPUT_DIR = Path(
    r"C:\Users\Asus\data\source_data_equivalence_audit"
)

PRODUCTS = [
    "MODIS_SP",
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
]

REQUIRED_COLUMNS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
]

HASH_CHUNK_SIZE = 1024 * 1024


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def product_for_name(filename):
    for product in PRODUCTS:
        if product in filename:
            return product
    return None


def sha256_file(path):
    """Calculate SHA-256 without loading the entire file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(HASH_CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def inspect_csv(path):
    """Inspect one FIRMS CSV file."""

    try:
        header = pd.read_csv(path, nrows=0)
        columns = list(header.columns)

        missing_columns = [
            col for col in REQUIRED_COLUMNS
            if col not in columns
        ]

        if missing_columns:
            return {
                "file_name": path.name,
                "relative_path": str(path.relative_to(DATA_DIR)),
                "product": product_for_name(path.name),
                "size_bytes": path.stat().st_size,
                "row_count": None,
                "valid_coordinate_rows": None,
                "invalid_coordinate_rows": None,
                "valid_timestamp_rows": None,
                "invalid_timestamp_rows": None,
                "missing_required_columns": ";".join(
                    missing_columns
                ),
                "sha256": sha256_file(path),
                "error": "",
            }

        data = pd.read_csv(
            path,
            usecols=REQUIRED_COLUMNS,
            low_memory=False
        )

        row_count = len(data)

        # Coordinate validation
        latitude = pd.to_numeric(
            data["latitude"],
            errors="coerce"
        )

        longitude = pd.to_numeric(
            data["longitude"],
            errors="coerce"
        )

        valid_coordinates = (
            latitude.between(-90, 90)
            & longitude.between(-180, 180)
        )

        # Acquisition-time validation
        acq_time = pd.to_numeric(
            data["acq_time"],
            errors="coerce"
        )

        valid_time_numeric = (
            acq_time.notna()
            & (acq_time >= 0)
            & (acq_time <= 2359)
            & (acq_time.mod(100) < 60)
        )

        time_string = (
            acq_time.fillna(-1)
            .astype(int)
            .astype(str)
            .str.zfill(4)
        )

        timestamp_text = (
            data["acq_date"].astype(str).str.strip()
            + " "
            + time_string
        )

        parsed_timestamp = pd.to_datetime(
            timestamp_text,
            format="%Y-%m-%d %H%M",
            errors="coerce",
            utc=True
        )

        valid_timestamps = (
            valid_time_numeric
            & parsed_timestamp.notna()
        )

        return {
            "file_name": path.name,
            "relative_path": str(path.relative_to(DATA_DIR)),
            "product": product_for_name(path.name),
            "size_bytes": path.stat().st_size,
            "row_count": row_count,
            "valid_coordinate_rows": int(
                valid_coordinates.sum()
            ),
            "invalid_coordinate_rows": int(
                (~valid_coordinates).sum()
            ),
            "valid_timestamp_rows": int(
                valid_timestamps.sum()
            ),
            "invalid_timestamp_rows": int(
                (~valid_timestamps).sum()
            ),
            "missing_required_columns": "",
            "sha256": sha256_file(path),
            "error": "",
        }

    except Exception as exc:

        return {
            "file_name": path.name,
            "relative_path": str(path),
            "product": product_for_name(path.name),
            "size_bytes": (
                path.stat().st_size
                if path.exists()
                else None
            ),
            "row_count": None,
            "valid_coordinate_rows": None,
            "invalid_coordinate_rows": None,
            "valid_timestamp_rows": None,
            "invalid_timestamp_rows": None,
            "missing_required_columns": "",
            "sha256": "",
            "error": repr(exc),
        }


# ============================================================
# 3. MAIN AUDIT
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Data directory not found: {DATA_DIR}"
        )

    print("=" * 78)
    print("FIRMS SOURCE-DATA EQUIVALENCE AUDIT")
    print("=" * 78)

    # Older script: non-recursive discovery
    older_files = sorted(
        path
        for product in PRODUCTS
        for path in DATA_DIR.glob(
            f"{product}_*.csv"
        )
    )

    # Newer script: recursive discovery
    newer_files = sorted(
        path
        for path in DATA_DIR.rglob("*.csv")
        if product_for_name(path.name) is not None
    )

    old_paths = {
        str(path.resolve())
        for path in older_files
    }

    new_paths = {
        str(path.resolve())
        for path in newer_files
    }

    only_old = sorted(old_paths - new_paths)
    only_new = sorted(new_paths - old_paths)
    common = sorted(old_paths & new_paths)

    print(
        f"\nOlder glob() discovery: {len(old_paths):,}"
    )

    print(
        f"Newer rglob() discovery: {len(new_paths):,}"
    )

    print(f"Common files: {len(common):,}")
    print(f"Only older: {len(only_old):,}")
    print(f"Only newer: {len(only_new):,}")

    # Inspect union of discovered files
    path_lookup = {
        str(path.resolve()): path
        for path in older_files + newer_files
    }

    all_paths = sorted(
        old_paths | new_paths
    )

    records = []

    for index, path_string in enumerate(
        all_paths,
        start=1
    ):

        path = path_lookup[path_string]

        print(
            f"[{index}/{len(all_paths)}] "
            f"Inspecting {path}"
        )

        record = inspect_csv(path)

        record["found_by_older_glob"] = (
            path_string in old_paths
        )

        record["found_by_newer_rglob"] = (
            path_string in new_paths
        )

        records.append(record)

    files_df = pd.DataFrame(records)

    files_df.to_csv(
        OUTPUT_DIR / "01_file_inventory.csv",
        index=False
    )

    # ========================================================
    # 4. DISCOVERY DIFFERENCES
    # ========================================================

    difference_rows = []

    for path_string in only_old:

        difference_rows.append({
            "discovery_difference": "only_older_glob",
            "absolute_path": path_string,
            "file_name": Path(path_string).name,
        })

    for path_string in only_new:

        difference_rows.append({
            "discovery_difference": "only_newer_rglob",
            "absolute_path": path_string,
            "file_name": Path(path_string).name,
        })

    pd.DataFrame(
        difference_rows,
        columns=[
            "discovery_difference",
            "absolute_path",
            "file_name"
        ]
    ).to_csv(
        OUTPUT_DIR / "02_discovery_differences.csv",
        index=False
    )

    # ========================================================
    # 5. PRODUCT-LEVEL TOTALS
    # ========================================================

    product_rows = []

    for product in PRODUCTS:

        subset = files_df[
            files_df["product"] == product
        ]

        for discovery_column, label in [
            ("found_by_older_glob", "older_glob"),
            ("found_by_newer_rglob", "newer_rglob"),
        ]:

            selected = subset[
                subset[discovery_column] == True
            ]

            product_rows.append({
                "product": product,
                "discovery_method": label,
                "file_count": len(selected),

                "total_rows": (
                    int(selected["row_count"].sum())
                    if selected["row_count"].notna().all()
                    else None
                ),

                "total_valid_coordinate_rows": (
                    int(
                        selected[
                            "valid_coordinate_rows"
                        ].sum()
                    )
                    if selected[
                        "valid_coordinate_rows"
                    ].notna().all()
                    else None
                ),

                "total_valid_timestamp_rows": (
                    int(
                        selected[
                            "valid_timestamp_rows"
                        ].sum()
                    )
                    if selected[
                        "valid_timestamp_rows"
                    ].notna().all()
                    else None
                ),
            })

    pd.DataFrame(product_rows).to_csv(
        OUTPUT_DIR / "03_product_totals_by_discovery.csv",
        index=False
    )

    # ========================================================
    # 6. IDENTICAL FILE CONTENTS
    # ========================================================

    valid_hashes = files_df[
        files_df["sha256"].astype(str).str.len() == 64
    ]

    duplicate_hash_groups = (
        valid_hashes.groupby("sha256")
        .filter(lambda group: len(group) > 1)
        .sort_values("sha256")
    )

    duplicate_hash_groups.to_csv(
        OUTPUT_DIR / "04_identical_file_hashes.csv",
        index=False
    )

    # ========================================================
    # 7. REPEATED FILENAMES
    # ========================================================

    duplicate_names = (
        files_df.groupby("file_name")
        .filter(
            lambda group:
            group["relative_path"].nunique() > 1
        )
        .sort_values([
            "file_name",
            "relative_path"
        ])
    )

    duplicate_names.to_csv(
        OUTPUT_DIR / "05_repeated_basenames.csv",
        index=False
    )

    # ========================================================
    # 8. AUDIT SUMMARY
    # ========================================================

    summary_rows = [
        ("older_glob_file_count", len(old_paths)),
        ("newer_rglob_file_count", len(new_paths)),
        ("common_file_count", len(common)),
        ("only_older_glob_file_count", len(only_old)),
        ("only_newer_rglob_file_count", len(only_new)),

        (
            "identical_content_duplicate_groups",
            int(
                valid_hashes["sha256"]
                .value_counts()
                .gt(1)
                .sum()
            )
        ),

        (
            "repeated_basename_groups",
            int(duplicate_names["file_name"].nunique())
        ),

        (
            "files_with_errors",
            int((files_df["error"] != "").sum())
        ),

        (
            "files_missing_required_columns",
            int(
                (
                    files_df[
                        "missing_required_columns"
                    ].fillna("") != ""
                ).sum()
            )
        ),
    ]

    summary_df = pd.DataFrame(
        summary_rows,
        columns=["metric", "value"]
    )

    summary_df.to_csv(
        OUTPUT_DIR / "00_audit_summary.csv",
        index=False
    )

    # ========================================================
    # 9. PRINT RESULTS
    # ========================================================

    print("\nAUDIT SUMMARY")
    print("-" * 78)

    for metric, value in summary_rows:
        print(f"{metric}: {value:,}")

    print("\nPRODUCT TOTALS")
    print("-" * 78)

    print(
        pd.DataFrame(product_rows).to_string(
            index=False
        )
    )

    print("\nOUTPUT FILES")
    print("-" * 78)

    for output_file in sorted(
        OUTPUT_DIR.glob("*.csv")
    ):

        print(
            f"{output_file.name} "
            f"({output_file.stat().st_size:,} bytes)"
        )

    print(
        f"\nAudit completed.\n"
        f"Output directory: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
