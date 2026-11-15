
"""Filter harmonized FIRMS detections using a geographic boundary."""

from pathlib import Path

import geopandas as gpd
import pandas as pd


def filter_detections_by_boundary(
    detections: pd.DataFrame,
    boundary_path: str | Path | gpd.GeoDataFrame,
    *,
    longitude_col: str = "longitude",
    latitude_col: str = "latitude",
) -> pd.DataFrame:
    """Return detections inside or on a supplied geographic boundary.

    Args:
        detections: DataFrame containing longitude and latitude columns.
        boundary_path: Path to a boundary file or an existing GeoDataFrame.
        longitude_col: Name of the longitude column.
        latitude_col: Name of the latitude column.

    Returns:
        A copy of the original DataFrame containing only detections
        inside or on the boundary. Original columns and row order are kept.

    Raises:
        ValueError: If the boundary or coordinate data is invalid.
        KeyError: If a required coordinate column is missing.
    """
    if longitude_col not in detections.columns:
        raise KeyError(f"Missing longitude column: {longitude_col}")

    if latitude_col not in detections.columns:
        raise KeyError(f"Missing latitude column: {latitude_col}")

    # Accept either a boundary file or a GeoDataFrame.
    if isinstance(boundary_path, (str, Path)):
        boundary = gpd.read_file(boundary_path)
    elif isinstance(boundary_path, gpd.GeoDataFrame):
        boundary = boundary_path.copy()
    else:
        raise TypeError(
            "boundary_path must be a file path or a GeoDataFrame."
        )

    if boundary.empty:
        raise ValueError("Boundary contains no features.")

    if boundary.crs is None:
        raise ValueError("Boundary has no defined coordinate reference system.")

    # Remove missing and empty geometries.
    boundary = boundary[
        boundary.geometry.notna() & ~boundary.geometry.is_empty
    ]

    if boundary.empty:
        raise ValueError("Boundary contains no usable geometries.")

    # Combine the supplied features into one area of interest.
    area = boundary.geometry.union_all()

    if area.is_empty or not area.is_valid:
        raise ValueError("Boundary geometry is empty or invalid.")

    # Convert coordinates to numeric values; invalid coordinates are excluded.
    longitude = pd.to_numeric(
        detections[longitude_col], errors="coerce"
    )
    latitude = pd.to_numeric(
        detections[latitude_col], errors="coerce"
    )

    valid_coordinates = (
        longitude.notna()
        & latitude.notna()
        & longitude.between(-180, 180)
        & latitude.between(-90, 90)
    )

    # Start with all detections marked as outside.
    inside = pd.Series(False, index=detections.index)

    if valid_coordinates.any():
        points = gpd.GeoSeries(
            gpd.points_from_xy(
                longitude.loc[valid_coordinates],
                latitude.loc[valid_coordinates],
            ),
            index=detections.index[valid_coordinates],
            crs="EPSG:4326",
        )

        # Transform points into the boundary's CRS when necessary.
        if boundary.crs != points.crs:
            points = points.to_crs(boundary.crs)

        # covered_by includes points on the boundary itself.
        inside.loc[valid_coordinates] = points.covered_by(area).to_numpy()

    return detections.loc[inside].copy()
