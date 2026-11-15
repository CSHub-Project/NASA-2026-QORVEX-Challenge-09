
from datetime import datetime, timezone
import math


def parse_acquisition_timestamp(acq_date, acq_time):
    """Convert a FIRMS date and HHMM time into a UTC datetime."""

    date_part = datetime.strptime(acq_date, "%Y-%m-%d").date()

    if isinstance(acq_time, float) and acq_time.is_integer():
        time_text = str(int(acq_time)).zfill(4)
    else:
        time_text = str(acq_time).strip().zfill(4)

    if len(time_text) != 4 or not time_text.isdigit():
        raise ValueError(f"Invalid FIRMS acquisition time: {acq_time}")

    hour = int(time_text[:2])
    minute = int(time_text[2:])

    if hour > 23 or minute > 59:
        raise ValueError(f"Invalid FIRMS acquisition time: {acq_time}")

    return datetime(
        date_part.year,
        date_part.month,
        date_part.day,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def parse_required_float(value, field_name):
    """Convert a required field to a finite floating-point number."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a valid number; received {value!r}"
        ) from None

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite; received {value!r}")

    return number


def parse_optional_float(value, field_name):
    """Convert an optional numeric field, preserving missing values as None."""

    if value is None or str(value).strip() == "":
        return None

    return parse_required_float(value, field_name)


def harmonize_record(
    row,
    source_product,
    processing_type=None,
    source_file=None,
    source_record_id=None,
):
    """Validate and harmonize one raw MODIS or VIIRS FIRMS record."""

    raw_instrument = row.get("instrument")

    if not isinstance(raw_instrument, str) or not raw_instrument.strip():
        raise ValueError("Missing or invalid instrument.")

    instrument = raw_instrument.strip().upper()

    if instrument not in {"MODIS", "VIIRS"}:
        raise ValueError(f"Unsupported instrument: {instrument}")

    latitude = parse_required_float(row.get("latitude"), "latitude")
    longitude = parse_required_float(row.get("longitude"), "longitude")
    frp = parse_optional_float(row.get("frp"), "frp")
    scan = parse_optional_float(row.get("scan"), "scan")
    track = parse_optional_float(row.get("track"), "track")

    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitude out of range: {latitude}")

    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitude out of range: {longitude}")

    if frp is not None and frp < 0:
        raise ValueError(f"FRP cannot be negative: {frp}")

    timestamp = parse_acquisition_timestamp(
        row["acq_date"], row["acq_time"]
    )

    if instrument == "MODIS":
        brightness = parse_optional_float(
            row.get("brightness"), "brightness"
        )
        brightness_11um = parse_optional_float(
            row.get("bright_t31"), "bright_t31"
        )
        brightness_i4 = None
        brightness_i5 = None
        confidence_type = "numeric_0_100"

    else:
        brightness = None
        brightness_11um = None
        brightness_i4 = parse_optional_float(
            row.get("bright_ti4"), "bright_ti4"
        )
        brightness_i5 = parse_optional_float(
            row.get("bright_ti5"), "bright_ti5"
        )
        confidence_type = "categorical"

    confidence = row.get("confidence")
    if confidence is not None and str(confidence).strip() == "":
        confidence = None

    return {
        "timestamp_utc": timestamp,
        "latitude": latitude,
        "longitude": longitude,
        "sensor": instrument,
        "satellite_raw": row.get("satellite"),
        "source_product": source_product,
        "processing_type": processing_type,
        "source_file": source_file,
        "source_record_id": source_record_id,
        "confidence_raw": confidence,
        "confidence_type": confidence_type,
        "frp_mw": frp,
        "brightness_raw": brightness,
        "brightness_11um_raw": brightness_11um,
        "viirs_bright_ti4": brightness_i4,
        "viirs_bright_ti5": brightness_i5,
        "scan": scan,
        "track": track,
        "daynight_raw": row.get("daynight") or None,
        "source_type_raw": row.get("type") or None,
        "product_version": row.get("version") or None,
    }
