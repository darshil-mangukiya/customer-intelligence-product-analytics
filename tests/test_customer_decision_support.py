from __future__ import annotations

import json

import pandas as pd
import pytest

from analytics.customer_decision_support import SCENARIOS, calculate_retention_scenarios
from analytics.experiment_design import required_sample_size_per_group, sample_ratio_mismatch
from config.settings import CONFIG


def _at_risk() -> pd.DataFrame:
    return pd.DataFrame({
        "customer_id": ["C1", "C2"], "net_revenue": [100.0, 200.0],
        "predicted_12m_clv": [150.0, 250.0], "return_adjusted_profit": [30.0, 60.0],
    })


def test_experiment_design_sample_size_and_validation() -> None:
    assert required_sample_size_per_group(0.06, 0.02, 0.05, 0.80) > 1_000
    with pytest.raises(ValueError):
        required_sample_size_per_group(0, 0.02)
    with pytest.raises(ValueError):
        required_sample_size_per_group(0.99, 0.02)


def test_srm_pass_fail_and_edge_cases() -> None:
    assert sample_ratio_mismatch(500, 500)["status"] == "PASS"
    assert sample_ratio_mismatch(900, 100)["status"] == "FAIL"
    with pytest.raises(ValueError):
        sample_ratio_mismatch(0, 0)
    with pytest.raises(ValueError):
        sample_ratio_mismatch(5, -1)


def test_retention_scenarios_baseline_positive_and_zero_cost() -> None:
    result = calculate_retention_scenarios(_at_risk())
    assert list(result["scenario"]) == list(SCENARIOS)
    baseline = result.loc[result["scenario"].eq("Baseline")].iloc[0]
    assert baseline["estimated_customers_retained"] == 0
    assert baseline["estimated_roi"] == 0
    expected = result.loc[result["scenario"].eq("Expected")].iloc[0]
    assert expected["estimated_revenue_preserved"] > 0
    zero_cost = calculate_retention_scenarios(_at_risk(), {"Free": {"retention_lift": 0.1, "cost_per_customer": 0, "target_share": 1}})
    assert zero_cost.iloc[0]["estimated_roi"] == 0


def test_retention_scenarios_invalid_and_zero_revenue() -> None:
    with pytest.raises(ValueError):
        calculate_retention_scenarios(_at_risk(), {"Bad": {"retention_lift": -0.1, "cost_per_customer": 1, "target_share": 1}})
    zero = _at_risk().assign(net_revenue=0.0, return_adjusted_profit=0.0)
    assert calculate_retention_scenarios(zero).iloc[0]["estimated_roi"] == 0


def test_generated_migration_action_and_reconciliation_outputs() -> None:
    migration = pd.read_csv(CONFIG.export_dir / "customer_segment_migration.csv")
    summary = pd.read_csv(CONFIG.export_dir / "segment_migration_summary.csv")
    action = pd.read_csv(CONFIG.export_dir / "retention_action_center.csv")
    reconciliation = pd.read_csv(CONFIG.export_dir / "customer_intelligence_reconciliation.csv")
    assert migration["customer_id"].nunique() == int(summary["customer_count"].sum())
    assert migration["prior_segment"].notna().all()
    assert set(migration["migration_signal"]) <= {"DETERIORATING", "IMPROVING", "STABLE"}
    assert not migration.select_dtypes("number").isna().any().any()
    assert set(action["priority"]) <= {"LOW", "MEDIUM", "HIGH"}
    assert action["review_status"].eq("NEEDS_REVIEW").all()
    assert reconciliation["status"].eq("PASS").all()


def test_insight_packet_schema_and_finiteness() -> None:
    path = CONFIG.root / "artifacts" / "customer_intelligence" / "latest_customer_insight_packet.json"
    raw = path.read_text(encoding="utf-8")
    packet = json.loads(raw)
    required = {"reporting_period", "customer_kpis", "segment_summary", "segment_migrations", "churn_summary", "churn_drivers", "clv_summary", "cohort_summary", "experiment_results", "experiment_validity", "python_r_reconciliation", "retention_scenarios", "revenue_or_clv_exposure", "priority_actions", "data_quality_warnings", "source_evidence", "generated_at"}
    assert required <= packet.keys()
    assert "NaN" not in raw and "Infinity" not in raw
    assert "customer_id" not in raw
