import numpy as np
import pandas as pd

from pipeline.day11_multiswath_audit import aoi_cells, classify_state


def test_aoi_template_has_unique_centers_inside_bounds() -> None:
    cells = aoi_cells((-9.0, 39.0, -7.0, 41.0), 10)
    assert len(cells) > 300
    assert not cells.duplicated(["cell_x", "cell_y"]).any()
    assert cells["center_lon"].between(-9, -7).all()
    assert cells["center_lat"].between(39, 41).all()


def test_evidence_precedence_never_calls_cloud_clear() -> None:
    frame = pd.DataFrame({
        "not_processed": [0, 0, 0, 0], "water": [0, 0, 0, 0],
        "cloud": [0, 0, 3, 0], "clear_nonfire_land": [0, 2, 0, 2],
        "unknown": [0, 0, 0, 0], "fire": [0, 0, 0, 1],
    })
    assert classify_state(frame).tolist() == [
        "not_observed", "clear_sampled_no_detection",
        "obscured_or_nonland_only", "fire_observed",
    ]


def test_unknown_mask_content_remains_obscured() -> None:
    frame = pd.DataFrame({
        "not_processed": [1], "water": [2], "cloud": [1],
        "clear_nonfire_land": [0], "unknown": [1], "fire": [0],
    })
    assert classify_state(frame).iloc[0] == "obscured_or_nonland_only"
