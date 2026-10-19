
import csv
import io

import pytest

from qorvex.harmonize_firms import harmonize_record


from scripts.collect_firms_2024 import (
    REQUIRED_COLUMNS,
    validate_csv_header,
)


def test_valid_firms_csv_header_is_accepted():
    header = ",".join(sorted(REQUIRED_COLUMNS))
    content = f"{header}\n"

    result = validate_csv_header(content)

    assert set(result) == REQUIRED_COLUMNS


def test_empty_csv_response_is_rejected():
    with pytest.raises(ValueError, match="no CSV header"):
        validate_csv_header("")


def test_csv_missing_required_columns_is_rejected():
    content = "latitude,longitude,acq_date\n"

    with pytest.raises(
        ValueError,
        match="missing columns",
    ):
        validate_csv_header(content)
