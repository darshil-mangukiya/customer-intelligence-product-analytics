from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv


def _read_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _freshness_rows(project_config: ProjectConfig) -> pd.DataFrame:
    rows = []
    watched_paths = list(project_config.mart_dir.glob("*.csv")) + [
        project_config.export_dir / "kpi_summary.csv",
        project_config.export_dir / "stakeholder_insights.csv",
        project_config.export_dir / "next_best_actions.csv",
        project_config.export_dir / "validation_results.csv",
        project_config.export_dir / "model_monitoring_summary.csv",
    ]
    now = pd.Timestamp.now()
    for path in sorted({p for p in watched_paths if p.exists()}):
        age_hours = (now - pd.Timestamp.fromtimestamp(path.stat().st_mtime)).total_seconds() / 3600
        rows.append(
            {
                "asset_name": path.name,
                "asset_path": _repo_relative(path, project_config.root),
                "layer": "mart" if path.parent == project_config.mart_dir else "export",
                "row_count": _row_count(path),
                "age_hours": round(age_hours, 2),
                "freshness_status": "PASS" if age_hours <= 24 * 14 else "STALE",
                "owner": "BI Engineering",
            }
        )
    return pd.DataFrame(rows)


def _data_quality_summary(project_config: ProjectConfig) -> pd.DataFrame:
    validations = _read_optional(project_config.export_dir / "validation_results.csv")
    if validations.empty:
        return pd.DataFrame(
            [
                {
                    "suite": "validation",
                    "checks": 0,
                    "passing_checks": 0,
                    "failing_checks": 0,
                    "severity": "UNKNOWN",
                    "status": "MISSING",
                }
            ]
        )
    grouped = (
        validations.groupby(["suite", "severity", "status"])
        .size()
        .rename("checks")
        .reset_index()
    )
    pivot = grouped.pivot_table(index=["suite", "severity"], columns="status", values="checks", fill_value=0).reset_index()
    for col in ["PASS", "FAIL"]:
        if col not in pivot:
            pivot[col] = 0
    pivot["checks"] = pivot["PASS"] + pivot["FAIL"]
    pivot["passing_checks"] = pivot["PASS"]
    pivot["failing_checks"] = pivot["FAIL"]
    pivot["status"] = pivot["failing_checks"].eq(0).map({True: "PASS", False: "FAIL"})
    return pivot[["suite", "checks", "passing_checks", "failing_checks", "severity", "status"]]


def _rejected_rows(project_config: ProjectConfig) -> pd.DataFrame:
    rows = []
    for path in sorted(project_config.rejected_dir.glob("*.csv")):
        rows.append(
            {
                "source_file": path.name,
                "rejected_rows": _row_count(path),
                "reason": "See rejected source extract",
                "owner": "Data Engineering",
            }
        )
    if not rows:
        rows.append(
            {
                "source_file": "none",
                "rejected_rows": 0,
                "reason": "No rejected row extracts present for current run",
                "owner": "Data Engineering",
            }
        )
    return pd.DataFrame(rows)


def _anomaly_log(project_config: ProjectConfig) -> pd.DataFrame:
    rows = []
    validations = _read_optional(project_config.export_dir / "validation_results.csv")
    if not validations.empty:
        failures = validations.loc[validations["status"].eq("FAIL")]
        for row in failures.to_dict("records"):
            rows.append(
                {
                    "anomaly_type": row["expectation"],
                    "asset_name": row["table_name"],
                    "column_name": row["column_name"],
                    "observed_value": row["observed_value"],
                    "severity": row["severity"],
                    "recommended_action": "Review upstream cleaning, feature logic, or source generation rules.",
                }
            )
    product = _read_optional(project_config.mart_dir / "mart_product_profitability.csv")
    if not product.empty and {"product_id", "return_rate", "discount_dependency"}.issubset(product.columns):
        high_return = product.loc[pd.to_numeric(product["return_rate"], errors="coerce").fillna(0).ge(0.30)].head(25)
        for row in high_return.to_dict("records"):
            rows.append(
                {
                    "anomaly_type": "unusual_return_rate",
                    "asset_name": "mart_product_profitability",
                    "column_name": "return_rate",
                    "observed_value": f"{row['product_id']}={row['return_rate']}",
                    "severity": "MEDIUM",
                    "recommended_action": "Review product content, fulfillment, quality, and return policy exposure.",
                }
            )
    if not rows:
        rows.append(
            {
                "anomaly_type": "none_detected",
                "asset_name": "platform",
                "column_name": "*",
                "observed_value": "No anomalies detected by current checks",
                "severity": "INFO",
                "recommended_action": "Continue monitoring.",
            }
        )
    return pd.DataFrame(rows)


def _pipeline_audit(project_config: ProjectConfig) -> pd.DataFrame:
    manifest = _read_optional(project_config.audit_dir / "pipeline_run_manifest.csv")
    if manifest.empty:
        return pd.DataFrame(
            [
                {
                    "step": "pipeline_manifest",
                    "seconds": 0,
                    "status": "MISSING",
                    "owner": "Data Engineering",
                    "business_impact": "Pipeline run manifest is required for production-style auditability.",
                }
            ]
        )
    audit = manifest.copy()
    audit["owner"] = "Data Engineering"
    audit["business_impact"] = audit["step"].map(
        {
            "synthetic_data_generation": "Source-like data availability.",
            "data_cleaning": "Trusted staged data.",
            "feature_engineering_and_reporting_layer": "BI and model-ready marts.",
            "customer_segmentation": "Segment dashboard and lifecycle strategy.",
            "churn_model": "Churn risk scoring.",
            "clv_model": "Customer value scoring.",
            "kpi_engine": "Executive metric publication.",
            "insights_engine": "Stakeholder recommendation output.",
        }
    ).fillna("Downstream analytics readiness.")
    return audit


def build_enterprise_quality_outputs(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    output_dir = project_config.root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "data_quality_summary.csv": _data_quality_summary(project_config),
        "rejected_rows.csv": _rejected_rows(project_config),
        "anomaly_log.csv": _anomaly_log(project_config),
        "pipeline_audit_log.csv": _pipeline_audit(project_config),
        "mart_freshness_report.csv": _freshness_rows(project_config),
    }
    for filename, frame in outputs.items():
        write_csv(frame, output_dir / filename)

    write_csv(outputs["data_quality_summary.csv"], project_config.export_dir / "data_quality_summary.csv")
    write_csv(outputs["rejected_rows.csv"], project_config.rejected_dir / "rejected_rows.csv")
    write_csv(outputs["anomaly_log.csv"], project_config.audit_dir / "anomaly_log.csv")
    write_csv(outputs["pipeline_audit_log.csv"], project_config.audit_dir / "pipeline_audit_log.csv")
    write_csv(outputs["mart_freshness_report.csv"], project_config.export_dir / "mart_freshness_report.csv")
    return outputs


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Build enterprise data quality and observability outputs.").parse_args()


def main() -> None:
    parse_args()
    outputs = build_enterprise_quality_outputs()
    print(f"Generated {len(outputs)} quality and observability outputs.")


if __name__ == "__main__":
    main()
