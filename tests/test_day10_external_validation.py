from __future__ import annotations

import struct

import pandas as pd

from pipeline.day10_external_validation import (
    _intersects_bbox,
    association_table,
    cell_centres,
)


def test_bbox_intersection_includes_touching_edges() -> None:
    assert _intersects_bbox((0, 0, 1, 1), (1, 1, 2, 2))
    assert not _intersects_bbox((0, 0, 1, 1), (2, 2, 3, 3))


def test_cell_centres_are_inside_expected_10km_cell() -> None:
    frame = pd.DataFrame({"cell_x": [0], "cell_y": [0], "observation_date": ["2023-01-01"]})
    result = cell_centres(frame)
    assert 0 < result.loc[0, "longitude"] < 0.1
    assert 0 < result.loc[0, "latitude"] < 0.1


def test_association_table_preserves_locked_primary() -> None:
    events = pd.DataFrame({
        "area_ha": [30, 100, 300, 1000],
        "modis_count": [1, 2, 3, 4],
        "viirs_count": [2, 3, 4, 5],
        "incumbent_prediction": [0.5, 1, 2, 3],
        "geometry_aware_prediction": [0.4, 1.1, 2.2, 3.4],
    })
    table = association_table(events, "geometry_aware_prediction")
    assert table["is_primary"].sum() == 1
    assert table.loc[table["is_primary"], "method"].iloc[0] == "geometry_aware_prediction"
    assert table["spearman"].eq(1.0).all()


def test_struct_layout_matches_shapefile_integer_sizes() -> None:
    assert struct.calcsize(">2i") == 8
    assert struct.calcsize("<4d") == 32
