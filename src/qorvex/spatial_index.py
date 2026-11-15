
"""Spatially index harmonized FIRMS detections using H3."""

import math

import h3


H3_RESOLUTIONS = (5, 7, 8, 9)


def add_h3_indices(record):
    """Return a harmonized detection enriched with four H3 identifiers.

    The input record is not modified.
    """

    latitude = record.get("latitude")
    longitude = record.get("longitude")

    if isinstance(latitude, bool) or isinstance(longitude, bool):
        raise ValueError("Latitude and longitude must be numeric coordinates.")

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise ValueError("Latitude and longitude must be numeric coordinates.") from None

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("Latitude and longitude must be finite.")

    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitude out of range: {latitude}")

    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitude out of range: {longitude}")

    indexed_record = record.copy()

    for resolution in H3_RESOLUTIONS:
        indexed_record[f"h3_res{resolution}"] = h3.latlng_to_cell(
            latitude,
            longitude,
            resolution,
        )

    return indexed_record
