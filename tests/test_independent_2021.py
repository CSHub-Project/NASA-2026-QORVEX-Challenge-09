import pandas as pd
import pytest

from pipeline.common import ROOT
from pipeline.evaluate_2021 import assert_frozen_selection


def test_later_year_evaluation_rejects_changed_2019_model_choice():
    selection = pd.read_csv(ROOT / "outputs" / "tables" / "day4_validation_selection.csv")
    assert_frozen_selection(selection)
    changed = selection.copy()
    changed.loc[0, "selected_method"] = (
        "baseline" if changed.loc[0, "selected_method"] == "model" else "model"
    )
    with pytest.raises(AssertionError):
        assert_frozen_selection(changed)
