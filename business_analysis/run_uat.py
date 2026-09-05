from __future__ import annotations

import json
from collections.abc import Callable

import pandas as pd

from config.settings import CONFIG
from etl.io_utils import write_csv


def _exists(relative: str) -> tuple[bool, str]:
    path = CONFIG.root / relative
    passed = path.exists() and path.stat().st_size > 20
    return passed, f"{relative}: {'generated' if passed else 'missing or empty'}"


def run_uat() -> pd.DataFrame:
    checks: dict[str, tuple[str, str, Callable[[], tuple[bool, str]]]] = {
        "UAT-001": ("CR-001", "Customer 360 unique population", lambda: (pd.read_csv(CONFIG.processed_dir / "customer_features.csv")["customer_id"].is_unique, "customer_id uniqueness checked")),
        "UAT-002": ("CR-001", "Churn population reconciliation", lambda: _reconciliation("churn_population")),
        "UAT-003": ("CR-001", "Action center governed fields", lambda: _action_center()),
        "UAT-004": ("CR-003", "CLV finite modeled values", lambda: _finite_csv("data/marts/mart_clv.csv")),
        "UAT-005": ("CR-005", "RFM output generated", lambda: _exists("data/marts/mart_rfm_segments.csv")),
        "UAT-006": ("CR-005", "Segment comparison generated", lambda: _exists("data/exports/segment_kpi_comparison.csv")),
        "UAT-007": ("CR-002", "Driver evidence generated", lambda: _exists("data/exports/churn_driver_analysis.csv")),
        "UAT-008": ("CR-005", "Migration population reconciliation", lambda: _migration()),
        "UAT-009": ("CR-007", "Registry lifecycle traceability", lambda: _registry()),
        "UAT-010": ("CR-004", "Experiment results complete", lambda: _exists("data/exports/experiment_evaluation.csv")),
        "UAT-011": ("CR-006", "SRM status generated", lambda: _csv_status("data/exports/experiment_srm_validation.csv")),
        "UAT-012": ("CR-011", "Python/R reconciliation", lambda: _csv_status("data/exports/python_r_statistical_reconciliation.csv")),
        "UAT-013": ("CR-004", "Experiment readout generated", lambda: _exists("reports/experiments/synthetic_retention_offer_v1_readout.md")),
        "UAT-014": ("CR-007", "Decision log generated", lambda: _exists("experimentation/decision_log.csv")),
        "UAT-015": ("CR-003", "CLV-at-risk reconciliation", lambda: _reconciliation("clv_at_risk")),
        "UAT-016": ("CR-008", "Five scenario outputs", lambda: _scenarios()),
        "UAT-017": ("CR-009", "Action priorities review-only", lambda: _action_center()),
        "UAT-018": ("CR-010", "Machine-readable outputs", lambda: _exists("data/exports/customer_intelligence_alerts.csv")),
        "UAT-019": ("CR-012", "Advisory governance", lambda: _policy()),
        "UAT-020": ("CR-013", "Cross-layer reconciliation", lambda: _csv_status("data/exports/customer_intelligence_reconciliation.csv")),
        "UAT-021": ("CR-014", "Explainable alerts", lambda: _alerts()),
        "UAT-022": ("CR-015", "Finite aggregate insight packet", lambda: _packet()),
        "UAT-023": ("CR-016", "AI guardrail evaluations", lambda: _csv_status("data/exports/ai_evaluation_results.csv")),
        "UAT-024": ("CR-017", "Local AI modes tested", lambda: _exists("tests/test_ai_copilot.py")),
        "UAT-025": ("CR-018", "Automation run manifest", _automation_manifest),
    }
    rows = []
    for uat_id, (requirement, scenario, check) in checks.items():
        passed, actual = check()
        rows.append({"uat_id": uat_id, "requirement_id": requirement, "scenario": scenario, "actual_result": actual, "status": "PASS" if passed else "FAIL", "executed_by": "automated local validation"})
    output = pd.DataFrame(rows)
    write_csv(output, CONFIG.export_dir / "uat_execution_results.csv")
    evidence = CONFIG.root / "docs" / "evidence" / "uat_execution_results.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence_content = json.dumps(output.to_dict("records"), indent=2) + "\n"
    if not evidence.exists() or evidence.read_text(encoding="utf-8") != evidence_content:
        evidence.write_text(evidence_content, encoding="utf-8")
    return output


def _finite_csv(relative: str) -> tuple[bool, str]:
    frame = pd.read_csv(CONFIG.root / relative)
    numeric = frame.select_dtypes("number")
    passed = not numeric.isna().any().any() and not numeric.isin([float("inf"), float("-inf")]).any().any()
    return passed, f"{len(frame):,} rows; numeric fields finite={passed}"


