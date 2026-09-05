from __future__ import annotations

import pandas as pd

from churn_model.train_churn_model import _risk_tier
from segmentation.rfm_analysis import _qscore


def test_churn_risk_tiers_cover_expected_ranges():
    tiers = _risk_tier(pd.Series([0.05, 0.30, 0.60, 0.90]))
    assert tiers.tolist() == ["Low", "Medium", "High", "Critical"]


def test_rfm_qscore_returns_one_to_five_scores():
    scores = _qscore(pd.Series([10, 20, 30, 40, 50]), ascending=True)
    assert scores.min() == 1
    assert scores.max() == 5
    assert len(scores) == 5

