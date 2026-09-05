from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


@dataclass
class ValidationResult:
    suite: str
    table_name: str
    expectation: str
    column_name: str
    status: str
    observed_value: str
    threshold: str
    failing_rows: int
    severity: str


def _result(
    suite: str,
    table_name: str,
    expectation: str,
    column_name: str,
    passed: bool,
    observed_value: object,
    threshold: str,
    failing_rows: int = 0,
    severity: str = "HIGH",
) -> ValidationResult:
    return ValidationResult(
        suite=suite,
        table_name=table_name,
        expectation=expectation,
        column_name=column_name,
        status="PASS" if passed else "FAIL",
        observed_value=str(observed_value),
        threshold=threshold,
        failing_rows=int(failing_rows),
        severity=severity,
    )


def _read(path: Path, usecols: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, usecols=usecols)


def _file_rows(path: Path) -> int:
    with path.open("rb") as handle:
        row_count = sum(1 for _ in handle)
    return max(row_count - 1, 0)


def run_validations(project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    project_config.ensure_directories()
    results: list[ValidationResult] = []

    raw_expectations = {
        "transactions": 1_000_000,
        "customers": 100_000,
        "products": 1_000,
        "web_behavior": 500_000,
        "engagement": 100_000,
    }
    for table, min_rows in raw_expectations.items():
        path = project_config.raw_dir / f"{table}.csv"
        observed = _file_rows(path) if path.exists() else 0
        results.append(
            _result(
                "raw_volume",
                table,
                "expect_table_row_count_to_be_at_least",
                "*",
                observed >= min_rows,
                f"{observed:,}",
                f">= {min_rows:,}",
                0 if observed >= min_rows else min_rows - observed,
            )
        )

    dim_customer = _read(project_config.mart_dir / "dim_customer.csv", ["customer_id"])
    dim_product = _read(project_config.mart_dir / "dim_product.csv", ["product_id"])
    fact_orders = _read(
        project_config.mart_dir / "fact_orders.csv",
        ["order_id", "customer_id", "product_id", "net_revenue", "return_adjusted_profit", "return_flag", "order_status"],
    )
    churn = _read(project_config.mart_dir / "mart_churn_risk.csv", ["customer_id", "churn_probability", "churn_risk_tier"])
    cohort = _read(project_config.mart_dir / "mart_cohort_retention.csv", ["cohort_month", "cohort_index", "retention_rate"])
    product = _read(project_config.mart_dir / "mart_product_profitability.csv", ["product_id", "return_rate", "return_adjusted_margin"])
    clv = _read(project_config.mart_dir / "mart_clv.csv", ["customer_id", "predicted_12m_clv", "clv_band"])

    unique_checks = [
        ("dim_customer", dim_customer, "customer_id"),
        ("dim_product", dim_product, "product_id"),
        ("fact_orders", fact_orders, "order_id"),
        ("mart_churn_risk", churn, "customer_id"),
        ("mart_clv", clv, "customer_id"),
    ]
    for table, df, column in unique_checks:
        duplicates = int(df[column].duplicated().sum())
        results.append(
            _result(
                "key_integrity",
                table,
                "expect_column_values_to_be_unique",
                column,
                duplicates == 0,
                duplicates,
                "= 0",
                duplicates,
            )
        )
        nulls = int(df[column].isna().sum())
        results.append(
            _result(
                "key_integrity",
                table,
                "expect_column_values_to_not_be_null",
                column,
                nulls == 0,
                nulls,
                "= 0",
                nulls,
            )
        )

    range_checks = [
        ("fact_orders", fact_orders, "net_revenue", 0, np.inf),
        ("mart_churn_risk", churn, "churn_probability", 0, 1),
        ("mart_cohort_retention", cohort, "retention_rate", 0, 1),
        ("mart_product_profitability", product, "return_rate", 0, 1),
    ]
    for table, df, column, lower, upper in range_checks:
        values = pd.to_numeric(df[column], errors="coerce")
        failing = int((values.lt(lower) | values.gt(upper) | values.isna()).sum())
        results.append(
            _result(
                "numeric_ranges",
                table,
                "expect_column_values_to_be_between",
                column,
                failing == 0,
                f"min={values.min():.4f}, max={values.max():.4f}",
                f"{lower} to {upper}",
                failing,
            )
        )

    accepted_status = {"Completed", "Returned", "Cancelled", "Unknown"}
    bad_status = int(~fact_orders["order_status"].isin(accepted_status).sum()) if False else int((~fact_orders["order_status"].isin(accepted_status)).sum())
    results.append(
        _result(
            "accepted_values",
            "fact_orders",
            "expect_column_values_to_be_in_set",
            "order_status",
            bad_status == 0,
            f"{bad_status:,} invalid",
            str(sorted(accepted_status)),
            bad_status,
        )
    )

    analytical_files = {
        "descriptive_statistics": ["group", "metric", "sample_size", "mean", "median", "standard_deviation", "quantile_25", "quantile_75"],
        "statistical_test_results": ["analysis_id", "p_value", "holm_adjusted_p_value", "confidence_interval_low", "confidence_interval_high", "effect_size", "statistically_significant", "significant_after_holm"],
        "experiment_evaluation": ["experiment_id", "control_n", "treatment_n", "p_value", "confidence_interval_low", "confidence_interval_high"],
        "churn_driver_analysis": ["metric_or_driver", "p_value", "importance_or_strength"],
        "clv_driver_analysis": ["metric_or_driver", "p_value", "importance_or_strength"],
        "regression_analysis": ["predictor", "p_value", "ci_low", "ci_high"],
    }
    for name, expected_columns in analytical_files.items():
        path = project_config.export_dir / f"{name}.csv"
        exists = path.exists()
        results.append(_result("analytical_outputs", name, "expect_output_file_to_exist", "*", exists, exists, "True", int(not exists)))
        if not exists:
            continue
        analytical = _read(path)
        missing = sorted(set(expected_columns) - set(analytical.columns))
        results.append(_result("analytical_outputs", name, "expect_required_columns_to_exist", "*", not missing, missing or "none", "none missing", len(missing)))
        key = "analysis_id" if "analysis_id" in analytical else "experiment_id" if "experiment_id" in analytical else "metric_or_driver" if "metric_or_driver" in analytical else "predictor" if "predictor" in analytical else None
        if key is None:
            analytical["_compound_key"] = analytical["group"].astype(str) + "::" + analytical["metric"].astype(str)
            key = "_compound_key"
        duplicates = int(analytical[key].duplicated().sum())
        results.append(_result("analytical_outputs", name, "expect_analytical_ids_to_be_unique", key, duplicates == 0, duplicates, "= 0", duplicates))
        if "p_value" in analytical:
            p_values = pd.to_numeric(analytical["p_value"], errors="coerce")
            invalid = int((p_values.isna() | ~p_values.between(0, 1)).sum())
            results.append(_result("analytical_outputs", name, "expect_p_values_between_zero_and_one", "p_value", invalid == 0, invalid, "= 0", invalid))
        low_name = "confidence_interval_low" if "confidence_interval_low" in analytical else "ci_low"
        high_name = "confidence_interval_high" if "confidence_interval_high" in analytical else "ci_high"
        if low_name in analytical and high_name in analytical:
            low = pd.to_numeric(analytical[low_name], errors="coerce")
            high = pd.to_numeric(analytical[high_name], errors="coerce")
            comparable = low.notna() & high.notna()
            invalid = int((low[comparable] > high[comparable]).sum())
            results.append(_result("analytical_outputs", name, "expect_confidence_interval_ordering", low_name, invalid == 0, invalid, "= 0", invalid))

    for report_name in ["statistical_analysis_report.md", "executive_customer_strategy.md"]:
        report_path = project_config.report_dir / report_name
        exists = report_path.exists() and report_path.stat().st_size > 500
        results.append(_result("analytical_reports", report_name, "expect_generated_report_to_exist", "*", exists, exists, "True and >500 bytes", int(not exists)))

    r_result_path = project_config.export_dir / "r_experiment_validation.csv"
    reconciliation_path = project_config.export_dir / "python_r_statistical_reconciliation.csv"
    if r_result_path.exists() or reconciliation_path.exists():
        r_required = {"analysis_name", "control_n", "treatment_n", "control_rate", "treatment_rate", "absolute_lift", "relative_lift", "ci_lower", "ci_upper", "test_statistic", "p_value", "statistically_significant"}
        r_result = _read(r_result_path) if r_result_path.exists() else pd.DataFrame()
        missing = sorted(r_required - set(r_result.columns))
        results.append(_result("r_statistical_validation", "r_experiment_validation", "expect_required_columns_to_exist", "*", not missing, missing or "none", "none missing", len(missing)))
        if not r_result.empty and "p_value" in r_result:
            p_values = pd.to_numeric(r_result["p_value"], errors="coerce")
            invalid = int((p_values.isna() | ~p_values.between(0, 1)).sum())
            results.append(_result("r_statistical_validation", "r_experiment_validation", "expect_p_values_between_zero_and_one", "p_value", invalid == 0, invalid, "= 0", invalid))
        reconciliation = _read(reconciliation_path) if reconciliation_path.exists() else pd.DataFrame()
        required_metrics = {"control_n", "treatment_n", "control_rate", "treatment_rate", "absolute_lift", "relative_lift", "ci_lower", "ci_upper", "p_value", "statistically_significant"}
        present_metrics = set(reconciliation.get("metric", pd.Series(dtype=str)))
        failed = int(reconciliation.get("status", pd.Series(dtype=str)).ne("PASS").sum()) if not reconciliation.empty else 1
        missing_metrics = sorted(required_metrics - present_metrics)
        results.append(_result("r_statistical_validation", "python_r_statistical_reconciliation", "expect_required_metrics_to_pass", "status", failed == 0 and not missing_metrics, f"failed={failed}, missing={missing_metrics}", "no failures or missing metrics", failed + len(missing_metrics)))

    accepted_risk = {"Low", "Medium", "High", "Critical"}
    bad_risk = int((~churn["churn_risk_tier"].isin(accepted_risk)).sum())
    results.append(
        _result(
            "accepted_values",
            "mart_churn_risk",
            "expect_column_values_to_be_in_set",
            "churn_risk_tier",
            bad_risk == 0,
            f"{bad_risk:,} invalid",
            str(sorted(accepted_risk)),
            bad_risk,
        )
    )

    missing_customers = int((~fact_orders["customer_id"].isin(set(dim_customer["customer_id"]))).sum())
    missing_products = int((~fact_orders["product_id"].isin(set(dim_product["product_id"]))).sum())
    results.append(
        _result(
            "referential_integrity",
            "fact_orders",
            "expect_foreign_key_to_exist",
            "customer_id",
            missing_customers == 0,
            f"{missing_customers:,} missing customer keys",
            "all customer_id values in dim_customer",
            missing_customers,
        )
    )
    results.append(
        _result(
            "referential_integrity",
            "fact_orders",
            "expect_foreign_key_to_exist",
            "product_id",
            missing_products == 0,
            f"{missing_products:,} missing product keys",
            "all product_id values in dim_product",
            missing_products,
        )
    )

    kpis = _read(project_config.export_dir / "kpi_summary.csv")
    revenue_kpi = kpis.loc[kpis["kpi_name"].eq("Total Net Revenue"), "value"]
    if not revenue_kpi.empty:
        fact_revenue = float(fact_orders["net_revenue"].sum())
        delta = abs(fact_revenue - float(revenue_kpi.iloc[0]))
        results.append(
            _result(
                "metric_reconciliation",
                "fact_orders",
                "expect_total_net_revenue_to_match_kpi_export",
                "net_revenue",
                delta <= 1.0,
                f"delta={delta:.2f}",
                "<= 1.00",
                int(delta > 1.0),
            )
        )

    freshness_path = project_config.audit_dir / "pipeline_run_manifest.csv"
    age_days = (pd.Timestamp.now() - pd.Timestamp.fromtimestamp(freshness_path.stat().st_mtime)).days if freshness_path.exists() else 999
    results.append(
        _result(
            "freshness",
            "pipeline_run_manifest",
            "expect_pipeline_outputs_to_be_recent",
            "modified_time",
            age_days <= 14,
            f"{age_days} days old",
            "<= 14 days",
            int(age_days > 14),
            "MEDIUM",
        )
    )

    upgrade_files = [
        "experiment_design.csv", "experiment_srm_validation.csv", "segment_migration_summary.csv",
        "retention_economics_scenarios.csv", "retention_action_center.csv",
        "customer_intelligence_reconciliation.csv", "ai_evaluation_results.csv",
    ]
    for filename in upgrade_files:
        path = project_config.export_dir / filename
        passed = path.exists() and path.stat().st_size > 20
        results.append(_result("customer_intelligence_upgrade", filename, "expect_generated_output_to_exist_and_be_nonempty", "*", passed, path.stat().st_size if path.exists() else 0, "> 20 bytes", 0 if passed else 1))

    reconciliation_path = project_config.export_dir / "customer_intelligence_reconciliation.csv"
    if reconciliation_path.exists():
        reconciliation = pd.read_csv(reconciliation_path)
        failed = int(reconciliation["status"].ne("PASS").sum())
        results.append(_result("reconciliation", "customer_intelligence_reconciliation", "expect_all_source_output_checks_to_pass", "status", failed == 0, f"{failed} failed", "0 failed", failed))

    packet_path = project_config.root / "artifacts" / "customer_intelligence" / "latest_customer_insight_packet.json"
    packet_valid = False
    if packet_path.exists():
        raw_packet = packet_path.read_text(encoding="utf-8")
        packet = json.loads(raw_packet)
        required_packet_keys = {"reporting_period", "customer_kpis", "segment_summary", "segment_migrations", "churn_summary", "churn_drivers", "clv_summary", "cohort_summary", "experiment_results", "experiment_validity", "python_r_reconciliation", "retention_scenarios", "revenue_or_clv_exposure", "priority_actions", "data_quality_warnings", "source_evidence", "generated_at"}
        packet_valid = required_packet_keys <= packet.keys() and "NaN" not in raw_packet and "Infinity" not in raw_packet and "customer_id" not in raw_packet
    results.append(_result("customer_intelligence_upgrade", "latest_customer_insight_packet", "expect_governed_finite_aggregate_packet", "schema", packet_valid, packet_valid, "required keys; no IDs/NaN/Infinity", 0 if packet_valid else 1))

    for rel_path in ["business_analysis/requirements_traceability_matrix.xlsx", "business_analysis/uat_test_plan.xlsx"]:
        artifact = project_config.root / rel_path
        passed = artifact.exists() and artifact.stat().st_size > 5_000
        results.append(_result("business_analysis", rel_path, "expect_real_xlsx_artifact", "file", passed, artifact.stat().st_size if artifact.exists() else 0, "> 5,000 bytes", 0 if passed else 1))

    output = pd.DataFrame([r.__dict__ for r in results])
    write_csv(output, project_config.export_dir / "validation_results.csv")
    _write_validation_report(output, project_config)
    return output


def _write_validation_report(results: pd.DataFrame, project_config: ProjectConfig) -> None:
    failed = results.loc[results["status"].eq("FAIL")]
    lines = [
        "# Validation Report",
        "",
        f"- Total checks: {len(results):,}",
        f"- Passing checks: {results['status'].eq('PASS').sum():,}",
        f"- Failing checks: {len(failed):,}",
        "",
        "| Suite | Table | Expectation | Column | Status | Observed | Threshold | Failing Rows | Severity |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for row in results.to_dict("records"):
        lines.append(
            f"| {row['suite']} | {row['table_name']} | `{row['expectation']}` | `{row['column_name']}` | "
            f"{row['status']} | {row['observed_value']} | {row['threshold']} | {row['failing_rows']} | {row['severity']} |"
        )
    if failed.empty:
        lines.extend(["", "## Result", "All critical data quality gates passed."])
    else:
        lines.extend(["", "## Failed Checks"])
        for row in failed.to_dict("records"):
            lines.append(f"- {row['table_name']}.{row['column_name']}: {row['expectation']} failed with {row['observed_value']}.")
    write_markdown(lines, project_config.report_dir / "validation_report.md")


def main() -> None:
    run_validations()


if __name__ == "__main__":
    main()
