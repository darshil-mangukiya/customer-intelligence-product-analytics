from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

import business_analysis.run_uat as uat_module
import scripts.customer_intelligence as customer_intelligence
from config.settings import ProjectConfig
from etl.io_utils import write_csv
from warehouse_loader.postgres_loader import _validated_identifier, default_targets


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_make_python_recipe_expansions_are_shell_quoted() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    recipe_lines = [line for line in makefile.splitlines() if line.startswith("\t")]
    unsafe = [line for line in recipe_lines if "$(PYTHON)" in line and '"$(PYTHON)"' not in line]
    assert unsafe == []


def test_make_preserves_spaced_python_path_as_one_argument() -> None:
    result = subprocess.run(
        ["make", "--dry-run", "r-validate", f"PYTHON={sys.executable}"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert f'"{sys.executable}" -m analytics.r_validation' in result.stdout


def test_postgres_loader_covers_dbt_sources_and_governed_experiment() -> None:
    targets = {(target.schema, target.table) for target in default_targets()}

    assert {
        ("raw", "customers"),
        ("raw", "products"),
        ("raw", "transactions"),
        ("raw", "web_behavior"),
        ("raw", "engagement"),
        ("marts", "experiment_assignments"),
    }.issubset(targets)


def test_postgres_loader_rejects_unsafe_identifiers() -> None:
    assert _validated_identifier("mart_customer_360") == "mart_customer_360"
    with pytest.raises(ValueError, match="invalid SQL identifier"):
        _validated_identifier('customers"; DROP SCHEMA raw; --')


def test_csv_writer_leaves_identical_artifact_in_place(tmp_path) -> None:
    path = tmp_path / "result.csv"
    frame = pd.DataFrame([{"metric": "customers", "value": 5_000}])
    write_csv(frame, path)
    inode = path.stat().st_ino

    write_csv(frame, path)

    assert path.stat().st_ino == inode


def test_ci_workflow_uses_read_only_permissions_and_pinned_actions() -> None:
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow_text
    assert "persist-credentials: false" in workflow_text
    action_lines = [line.strip() for line in workflow_text.splitlines() if "uses:" in line]
    assert action_lines
    assert all("@" in line and len(line.split("@", 1)[1].split()[0]) == 40 for line in action_lines)


def test_compose_does_not_mount_the_repository_root_into_services() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert ".:/app" not in compose
    assert "./data/marts:/app/data/marts:ro" in compose
    assert "./data:/app/data:ro" in compose
    assert compose.count("127.0.0.1:${") == 3


def test_customer_intelligence_writes_current_manifest_before_uat(tmp_path, monkeypatch) -> None:
    config = ProjectConfig(
        root=tmp_path,
        raw_dir=tmp_path / "data" / "raw",
        processed_dir=tmp_path / "data" / "processed",
        mart_dir=tmp_path / "data" / "marts",
        export_dir=tmp_path / "data" / "exports",
        rejected_dir=tmp_path / "data" / "rejected",
        audit_dir=tmp_path / "data" / "audit",
        report_dir=tmp_path / "reports",
        model_dir=tmp_path / "models",
    )
    config.ensure_directories()
    for name in ["customers.csv", "products.csv", "transactions.csv", "web_behavior.csv", "engagement.csv"]:
        (config.raw_dir / name).write_text("generated\n", encoding="utf-8")

    monkeypatch.setattr(customer_intelligence, "CONFIG", config)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    for name in [
        "run_pipeline",
        "build_retention_lifecycle",
        "build_retention_experiment",
        "run_analysis",
        "run_churn_validation",
        "run_drift_monitoring",
        "run_segmentation_validation",
        "run_forecast_validation",
        "build_model_registry",
        "run_r_validation",
        "run_customer_decision_support",
        "run_evaluations",
        "run_validations",
    ]:
        monkeypatch.setattr(customer_intelligence, name, lambda *args, **kwargs: None)

    def assert_manifest_precedes_uat() -> pd.DataFrame:
        manifest = pd.read_csv(config.audit_dir / "customer_intelligence_run_manifest.csv")
        assert manifest.iloc[-1]["stage"] == "ai_fake_provider_evaluations"
        assert manifest["status"].isin({"PASS", "PASS_REUSED_EXISTING_OUTPUTS"}).all()
        return pd.DataFrame([{"uat_id": "UAT-025", "status": "PASS"}])

    monkeypatch.setattr(customer_intelligence, "run_uat", assert_manifest_precedes_uat)

    final_manifest = customer_intelligence.run_customer_intelligence()

    assert "automated_business_uat" in set(final_manifest["stage"])
    assert pd.read_csv(config.audit_dir / "customer_intelligence_run_manifest.csv").equals(final_manifest)


def test_uat_rejects_absent_or_malformed_automation_manifest(tmp_path, monkeypatch) -> None:
    config = ProjectConfig(root=tmp_path, audit_dir=tmp_path / "data" / "audit")
    monkeypatch.setattr(uat_module, "CONFIG", config)

    assert uat_module._automation_manifest()[0] is False

    config.audit_dir.mkdir(parents=True)
    (config.audit_dir / "customer_intelligence_run_manifest.csv").write_text("not,a,valid,manifest\n", encoding="utf-8")

    assert uat_module._automation_manifest()[0] is False
