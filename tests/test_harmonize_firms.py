from datetime import datetime, timezone

from qorvex.harmonize_firms import harmonize_record


# Real MODIS record from our earlier FIRMS query.
modis_record = {
    "latitude": "-37.6459",
    "longitude": "145.0045",
    "acq_date": "2024-01-03",
    "acq_time": "430",
    "satellite": "Aqua",
    "instrument": "MODIS",
    "confidence": "37",
    "brightness": "320.4",
    "bright_t31": "296.8",
    "frp": "7.5",
    "daynight": "D",
    "type": "2",
    "version": "61.03",
}

# Real VIIRS record from our earlier FIRMS query.
viirs_record = {
    "latitude": "-33.98823",
    "longitude": "145.50688",
    "acq_date": "2024-01-01",
    "acq_time": "1443",
    "satellite": "N",
    "instrument": "VIIRS",
    "confidence": "n",
    "bright_ti4": "295.85",
    "bright_ti5": "263.28",
    "frp": "2.6",
    "daynight": "N",
    "type": "0",
    "version": "2",
}


modis_result = harmonize_record(modis_record, "MODIS_SP")
viirs_result = harmonize_record(viirs_record, "VIIRS_SNPP_SP")


print("MODIS harmonized record")
print("-" * 40)

for field, value in modis_result.items():
    print(f"{field}: {value!r} ({type(value).__name__})")


print("\nVIIRS harmonized record")
print("-" * 40)

for field, value in viirs_result.items():
    print(f"{field}: {value!r} ({type(value).__name__})")


# Basic checks of important properties.
assert modis_result["latitude"] == -37.6459
assert modis_result["frp_mw"] == 7.5
assert modis_result["confidence_raw"] == "37"
assert modis_result["timestamp_utc"] == datetime(
    2024, 1, 3, 4, 30, tzinfo=timezone.utc
)

assert viirs_result["latitude"] == -33.98823
assert viirs_result["frp_mw"] == 2.6
assert viirs_result["confidence_raw"] == "n"
assert viirs_result["timestamp_utc"] == datetime(
    2024, 1, 1, 14, 43, tzinfo=timezone.utc
)

assert modis_result["viirs_bright_ti4"] is None
assert viirs_result["brightness_raw"] is None

print("\nAll basic checks passed.")

print("\nTesting invalid records")
print("-" * 40)

# Each test starts from a copy of our valid MODIS example.
invalid_cases = [
    ("Invalid latitude", {"latitude": "-120"}),
    ("Negative FRP", {"frp": "-5"}),
    ("Invalid acquisition time", {"acq_time": "2560"}),
]

for test_name, changes in invalid_cases:
    bad_record = modis_record.copy()
    bad_record.update(changes)

    try:
        harmonize_record(bad_record, "MODIS_SP")
    except ValueError as error:
        print(f"PASS — {test_name}: {error}")
    else:
        raise AssertionError(
            f"FAIL — {test_name}: invalid record was accepted"
        )

print("\nAll invalid-record tests passed.")

