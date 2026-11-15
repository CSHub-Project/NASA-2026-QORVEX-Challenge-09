from datetime import date, timedelta

import numpy as np
import pandas as pd

from pipeline.day9_independent_transfer import date_block_bootstrap, make_decision, metric_table


REGIONS = ("southern_africa_savanna", "eastern_siberia_boreal", "southeast_australia")


def synthetic_scores() -> pd.DataFrame:
    rows = []
    start = date(2024, 1, 1)
    for region in REGIONS:
        for index in range(500):
            observed = 1 + index % 3
            rows.append({
                "region_id": region,
                "daynight": "D" if index % 2 == 0 else "N",
                "observation_date": start + timedelta(days=index % 100),
                "modis_count": observed,
                "baseline_prediction": observed + 1.0,
                "model_prediction": observed + 0.1,
            })
    return pd.DataFrame(rows)


def test_day9_metrics_and_bootstrap_reward_lower_error() -> None:
    frame = synthetic_scores()
    metrics = metric_table(frame)
    pooled = metrics[(metrics.region_id == "all") & (metrics.daynight == "all")].set_index("method")
    assert pooled.loc["model", "wape"] < pooled.loc["baseline", "wape"]
    bootstrap = date_block_bootstrap(frame, replicates=100)
    assert bootstrap.loc[0, "ci_97_5"] < 0


def test_day9_decision_requires_every_locked_gate() -> None:
    frame = synthetic_scores()
    metrics = metric_table(frame)
    bootstrap = date_block_bootstrap(frame, replicates=100)
    matches = pd.DataFrame([
        {"region_id": region, "pair_id": f"{region}-{index}"}
        for region in REGIONS for index in range(50)
    ])
    decision = make_decision(metrics, bootstrap, matches).iloc[0]
    assert bool(decision["minimum_support_all_regions"])
    assert bool(decision["external_transfer_gate_passed"])


def test_day9_decision_fails_when_one_region_is_underpowered() -> None:
    frame = synthetic_scores()
    metrics = metric_table(frame)
    bootstrap = date_block_bootstrap(frame, replicates=100)
    matches = pd.DataFrame([
        {"region_id": region, "pair_id": f"{region}-{index}"}
        for region in REGIONS for index in range(49 if region == REGIONS[0] else 50)
    ])
    decision = make_decision(metrics, bootstrap, matches).iloc[0]
    assert not bool(decision["minimum_support_all_regions"])
    assert not bool(decision["external_transfer_gate_passed"])