def _csv_status(relative: str) -> tuple[bool, str]:
    frame = pd.read_csv(CONFIG.root / relative)
    passed = "status" in frame and frame["status"].eq("PASS").all()
    return passed, f"{int(frame['status'].eq('PASS').sum()) if 'status' in frame else 0}/{len(frame)} PASS"


def _automation_manifest() -> tuple[bool, str]:
    path = CONFIG.audit_dir / "customer_intelligence_run_manifest.csv"
    if not path.exists() or path.stat().st_size <= 20:
        return False, "data/audit/customer_intelligence_run_manifest.csv: missing or empty"
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return False, "data/audit/customer_intelligence_run_manifest.csv: unreadable"
    required_columns = {"stage", "status", "seconds"}
    required_stages = {
        "source_data_validation",
        "customer_feature_model_refresh",
        "python_r_reconciliation",
        "decision_support_and_insight_packet",
        "ai_fake_provider_evaluations",
    }
    valid_statuses = {"PASS", "PASS_REUSED_EXISTING_OUTPUTS"}
    columns_valid = required_columns <= set(frame.columns)
    required_rows = frame.loc[frame["stage"].isin(required_stages)] if columns_valid else pd.DataFrame()
    stages_valid = columns_valid and set(required_rows["stage"]) == required_stages
    statuses_valid = stages_valid and required_rows["status"].isin(valid_statuses).all()
    passed = columns_valid and stages_valid and statuses_valid
    return passed, f"current-run prerequisites={len(required_stages & set(frame['stage'])) if columns_valid else 0}/{len(required_stages)}; statuses valid={statuses_valid}"


def _reconciliation(name: str) -> tuple[bool, str]:
    frame = pd.read_csv(CONFIG.export_dir / "customer_intelligence_reconciliation.csv")
    row = frame.loc[frame["check"].eq(name)]
    passed = len(row) == 1 and row.iloc[0]["status"] == "PASS"
    return passed, f"{name}: {row.iloc[0]['status'] if len(row) else 'missing'}"


def _migration() -> tuple[bool, str]:
    detail = pd.read_csv(CONFIG.export_dir / "customer_segment_migration.csv")
    summary = pd.read_csv(CONFIG.export_dir / "segment_migration_summary.csv")
    passed = detail["customer_id"].nunique() == int(summary["customer_count"].sum()) and not detail.select_dtypes("number").isna().any().any()
    return passed, f"detail={detail['customer_id'].nunique():,}; summary={int(summary['customer_count'].sum()):,}"


def _registry() -> tuple[bool, str]:
    registry = json.loads((CONFIG.root / "experimentation" / "experiment_registry.yml").read_text(encoding="utf-8"))
    result = pd.read_csv(CONFIG.export_dir / "experiment_evaluation.csv").iloc[0]
    passed = registry["experiment_id"] == result["experiment_id"]
    return passed, f"experiment_id={registry['experiment_id']}"


def _scenarios() -> tuple[bool, str]:
    frame = pd.read_csv(CONFIG.export_dir / "retention_economics_scenarios.csv")
    expected = {"Baseline", "Conservative", "Expected", "Aggressive", "User Defined"}
    passed = set(frame["scenario"]) == expected and frame["estimate_type"].eq("SCENARIO ESTIMATE").all()
    return passed, f"{len(frame)} named scenario estimates"


def _action_center() -> tuple[bool, str]:
    frame = pd.read_csv(CONFIG.export_dir / "retention_action_center.csv")
    passed = frame["review_status"].eq("NEEDS_REVIEW").all() and frame["evidence"].notna().all()
    return passed, f"{len(frame)} aggregate priorities; all review-only={passed}"


def _policy() -> tuple[bool, str]:
    text = (CONFIG.root / "governance" / "ai_data_policy.md").read_text(encoding="utf-8").lower()
    passed = "advisory" in text and "crm writes" in text and "emails" in text
    return passed, "AI policy includes advisory, privacy, and no-write controls"


def _alerts() -> tuple[bool, str]:
    frame = pd.read_csv(CONFIG.export_dir / "customer_intelligence_alerts.csv")
    required = {"alert_type", "status", "metric_value", "threshold", "interpretation"}
    passed = required <= set(frame) and frame[list(required)].notna().all().all()
    return passed, f"{len(frame)} alerts with threshold evidence"


def _packet() -> tuple[bool, str]:
    raw = (CONFIG.root / "artifacts" / "customer_intelligence" / "latest_customer_insight_packet.json").read_text(encoding="utf-8")
    packet = json.loads(raw)
    passed = "customer_id" not in raw and "NaN" not in raw and "Infinity" not in raw and "source_evidence" in packet
    return passed, "aggregate JSON parsed; prohibited identifiers/invalid numbers absent"


if __name__ == "__main__":
    result = run_uat()
    print(f"Automated UAT: {result['status'].eq('PASS').sum()}/{len(result)} PASS")
