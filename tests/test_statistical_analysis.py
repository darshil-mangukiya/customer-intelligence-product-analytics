from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.customer_driver_analysis import churn_driver_analysis, clv_driver_analysis
from analytics.run_analysis import evaluate_experiment
from analytics.statistical_analysis import (
    chi_square_test,
    cohens_d,
    correlation_test,
    descriptive_summary,
    fit_explanatory_ols,
    holm_adjusted_p_values,
    mean_confidence_interval,
    minimum_detectable_effect,
    proportion_confidence_interval,
    two_proportion_test,
    welch_mean_test,
)


def test_mean_confidence_interval_contains_mean() -> None:
    values = [1, 2, 3, 4, 5]
    low, high = mean_confidence_interval(values)
    assert low < np.mean(values) < high


def test_descriptive_summary_supports_groups_and_binary_proportions() -> None:
    frame = pd.DataFrame({"group": ["a", "a", "b"], "value": [1, 3, 8], "flag": [0, 1, 1]})
    summary = descriptive_summary(frame, ["value", "flag"], "group")
    assert len(summary) == 4
    assert summary.loc[(summary["group"].eq("a")) & summary["metric"].eq("flag"), "proportion"].iloc[0] == 0.5
    with pytest.raises(KeyError):
        descriptive_summary(frame, ["missing"])


def test_constant_mean_interval_collapses() -> None:
    assert mean_confidence_interval([4, 4, 4]) == (4.0, 4.0)


def test_empty_mean_interval_is_rejected() -> None:
    with pytest.raises(ValueError):
        mean_confidence_interval([])


def test_wilson_proportion_interval_is_valid() -> None:
    low, high = proportion_confidence_interval(40, 100)
    assert 0 <= low < 0.4 < high <= 1


def test_zero_denominator_is_rejected() -> None:
    with pytest.raises(ValueError):
        proportion_confidence_interval(0, 0)


def test_cohens_d_direction_uses_group_b_minus_a() -> None:
    assert cohens_d([1, 2, 3], [4, 5, 6]) > 0


def test_welch_test_reports_interval_and_samples() -> None:
    result = welch_mean_test(np.arange(40), np.arange(40) + 3)
    assert result.n_a == result.n_b == 40
    assert result.ci_low <= result.effect_size * np.sqrt((39**2 + 39**2) / 78) or result.ci_low < result.ci_high


def test_two_proportion_test_detects_large_difference() -> None:
    result = two_proportion_test(10, 100, 30, 100)
    assert result.effect_size == pytest.approx(0.2)
    assert result.p_value < 0.05
    assert result.ci_low < result.effect_size < result.ci_high


def test_malformed_proportion_groups_are_rejected() -> None:
    with pytest.raises(ValueError):
        two_proportion_test(2, 1, 0, 10)


def test_chi_square_returns_cramers_v() -> None:
    result = chi_square_test(pd.DataFrame([[40, 10], [10, 40]]))
    assert 0 <= result.effect_size <= 1
    assert result.p_value < 0.05


def test_single_group_chi_square_is_rejected() -> None:
    with pytest.raises(ValueError):
        chi_square_test(pd.DataFrame([[1, 2]]))


def test_spearman_correlation_and_constant_guard() -> None:
    result = correlation_test([1, 2, 3, 4], [10, 20, 30, 40])
    assert result.effect_size == pytest.approx(1.0)
    with pytest.raises(ValueError):
        correlation_test([1, 1, 1], [1, 2, 3])


def test_regression_outputs_predictors_and_diagnostics() -> None:
    x = np.arange(50, dtype=float)
    frame = pd.DataFrame({"target": 10 + x * 2, "x": x, "constant": 1})
    coefficients, diagnostics = fit_explanatory_ols(frame, "target", ["x", "constant"])
    assert coefficients["predictor"].tolist() == ["x"]
    assert diagnostics["n"] == 50
    assert diagnostics["r_squared"] > 0.9


def test_mde_validation_and_positive_result() -> None:
    assert minimum_detectable_effect(500, 500, 0.1) > 0
    with pytest.raises(ValueError):
        minimum_detectable_effect(0, 500, 0.1)


def test_holm_adjustment_controls_familywise_error() -> None:
    adjusted = holm_adjusted_p_values([0.01, 0.03, 0.5])
    assert adjusted.tolist() == pytest.approx([0.03, 0.06, 0.5])
    with pytest.raises(ValueError):
        holm_adjusted_p_values([])


def test_experiment_evaluation_separates_statistical_and_practical_significance() -> None:
    assignments = pd.DataFrame({"variant": ["Control"] * 1000 + ["Retention Offer"] * 1000, "converted": [1] * 100 + [0] * 900 + [1] * 115 + [0] * 885})
    output = evaluate_experiment(assignments)
    assert {"statistically_significant", "practically_significant", "minimum_detectable_effect_80pct_power"}.issubset(output.columns)
    assert bool(output.iloc[0]["practically_significant"]) is False


def test_experiment_requires_both_expected_groups() -> None:
    with pytest.raises(ValueError):
        evaluate_experiment(pd.DataFrame({"variant": ["Control"], "converted": [0]}))


def _driver_frame(rows: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    churn = np.array([0, 1] * (rows // 2))
    data = {"churn_label": churn, "historical_clv": rng.gamma(2, 200, rows)}
    for index, driver in enumerate(["orders", "purchase_frequency_30d", "recency_days", "engagement_score", "engagement_rate", "days_since_engagement", "sessions", "return_rate", "discount_dependency", "avg_order_value", "support_cases", "customer_age_days"]):
        data[driver] = rng.normal(index + churn * 0.2, 1, rows)
    return pd.DataFrame(data)


def test_driver_outputs_have_stable_unique_rankings() -> None:
    frame = _driver_frame()
    churn = churn_driver_analysis(frame)
    clv = clv_driver_analysis(frame)
    for output in [churn, clv]:
        assert output["metric_or_driver"].is_unique
        assert output["importance_or_strength"].is_monotonic_decreasing
        assert output["p_value"].between(0, 1).all()


def test_driver_analysis_rejects_missing_columns() -> None:
    with pytest.raises(KeyError):
        churn_driver_analysis(pd.DataFrame({"churn_label": [0, 1]}))
