from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main
from activation.build_activation_exports import ACTIVATION_COLUMNS, build_activation_exports
from config.settings import ProjectConfig
from enterprise_assets.generate_enterprise_assets import generate_enterprise_assets
from observability.enterprise_quality import build_enterprise_quality_outputs


def _config(root: Path) -> ProjectConfig:
    return ProjectConfig(
        root=root,
        raw_dir=root / "data" / "raw",
        processed_dir=root / "data" / "processed",
        mart_dir=root / "data" / "marts",
        export_dir=root / "data" / "exports",
        rejected_dir=root / "data" / "rejected",
        audit_dir=root / "data" / "audit",
        report_dir=root / "reports",
        model_dir=root / "models",
    )


def test_enterprise_asset_generation_creates_technical_catalogs(tmp_path):
    config = _config(tmp_path)

    paths = generate_enterprise_assets(config)

    assert paths
    assert (tmp_path / "docs" / "architecture_overview.md").exists()
    assert (tmp_path / "docs" / "feature_catalog.md").exists()
    assert (tmp_path / "docs" / "kpi_dictionary.md").exists()
    assert (tmp_path / "dashboards" / "specs" / "powerbi_dashboard_spec.md").exists()
    assert (tmp_path / "dashboards" / "specs" / "dax_measure_catalog.md").exists()
    assert (tmp_path / "outputs" / "feature_catalog.csv").exists()
    assert (tmp_path / "outputs" / "kpi_catalog.csv").exists()
    assert (tmp_path / "outputs" / "model_registry.csv").exists()
    assert (tmp_path / "outputs" / "churn_model_evaluation.csv").exists()
    assert (tmp_path / "outputs" / "feature_importance_clv.csv").exists()
    assert (tmp_path / "outputs" / "model_scoring_log.csv").exists()
    assert not (tmp_path / "docs" / "interview_talking_points.md").exists()
    assert not (tmp_path / "docs" / "portfolio").exists()
    assert not (tmp_path / "docs" / "recruiter_pitch.md").exists()


def test_activation_exports_have_required_schema(tmp_path):
    config = _config(tmp_path)
    config.ensure_directories()
    pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "churn_probability": 0.91,
                "churn_risk_tier": "Critical",
                "expected_profit_at_risk": 2500,
                "top_purchase_category": "Electronics",
                "discount_dependency": 0.45,
                "return_rate": 0.05,
                "orders": 1,
                "recency_days": 180,
            },
            {
                "customer_id": "C002",
                "churn_probability": 0.22,
                "churn_risk_tier": "Low",
                "expected_profit_at_risk": 100,
                "top_purchase_category": "Home",
                "discount_dependency": 0.10,
                "return_rate": 0.02,
                "orders": 5,
                "recency_days": 20,
            },
        ]
    ).to_csv(config.mart_dir / "mart_churn_risk.csv", index=False)
    pd.DataFrame(
        [
            {"customer_id": "C001", "predicted_12m_clv": 4500, "clv_band": "Platinum", "loyalty_tier": "Gold"},
            {"customer_id": "C002", "predicted_12m_clv": 300, "clv_band": "Bronze", "loyalty_tier": "Bronze"},
        ]
    ).to_csv(config.mart_dir / "mart_clv.csv", index=False)
    pd.DataFrame([{"customer_id": "C001", "segment_name": "High Value Loyal"}]).to_csv(
        config.mart_dir / "mart_customer_segments.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "recommended_category": "Beauty",
                "recommended_action": "Cross-sell recommendation",
                "action_priority_score": 0.98,
            }
        ]
    ).to_csv(config.export_dir / "next_best_actions.csv", index=False)

    exports = build_activation_exports(config, sample_rows=10)

    assert set(exports) == {
        "activation_churn_campaign.csv",
        "activation_winback_campaign.csv",
        "activation_high_clv_customers.csv",
        "activation_cross_sell_targets.csv",
        "activation_loyalty_upgrade_targets.csv",
        "activation_discount_sensitive_customers.csv",
    }
    for filename in exports:
        full_export = pd.read_csv(config.export_dir / filename)
        sample_export = pd.read_csv(tmp_path / "outputs" / filename)
        assert list(full_export.columns) == ACTIVATION_COLUMNS
        assert list(sample_export.columns) == ACTIVATION_COLUMNS


