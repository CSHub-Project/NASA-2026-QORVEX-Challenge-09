
"""Filter the 2024 harmonized FIRMS dataset to Victoria, Australia."""

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd

from qorvex.geographic_filter import filter_detections_by_boundary


DATA_DIR = Path(
    os.getenv("QORVEX_DATA_DIR", r"C:\Users\Asus\data")
)

INPUT_FILE = DATA_DIR / "harmonized_fires_2024.csv"
BOUNDARY_FILE = DATA_DIR / "boundaries" / "victoria_boundary.geojson"
OUTPUT_FILE = DATA_DIR / "victoria_fires_2024.csv"


def main() -> None:
    """Load the boundary, filter detections, and save the result."""
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Input dataset not found: {INPUT_FILE}")

    if not BOUNDARY_FILE.is_file():
        raise FileNotFoundError(f"Boundary file not found: {BOUNDARY_FILE}")

    print("Loading Victoria boundary...")
    boundary = gpd.read_file(BOUNDARY_FILE)

    if "FEATURE_TY" not in boundary.columns:
        raise ValueError(
            "Boundary file is missing the FEATURE_TY column."
        )

    # Include the mainland and coastal islands, excluding the sea feature.
    boundary = boundary[
        boundary["FEATURE_TY"].str.lower() != "sea"
    ].copy()

    if boundary.empty:
        raise ValueError("No land features remain in the boundary.")

    print(f"Land boundary features: {len(boundary):,}")
    print("Loading harmonized fire detections...")
    detections = pd.read_csv(INPUT_FILE)

    print(f"Input detections: {len(detections):,}")
    print("Filtering detections geographically...")

    filtered = filter_detections_by_boundary(
        detections,
        boundary,
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(OUTPUT_FILE, index=False)

    print("\nGeographic filtering complete.")
    print(f"Input detections:     {len(detections):,}")
    print(f"Victoria detections:  {len(filtered):,}")
    print(f"Excluded detections:  {len(detections) - len(filtered):,}")
    print(f"Output file: {OUTPUT_FILE}")

    if not filtered.empty:
        print("\nDetections by source product:")
        print(
            filtered["source_product"]
            .value_counts(dropna=False)
            .to_string()
        )

        print("\nDate range:")
        timestamps = pd.to_datetime(
            filtered["timestamp_utc"],
            errors="coerce",
            utc=True,
        )
        print(f"First detection: {timestamps.min()}")
        print(f"Last detection:  {timestamps.max()}")
    else:
        print(
            "\nWARNING: No detections fall inside the supplied boundary. "
            "Check the boundary and coordinate reference systems."
        )


if __name__ == "__main__":
    main()
