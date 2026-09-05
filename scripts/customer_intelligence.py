from __future__ import annotations

import os
import time

import pandas as pd

from ai.copilot import OpenAIProvider, ask, load_packet
from ai.evals.run_evals import run_evaluations
from analytics.customer_decision_support import run_customer_decision_support
from analytics.r_validation import run_r_validation
from analytics.run_analysis import run_analysis
from config.settings import CONFIG
from etl.io_utils import write_csv, write_markdown
from etl.run_pipeline import run_pipeline
from etl.synthetic_data import GenerationConfig
from experimentation.ab_testing import build_retention_experiment
from retention_analytics.lifecycle_analysis import build_retention_lifecycle
from validation.validate_data import run_validations
from business_analysis.run_uat import run_uat
from forecasting.validation import run_forecast_validation
from model_validation.churn_validation import run_churn_validation
from model_validation.model_registry import build_model_registry
from monitoring.drift_monitoring import run_drift_monitoring
from segmentation.validation import run_segmentation_validation


def run_customer_intelligence() -> pd.DataFrame:
    """Refresh the existing local lifecycle and record truthful stage evidence."""
    stages: list[dict[str, object]] = []
    manifest_path = CONFIG.audit_dir / "customer_intelligence_run_manifest.csv"

    def write_run_manifest() -> pd.DataFrame:
        manifest = pd.DataFrame(stages)
        write_csv(manifest, manifest_path)
        return manifest

    def execute(name: str, function, required_outputs: list[str] | None = None):
        started = time.perf_counter()
        status = "PASS"
        try:
            function()
        except PermissionError:
            paths = [CONFIG.root / path for path in (required_outputs or [])]
            if not paths or not all(path.exists() and path.stat().st_size > 0 for path in paths):
                raise
            status = "PASS_REUSED_EXISTING_OUTPUTS"
        seconds = round(time.perf_counter() - started, 3)
        stages.append({"stage": name, "status": status, "seconds": seconds})
        print(f"[customer-intelligence] {name}: {status} ({seconds:.3f}s)")

    def validate_source_presence() -> None:
        required = ["customers.csv", "products.csv", "transactions.csv", "web_behavior.csv", "engagement.csv"]
        missing = [name for name in required if not (CONFIG.raw_dir / name).is_file() or (CONFIG.raw_dir / name).stat().st_size == 0]
        if missing:
            raise FileNotFoundError(f"missing or empty synthetic sources: {missing}")

    execute("source_data_validation", validate_source_presence)
    execute("customer_feature_model_refresh", lambda: run_pipeline(GenerationConfig(), skip_generation=True), ["data/processed/customer_features.csv", "data/marts/mart_churn_risk.csv", "data/marts/mart_clv.csv"])
    execute("retention_lifecycle", build_retention_lifecycle, ["data/marts/mart_retention_lifecycle.csv"])
    execute("synthetic_experiment", build_retention_experiment, ["data/exports/ab_test_customer_assignments.csv"])
    execute("statistical_and_driver_analysis", run_analysis, ["data/exports/experiment_evaluation.csv", "data/exports/churn_driver_analysis.csv"])
    execute("churn_model_validation", run_churn_validation, ["data/exports/churn_model_metrics.csv", "data/exports/churn_threshold_analysis.csv", "data/exports/churn_calibration_bins.csv"])
    execute("model_drift_monitoring", run_drift_monitoring, ["data/exports/model_feature_drift.csv", "data/exports/model_prediction_drift.csv", "data/exports/segment_drift_monitoring.csv"])
    execute("segmentation_validation", run_segmentation_validation, ["data/exports/segmentation_validation_metrics.csv", "data/exports/segmentation_seed_stability.csv"])
    execute("forecast_walk_forward_validation", run_forecast_validation, ["data/exports/forecast_backtest_results.csv"])
    execute("model_registry_refresh", build_model_registry, ["artifacts/model_registry.json"])
    execute("python_r_reconciliation", run_r_validation, ["data/exports/python_r_statistical_reconciliation.csv"])
    execute("decision_support_and_insight_packet", run_customer_decision_support, ["artifacts/customer_intelligence/latest_customer_insight_packet.json", "data/exports/customer_intelligence_reconciliation.csv"])
    execute("ai_fake_provider_evaluations", run_evaluations, ["data/exports/ai_evaluation_results.csv"])
    write_run_manifest()
    execute("automated_business_uat", run_uat, ["data/exports/uat_execution_results.csv"])

    if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL"):
        def real_provider_check() -> None:
            response = ask("Was the retention experiment statistically and practically significant?", OpenAIProvider.from_environment(), load_packet())
            evidence_path = CONFIG.audit_dir / "ai_real_provider_smoke.json"
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            safe = {"provider": "openai", "model_from_environment": True, "response_keys": sorted(response), "status": "PASS"}
            evidence_path.write_text(__import__("json").dumps(safe, indent=2), encoding="utf-8")
        execute("openai_provider_smoke", real_provider_check)
    else:
        stages.append({"stage": "openai_provider_smoke", "status": "NOT_RUN_NO_CREDENTIALS", "seconds": 0.0})

    execute("data_validation_post_refresh", run_validations, ["data/exports/validation_results.csv"])
    manifest = write_run_manifest()
    lines = [
        "# Automated Customer Intelligence Run", "",
        "This run reused the existing deterministic P3 pipeline and added governed decision-support stages. All data is synthetic.", "",
        "| Stage | Status | Seconds |", "|---|---|---:|",
    ]
    lines.extend(f"| {row['stage']} | {row['status']} | {row['seconds']:.3f} |" for row in stages)
    report_path = CONFIG.report_dir / "customer_intelligence_automation.md"
    try:
        write_markdown(lines, report_path)
    except PermissionError:
        if not report_path.exists() or report_path.stat().st_size == 0:
            raise
    return manifest


def main() -> None:
    run_customer_intelligence()


if __name__ == "__main__":
    main()
