from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main
from config.settings import ProjectConfig
from model_registry.registry import _sha256, register_models
from orchestration.dag_runner import build_dag
from warehouse_loader.postgres_loader import default_targets


def test_customer_search_route_returns_json_safe_records(tmp_path, monkeypatch):
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
                "acquisition_channel": None,
                "loyalty_tier": "Gold",
                "top_purchase_category": "Electronics",
            },
            {
                "customer_id": "C002",
                "churn_probability": 0.12,
                "churn_risk_tier": "Low",
                "expected_profit_at_risk": 100.0,
                "acquisition_channel": "Paid Search",
                "loyalty_tier": "Bronze",
                "top_purchase_category": "Home",
            },
        ]
    ).to_csv(marts / "mart_churn_risk.csv", index=False)
    pd.DataFrame(
        [
            {"customer_id": "C001", "predicted_12m_clv": 4200.0, "clv_band": "Platinum"},
            {"customer_id": "C002", "predicted_12m_clv": 250.0, "clv_band": "Bronze"},
        ]
    ).to_csv(marts / "mart_clv.csv", index=False)
    pd.DataFrame([{"customer_id": "C001", "segment_name": "High Value Loyal Customers"}]).to_csv(
        marts / "mart_customer_segments.csv", index=False
    )
    pd.DataFrame([{"customer_id": "C001", "rfm_segment": "Champions"}]).to_csv(
        marts / "mart_rfm_segments.csv", index=False
    )

    monkeypatch.setattr(api_main, "MARTS", marts)
    monkeypatch.setattr(api_main, "EXPORTS", exports)

    client = TestClient(api_main.app)
    response = client.get("/customers/search?risk_tier=Critical&limit=2")

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "1"
    assert response.headers["X-Limit"] == "2"
    assert response.headers["X-Offset"] == "0"
    payload = response.json()
    assert payload[0]["customer_id"] == "C001"
    assert payload[0]["acquisition_channel"] is None


def test_api_key_is_required_when_configured(monkeypatch):
    monkeypatch.setenv("CUSTOMER_INTELLIGENCE_API_KEY", "secret")
    client = TestClient(api_main.app)

    unauthorized = client.get("/health")
    authorized = client.get("/health", headers={"X-API-Key": "secret"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


def test_downstream_orchestration_skips_pipeline_dependency():
    tasks = build_dag(downstream_only=True)
    assert tasks[0].task_id == "analytics_pipeline"
    assert tasks[0].enabled is False
    assert tasks[1].task_id == "data_validation"
    assert tasks[1].depends_on == []
    assert any(task.task_id == "statistical_analysis" for task in tasks)


def test_statistical_analytics_api_endpoints(tmp_path, monkeypatch):
    exports = tmp_path / "exports"
    exports.mkdir()
    fixtures = {
        "statistical_test_results.csv": [{"analysis_id": "Q01", "p_value": 0.04}],
        "experiment_evaluation.csv": [{"experiment_id": "exp", "absolute_difference": 0.03}],
        "churn_driver_analysis.csv": [{"metric_or_driver": "recency_days", "importance_or_strength": 0.7}],
        "clv_driver_analysis.csv": [{"metric_or_driver": "orders", "importance_or_strength": 0.8}],
    }
    for name, rows in fixtures.items():
        pd.DataFrame(rows).to_csv(exports / name, index=False)
    monkeypatch.setattr(api_main, "EXPORTS", exports)
    client = TestClient(api_main.app)
    for endpoint in ["statistics", "experiments", "churn-drivers", "clv-drivers"]:
        response = client.get(f"/analytics/{endpoint}")
        assert response.status_code == 200
        assert len(response.json()) == 1


def test_postgres_loader_target_catalog_contains_core_marts():
    target_names = {target.table for target in default_targets()}
    assert {"dim_customer", "fact_orders", "mart_churn_risk", "mart_clv", "kpi_summary"}.issubset(target_names)


def test_model_registry_hashes_existing_artifacts(tmp_path):
    artifact = Path(tmp_path / "model.joblib")
    artifact.write_text("registered-model", encoding="utf-8")
    assert len(_sha256(artifact)) == 64


def test_model_registry_uses_approved_public_paths(tmp_path):
    model_dir = tmp_path / "models"
    audit_dir = tmp_path / "data" / "audit"
    model_card_dir = tmp_path / "docs" / "model_cards"
    model_dir.mkdir(parents=True)
    audit_dir.mkdir(parents=True)
    model_card_dir.mkdir(parents=True)

    for artifact_name in ["churn_model.joblib", "clv_model.joblib", "segmentation_model.joblib"]:
        (model_dir / artifact_name).write_text(f"artifact-{artifact_name}", encoding="utf-8")
    (model_dir / "churn_metrics.json").write_text('{"roc_auc": 0.91}', encoding="utf-8")
    (model_dir / "clv_model_metrics.json").write_text('{"r2": 0.22}', encoding="utf-8")
    (model_dir / "segmentation_metrics.json").write_text('{"silhouette_score": 0.31}', encoding="utf-8")

    for card_name in ["churn_model_card.md", "clv_model_card.md", "segmentation_model_card.md"]:
        (model_card_dir / card_name).write_text("# Existing approved card\n", encoding="utf-8")

    config = ProjectConfig(
        root=tmp_path,
        raw_dir=tmp_path / "data" / "raw",
        processed_dir=tmp_path / "data" / "processed",
        mart_dir=tmp_path / "data" / "marts",
        export_dir=tmp_path / "data" / "exports",
        rejected_dir=tmp_path / "data" / "rejected",
        audit_dir=audit_dir,
        report_dir=tmp_path / "reports",
        model_dir=model_dir,
    )

    register_models(config)

    assert (tmp_path / "outputs" / "model_registry.csv").exists()
    assert (audit_dir / "model_registry.csv").exists()
    assert not (tmp_path / "docs" / "model_registry").exists()
    assert not list(model_card_dir.glob("*_model_model_card.md"))
    assert (model_card_dir / "churn_model_card.md").read_text(encoding="utf-8") == "# Existing approved card\n"