def test_enterprise_quality_outputs_create_freshness_and_summary(tmp_path):
    config = _config(tmp_path)
    config.ensure_directories()
    pd.DataFrame(
        [
            {
                "suite": "key_integrity",
                "table_name": "fact_orders",
                "expectation": "expect_column_values_to_be_unique",
                "column_name": "order_id",
                "status": "PASS",
                "observed_value": "0",
                "threshold": "= 0",
                "failing_rows": 0,
                "severity": "HIGH",
            }
        ]
    ).to_csv(config.export_dir / "validation_results.csv", index=False)
    pd.DataFrame([{"step": "data_cleaning", "seconds": 1.5, "status": "success"}]).to_csv(
        config.audit_dir / "pipeline_run_manifest.csv",
        index=False,
    )
    pd.DataFrame([{"order_id": "O001"}]).to_csv(config.mart_dir / "fact_orders.csv", index=False)

    outputs = build_enterprise_quality_outputs(config)

    assert {"data_quality_summary.csv", "mart_freshness_report.csv", "pipeline_audit_log.csv"}.issubset(outputs)
    assert (tmp_path / "outputs" / "data_quality_summary.csv").exists()
    assert (tmp_path / "outputs" / "mart_freshness_report.csv").exists()
    assert outputs["data_quality_summary.csv"].iloc[0]["status"] == "PASS"


def test_enterprise_api_routes_return_metrics_and_activation(tmp_path, monkeypatch):
    marts = tmp_path / "marts"
    exports = tmp_path / "exports"
    marts.mkdir()
    exports.mkdir()
    pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "churn_probability": 0.91,
                "churn_risk_tier": "Critical",
                "expected_profit_at_risk": 2500.0,
                "acquisition_channel": "Paid Search",
                "loyalty_tier": "Gold",
                "top_purchase_category": "Electronics",
            }
        ]
    ).to_csv(marts / "mart_churn_risk.csv", index=False)
    pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "predicted_12m_clv": 4200.0,
                "clv_band": "Platinum",
                "expected_clv_at_risk": 900.0,
            }
        ]
    ).to_csv(marts / "mart_clv.csv", index=False)
    pd.DataFrame([{"customer_id": "C001", "segment_name": "High Value Loyal"}]).to_csv(
        marts / "mart_customer_segments.csv",
        index=False,
    )
    pd.DataFrame([{"customer_id": "C001", "rfm_segment": "Champions"}]).to_csv(
        marts / "mart_rfm_segments.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "product_id": "P001",
                "category": "Electronics",
                "net_revenue": 1000.0,
                "return_adjusted_profit": 300.0,
                "return_rate": 0.08,
            }
        ]
    ).to_csv(marts / "mart_product_profitability.csv", index=False)
    pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "recommended_action": "Cross-sell recommendation",
                "action_priority_score": 0.95,
            }
        ]
    ).to_csv(exports / "next_best_actions.csv", index=False)
    activation_row = {
        "customer_id": "C001",
        "segment": "High Value Loyal",
        "churn_probability": 0.91,
        "clv_band": "Platinum",
        "recommended_action": "Retention save journey",
        "recommended_product_category": "Electronics",
        "priority_score": 99.0,
        "campaign_reason": "High churn risk.",
    }
    pd.DataFrame([activation_row]).to_csv(exports / "activation_churn_campaign.csv", index=False)
    pd.DataFrame([activation_row]).to_csv(exports / "activation_cross_sell_targets.csv", index=False)

    monkeypatch.setattr(api_main, "MARTS", marts)
    monkeypatch.setattr(api_main, "EXPORTS", exports)
    client = TestClient(api_main.app)

    assert client.get("/metrics/churn").status_code == 200
    assert client.get("/metrics/clv").status_code == 200
    assert client.get("/metrics/products").status_code == 200
    assert client.get("/customers/C001/profile").json()["segment_name"] == "High Value Loyal"
    assert client.get("/customers/C001/churn-risk").json()["churn_risk_tier"] == "Critical"
    assert client.get("/customers/C001/recommendations").json()[0]["recommended_action"] == "Cross-sell recommendation"
    assert client.get("/products/P001/profitability").json()["category"] == "Electronics"
    assert client.get("/activation/churn-campaign").json()[0]["customer_id"] == "C001"
