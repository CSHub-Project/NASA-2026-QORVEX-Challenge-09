from datetime import date

import polars as pl
import pytest

from pipeline.observability_audit import summarize


def test_support_audit_keeps_sensor_only_cells_distinct():
    pairs = pl.DataFrame({
        "region_id": ["western_iberia"] * 3,
        "observation_date": [date(2022, 7, 1)] * 3,
        "daynight": ["D"] * 3,
        "modis_count": [2, 0, 1],
        "viirs_count": [0, 3, 4],
    })
    row = summarize(pairs).row(0, named=True)
    assert row["union_cell_passes"] == 3
    assert row["modis_only_cell_passes"] == 1
    assert row["viirs_only_cell_passes"] == 1
    assert row["shared_positive_cell_passes"] == 1
    assert row["viirs_positive_cell_recall_of_modis"] == 0.5
    assert row["modis_detection_fraction_without_viirs_cell"] == pytest.approx(2 / 3)


def test_support_audit_rejects_empty_union_cell():
    pairs = pl.DataFrame({
        "region_id": ["western_iberia"],
        "observation_date": [date(2022, 7, 1)],
        "daynight": ["D"],
        "modis_count": [0],
        "viirs_count": [0],
    })
    with pytest.raises(ValueError, match="empty on both"):
        summarize(pairs)
