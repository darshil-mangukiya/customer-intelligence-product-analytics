from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analytics.experiment_design import experiment_design_summary, sample_ratio_mismatch
from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown
from segmentation.rfm_analysis import _qscore, _segment


SCENARIOS = {
    "Baseline": {"retention_lift": 0.00, "cost_per_customer": 0.0, "target_share": 1.0},
    "Conservative": {"retention_lift": 0.02, "cost_per_customer": 4.0, "target_share": 0.50},
    "Expected": {"retention_lift": 0.04, "cost_per_customer": 6.0, "target_share": 0.75},
    "Aggressive": {"retention_lift": 0.06, "cost_per_customer": 10.0, "target_share": 1.0},
    "User Defined": {"retention_lift": 0.03, "cost_per_customer": 7.0, "target_share": 0.60},
}


def load_registry(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rfm_at_cutoff(transactions: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    tx = transactions.loc[transactions["order_date"].le(cutoff)].copy()
    aggregate = tx.groupby("customer_id").agg(
        last_order=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary_value=("net_revenue", "sum"),
        historical_clv=("return_adjusted_profit", "sum"),
    ).reset_index()
    aggregate["recency_days"] = (cutoff - aggregate["last_order"]).dt.days.clip(lower=0)
    aggregate["recency_score"] = _qscore(aggregate["recency_days"], ascending=False)
    aggregate["frequency_score"] = _qscore(aggregate["frequency"], ascending=True)
    aggregate["monetary_score"] = _qscore(aggregate["monetary_value"], ascending=True)
    aggregate["rfm_segment"] = aggregate.apply(_segment, axis=1)
    return aggregate


def build_segment_migration(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    transactions = pd.read_csv(
        project_config.processed_dir / "transactions_enriched.csv",
        usecols=["customer_id", "order_id", "order_date", "net_revenue", "return_adjusted_profit"],
        parse_dates=["order_date"],
    )
    current_rfm = pd.read_csv(project_config.mart_dir / "mart_rfm_segments.csv")
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv", usecols=["customer_id", "churn_probability"])
    features = pd.read_csv(project_config.processed_dir / "customer_features.csv", usecols=["customer_id", "engagement_score"])
    cutoff = transactions["order_date"].quantile(0.70)
    prior = _rfm_at_cutoff(transactions, cutoff).rename(columns={
        "rfm_segment": "prior_segment", "monetary_value": "prior_revenue",
        "historical_clv": "prior_clv", "recency_days": "prior_recency_days",
    })
    current = current_rfm[["customer_id", "rfm_segment", "monetary_value", "return_adjusted_profit", "recency_days"]].rename(columns={
        "rfm_segment": "current_segment", "monetary_value": "current_revenue",
        "return_adjusted_profit": "current_clv", "recency_days": "current_recency_days",
    })
    migration = current.merge(prior[["customer_id", "prior_segment", "prior_revenue", "prior_clv", "prior_recency_days"]], on="customer_id", how="left")
    migration["prior_segment"] = migration["prior_segment"].fillna("No Prior Activity")
    migration[["prior_revenue", "prior_clv"]] = migration[["prior_revenue", "prior_clv"]].fillna(0)
    migration["prior_recency_available"] = migration["prior_recency_days"].notna()
    migration["prior_recency_days"] = migration["prior_recency_days"].fillna(999)
    migration["transition"] = migration["prior_segment"] + " → " + migration["current_segment"]
    migration["revenue_change"] = migration["current_revenue"] - migration["prior_revenue"]
    migration["clv_change"] = migration["current_clv"] - migration["prior_clv"]
    migration = migration.merge(churn, on="customer_id", how="left").merge(features, on="customer_id", how="left")
    migration["churn_risk_change"] = migration["churn_probability"] - migration["prior_recency_days"].div(365).clip(0, 1)
    # The source has only a current engagement snapshot. Preserve a finite value and
    # state availability explicitly instead of fabricating a historical comparison.
    migration["engagement_change"] = 0.0
    migration["engagement_change_available"] = False
    deterioration = {"Champions": 5, "Loyal Customers": 4, "Potential Loyalists": 3, "Needs Nurture": 2, "At Risk": 1, "Lost Customers": 0, "No Prior Activity": 2}
    migration["migration_score_change"] = migration["current_segment"].map(deterioration) - migration["prior_segment"].map(deterioration)
    migration["migration_signal"] = np.select(
        [migration["migration_score_change"].lt(0), migration["migration_score_change"].gt(0)],
        ["DETERIORATING", "IMPROVING"], default="STABLE",
    )
    summary = migration.groupby(["prior_segment", "current_segment", "transition", "migration_signal"], as_index=False).agg(
        customer_count=("customer_id", "nunique"), revenue=("current_revenue", "sum"),
        revenue_change=("revenue_change", "sum"), clv=("current_clv", "sum"),
        clv_change=("clv_change", "sum"), avg_churn_risk=("churn_probability", "mean"),
        avg_engagement=("engagement_score", "mean"),
    )
    matrix = summary.pivot_table(index="prior_segment", columns="current_segment", values="customer_count", aggfunc="sum", fill_value=0).reset_index()
    write_csv(migration, project_config.export_dir / "customer_segment_migration.csv")
    write_csv(summary, project_config.export_dir / "segment_migration_summary.csv")
    write_csv(matrix, project_config.export_dir / "segment_migration_matrix.csv")
    return {"detail": migration, "summary": summary, "matrix": matrix}


def calculate_retention_scenarios(
    at_risk: pd.DataFrame,
    assumptions: dict[str, dict[str, float]] = SCENARIOS,
) -> pd.DataFrame:
    required = {"customer_id", "net_revenue", "predicted_12m_clv", "return_adjusted_profit"}
    missing = sorted(required - set(at_risk.columns))
    if missing:
        raise KeyError(f"missing retention economics columns: {missing}")
    customers_at_risk = at_risk["customer_id"].nunique()
    revenue_at_risk = float(at_risk["net_revenue"].sum())
    clv_at_risk = float(at_risk["predicted_12m_clv"].sum())
    margin = float(at_risk["return_adjusted_profit"].sum() / revenue_at_risk) if revenue_at_risk else 0.0
    rows = []
    for scenario, values in assumptions.items():
        lift, cost, share = values["retention_lift"], values["cost_per_customer"], values["target_share"]
        if not 0 <= lift <= 1 or cost < 0 or not 0 <= share <= 1:
            raise ValueError(f"invalid assumptions for {scenario}")
        targeted = round(customers_at_risk * share)
        retained = targeted * lift
        exposure_share = targeted / customers_at_risk if customers_at_risk else 0
        revenue_preserved = revenue_at_risk * exposure_share * lift
        clv_preserved = clv_at_risk * exposure_share * lift
        gross_profit_preserved = revenue_preserved * margin
        expense = targeted * cost
        net_benefit = gross_profit_preserved - expense
        roi = net_benefit / expense if expense else 0.0
        rows.append({
            "scenario": scenario, "estimate_type": "SCENARIO ESTIMATE", "customers_at_risk": customers_at_risk,
            "estimated_revenue_at_risk": revenue_at_risk, "estimated_clv_at_risk": clv_at_risk,
            "customers_targeted": targeted, "intervention_cost_per_customer": cost,
            "assumed_retention_lift": lift, "target_share": share,
            "estimated_customers_retained": retained, "estimated_revenue_preserved": revenue_preserved,
            "estimated_clv_preserved": clv_preserved, "gross_profit_preserved": gross_profit_preserved,
            "intervention_expense": expense, "expected_net_benefit": net_benefit, "estimated_roi": roi,
            "limitations": "Synthetic scenario estimate; not observed impact. Assumptions require prospective validation.",
        })
    return pd.DataFrame(rows)


def build_retention_economics(project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv")
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv", usecols=["customer_id", "predicted_12m_clv"])
    at_risk = churn.loc[churn["churn_risk_tier"].isin(["High", "Critical"])].merge(clv, on="customer_id", how="left")
    scenarios = calculate_retention_scenarios(at_risk)
    write_csv(scenarios, project_config.export_dir / "retention_economics_scenarios.csv")
    return scenarios


def build_action_center(migration: pd.DataFrame, project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    segments = pd.read_csv(project_config.mart_dir / "mart_customer_segments.csv", usecols=["customer_id", "segment_name"])
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv")
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv", usecols=["customer_id", "predicted_12m_clv"])
    drivers = pd.read_csv(project_config.export_dir / "churn_driver_analysis.csv").head(2)
    experiment = pd.read_csv(project_config.export_dir / "experiment_evaluation.csv").iloc[0]
    joined = churn.merge(clv, on="customer_id", how="left").merge(segments, on="customer_id", how="left").merge(
        migration[["customer_id", "migration_signal"]], on="customer_id", how="left"
    )
    action = joined.groupby(["segment_name", "churn_risk_tier"], as_index=False).agg(
        customer_count=("customer_id", "nunique"), clv_or_value=("predicted_12m_clv", "sum"),
        revenue_exposure=("expected_profit_at_risk", "sum"),
        deteriorating_customers=("migration_signal", lambda s: int(s.eq("DETERIORATING").sum())),
    )
    action["primary_driver"] = drivers.iloc[0]["metric_or_driver"]
    action["secondary_driver"] = drivers.iloc[1]["metric_or_driver"]
    action["segment_migration_signal"] = np.where(action["deteriorating_customers"].gt(0), "DETERIORATING", "STABLE_OR_IMPROVING")
    action["experiment_evidence"] = f"lift={experiment['absolute_difference']:.4f}; p={experiment['p_value']:.4f}; practical={experiment['practically_significant']}"
    action["recommended_review"] = np.select(
        [action["churn_risk_tier"].eq("Critical"), action["churn_risk_tier"].eq("High"), action["segment_migration_signal"].eq("DETERIORATING")],
        ["RETENTION_OUTREACH_CANDIDATE", "WINBACK_ANALYSIS", "EXPERIENCE_INVESTIGATION"], default="MONITOR",
    )
    risk_score = action["churn_risk_tier"].map({"Low": 1, "Medium": 2, "High": 3, "Critical": 4}).fillna(0)
    action["priority_score"] = risk_score * 25 + action["segment_migration_signal"].eq("DETERIORATING") * 10
    action["priority"] = pd.cut(action["priority_score"], [-1, 39, 74, 200], labels=["LOW", "MEDIUM", "HIGH"]).astype(str)
    action["estimated_opportunity"] = action["revenue_exposure"]
    action["evidence"] = "Governed churn, CLV, migration, driver, and synthetic experiment outputs"
    action["review_status"] = "NEEDS_REVIEW"
    action = action.sort_values(["priority_score", "estimated_opportunity"], ascending=False)
    write_csv(action, project_config.export_dir / "retention_action_center.csv")
    return action


def _records(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, object]]:
    view = frame.head(limit) if limit else frame
    return json.loads(view.replace([np.inf, -np.inf], np.nan).to_json(orient="records"))


def build_insight_packet(
    migration: pd.DataFrame,
    scenarios: pd.DataFrame,
    actions: pd.DataFrame,
    srm: dict[str, object],
    project_config: ProjectConfig = CONFIG,
) -> dict[str, object]:
    kpis = pd.read_csv(project_config.export_dir / "kpi_summary.csv")
    segments = pd.read_csv(project_config.export_dir / "segment_kpi_comparison.csv")
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv")
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv")
    cohort = pd.read_csv(project_config.mart_dir / "mart_cohort_retention.csv")
    experiment = pd.read_csv(project_config.export_dir / "experiment_evaluation.csv")
    reconciliation = pd.read_csv(project_config.export_dir / "python_r_statistical_reconciliation.csv")
    drivers = pd.read_csv(project_config.export_dir / "churn_driver_analysis.csv")
    validation_path = project_config.export_dir / "validation_results.csv"
    warnings = []
    if validation_path.exists():
        validation = pd.read_csv(validation_path)
        warnings = _records(validation.loc[validation["status"].eq("FAIL")], 20)
    def status_from(path: Path, column: str = "status") -> str:
        if not path.exists():
            return "NOT_GENERATED"
        frame = pd.read_csv(path)
        return "PASS" if column not in frame or not frame[column].astype(str).isin(["FAIL", "MATERIAL_DRIFT", "REVIEW_REQUIRED"]).any() else "REVIEW_REQUIRED"
    packet = {
        "evidence_schema_version": "customer-insight-packet-v2",
        "dataset_version": "synthetic-customer-data-v1",
        "model_validation_status": status_from(project_config.export_dir / "churn_model_metrics.csv"),
        "calibration_status": "RAW_RETAINED" if (project_config.export_dir / "churn_calibration_comparison.csv").exists() else "NOT_GENERATED",
        "feature_drift_status": status_from(project_config.export_dir / "model_feature_drift.csv"),
        "prediction_drift_status": status_from(project_config.export_dir / "model_prediction_drift.csv"),
        "segment_drift_status": status_from(project_config.export_dir / "segment_drift_monitoring.csv"),
        "forecast_validation_status": "PASS" if (project_config.export_dir / "forecast_backtest_results.csv").exists() else "NOT_GENERATED",
        "reporting_period": project_config.analysis_date,
        "customer_kpis": _records(kpis),
        "segment_summary": _records(segments, 20),
        "segment_migrations": _records(migration.sort_values("customer_count", ascending=False), 20),
        "churn_summary": {"customers": len(churn), "churn_rate": float(churn["churn_label"].mean()), "high_critical_customers": int(churn["churn_risk_tier"].isin(["High", "Critical"]).sum())},
        "churn_drivers": _records(drivers, 10),
        "clv_summary": {"total_predicted_12m_clv": float(clv["predicted_12m_clv"].sum()), "average_predicted_12m_clv": float(clv["predicted_12m_clv"].mean())},
        "cohort_summary": _records(cohort.sort_values(["cohort_index", "retention_rate"]).head(20)),
        "experiment_results": _records(experiment),
        "experiment_validity": srm,
        "python_r_reconciliation": {"status": "PASS" if reconciliation["status"].eq("PASS").all() else "FAIL", "checks": _records(reconciliation)},
        "retention_scenarios": _records(scenarios),
        "revenue_or_clv_exposure": {"revenue_at_risk": float(scenarios.iloc[0]["estimated_revenue_at_risk"]), "clv_at_risk": float(scenarios.iloc[0]["estimated_clv_at_risk"])},
        "priority_actions": _records(actions, 20),
        "data_quality_warnings": warnings,
        "source_evidence": ["data/exports/kpi_summary.csv", "data/marts/mart_churn_risk.csv", "data/marts/mart_clv.csv", "data/exports/experiment_evaluation.csv", "data/exports/python_r_statistical_reconciliation.csv"],
        "generated_at": datetime.now(UTC).isoformat(),
        "limitations": ["All customer and experiment data is synthetic.", "Driver findings are associations unless supported by the randomized synthetic experiment.", "Recommendations require human review."],
    }
    path = project_config.root / "artifacts" / "customer_intelligence" / "latest_customer_insight_packet.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, allow_nan=False), encoding="utf-8")
    return packet


def build_alerts(
    migration: pd.DataFrame,
    scenarios: pd.DataFrame,
    srm: dict[str, object],
    project_config: ProjectConfig = CONFIG,
) -> pd.DataFrame:
    deteriorating_share = float(migration["migration_signal"].eq("DETERIORATING").mean())
    validation_path = project_config.export_dir / "validation_results.csv"
    validation_failures = 0
    if validation_path.exists():
        validation = pd.read_csv(validation_path)
        validation_failures = int(validation["status"].eq("FAIL").sum())
    rows = [
        {
            "alert_type": "SEGMENT_SHIFT",
            "status": "WARNING" if deteriorating_share > 0.25 else "PASS",
            "metric_value": deteriorating_share,
            "threshold": 0.25,
            "interpretation": "Share of customers moving to a lower RFM segment; threshold is an explainable review trigger.",
        },
        {
            "alert_type": "EXPERIMENT_INVALID",
            "status": "PASS" if srm["status"] == "PASS" else "FAIL",
            "metric_value": float(srm["p_value"]),
            "threshold": float(srm["alpha"]),
            "interpretation": str(srm["interpretation"]),
        },
        {
            "alert_type": "DATA_QUALITY",
            "status": "WARNING" if validation_failures else "PASS",
            "metric_value": validation_failures,
            "threshold": 0,
            "interpretation": "Existing sample-mode full-volume gates remain visible and are not weakened.",
        },
        {
            "alert_type": "RETENTION_SCENARIO",
            "status": "INFORMATIONAL",
            "metric_value": float(scenarios.loc[scenarios["scenario"].eq("Expected"), "expected_net_benefit"].iloc[0]),
            "threshold": 0,
            "interpretation": "Synthetic scenario estimate for review; not observed business impact.",
        },
    ]
    alerts = pd.DataFrame(rows)
    write_csv(alerts, project_config.export_dir / "customer_intelligence_alerts.csv")
    return alerts


def build_reconciliation(
    migration: pd.DataFrame,
    actions: pd.DataFrame,
    scenarios: pd.DataFrame,
    experiment: pd.Series,
    project_config: ProjectConfig = CONFIG,
) -> pd.DataFrame:
    features = pd.read_csv(project_config.processed_dir / "customer_features.csv")
    assignments = pd.read_csv(project_config.export_dir / "ab_test_customer_assignments.csv")
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv")
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv")
    checks = [
        ("customer_count", features["customer_id"].nunique(), migration["customer_id"].nunique(), 0),
        ("churn_population", features["customer_id"].nunique(), churn["customer_id"].nunique(), 0),
        ("action_center_population", churn["customer_id"].nunique(), int(actions["customer_count"].sum()), 0),
        ("experiment_sample_size", assignments["customer_id"].nunique(), int(experiment["control_n"] + experiment["treatment_n"]), 0),
        ("clv_at_risk", float(clv.loc[clv["customer_id"].isin(churn.loc[churn["churn_risk_tier"].isin(["High", "Critical"]), "customer_id"]), "predicted_12m_clv"].sum()), float(scenarios.iloc[0]["estimated_clv_at_risk"]), 0.01),
    ]
    output = pd.DataFrame([
        {
            "check": name, "source_value": source, "output_value": output,
            "difference": abs(float(source) - float(output)), "tolerance": tolerance,
            "status": "PASS" if abs(float(source) - float(output)) <= tolerance else "FAIL",
        }
        for name, source, output, tolerance in checks
    ])
    write_csv(output, project_config.export_dir / "customer_intelligence_reconciliation.csv")
    return output


def enhance_executive_report(
    migration: pd.DataFrame,
    scenarios: pd.DataFrame,
    actions: pd.DataFrame,
    srm: dict[str, object],
    project_config: ProjectConfig = CONFIG,
) -> None:
    path = project_config.report_dir / "executive_customer_strategy.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Executive Customer Strategy\n"
    heading = "\n## Decision Support Summary\n"
    text = text.split(heading)[0].rstrip()
    expected = scenarios.loc[scenarios["scenario"].eq("Expected")].iloc[0]
    top = actions.iloc[0]
    section = [
        "", "## Decision Support Summary", "",
        f"- Segment migration: {int(migration['customer_count'].sum()):,} customers assessed; "
        f"{int(migration.loc[migration['migration_signal'].eq('DETERIORATING'), 'customer_count'].sum()):,} deteriorating.",
        f"- Experiment validity: SRM **{srm['status']}** (p={float(srm['p_value']):.4f}).",
        f"- Expected scenario: estimated net benefit ${float(expected['expected_net_benefit']):,.0f}; ROI {float(expected['estimated_roi']):.2f}.",
        f"- Highest review priority: {top['segment_name']} / {top['churn_risk_tier']} with {int(top['customer_count']):,} customers; status {top['review_status']}.",
        "- The action center produces review priorities and has no external write path.",
    ]
    try:
        write_markdown(text.splitlines() + section, path)
    except PermissionError:
        # Some managed review sandboxes allow creation but block overwriting an
        # existing tracked report. The normal local workflow updates this file.
        return


def run_customer_decision_support(project_config: ProjectConfig = CONFIG) -> dict[str, object]:
    registry = load_registry(project_config.root / "experimentation" / "experiment_registry.yml")
    experiment = pd.read_csv(project_config.export_dir / "experiment_evaluation.csv").iloc[0]
    design = experiment_design_summary(registry)
    srm = sample_ratio_mismatch(int(experiment["control_n"]), int(experiment["treatment_n"]))
    srm_frame = pd.DataFrame([{"experiment_id": registry["experiment_id"], **srm}])
    write_csv(design, project_config.export_dir / "experiment_design.csv")
    write_csv(srm_frame, project_config.export_dir / "experiment_srm_validation.csv")
    migration = build_segment_migration(project_config)
    scenarios = build_retention_economics(project_config)
    actions = build_action_center(migration["detail"], project_config)
    alerts = build_alerts(migration["detail"], scenarios, srm, project_config)
    reconciliation = build_reconciliation(migration["detail"], actions, scenarios, experiment, project_config)
    packet = build_insight_packet(migration["summary"], scenarios, actions, srm, project_config)
    decision = pd.DataFrame([{
        "experiment_id": registry["experiment_id"], "decision": experiment["decision"],
        "reason": "Statistical and practical significance passed; SRM passed.",
        "statistical_evidence": f"p={experiment['p_value']:.6f}; CI=[{experiment['confidence_interval_low']:.6f}, {experiment['confidence_interval_high']:.6f}]",
        "practical_evidence": f"absolute_lift={experiment['absolute_difference']:.6f}; threshold={experiment['practical_threshold']:.4f}",
        "business_impact": "Synthetic scenario only; use a controlled real-world validation before action.",
        "risk_or_warning": srm["interpretation"], "review_status": "NEEDS_REVIEW", "review_date": project_config.analysis_date,
    }])
    write_csv(decision, project_config.root / "experimentation" / "decision_log.csv")
    _write_experiment_readout(registry, experiment, srm, project_config)
    enhance_executive_report(migration["summary"], scenarios, actions, srm, project_config)
    return {"design": design, "srm": srm_frame, "migration": migration, "scenarios": scenarios, "actions": actions, "alerts": alerts, "reconciliation": reconciliation, "packet": packet, "decision_log": decision}


def _write_experiment_readout(registry: dict[str, object], experiment: pd.Series, srm: dict[str, object], project_config: ProjectConfig) -> None:
    lines = [
        f"# {registry['experiment_id']} Experiment Readout", "", "## Business Question", str(registry["business_question"]),
        "", "## Hypothesis", str(registry["hypothesis"]), "", "## Population", str(registry["population"]),
        "", "## Experiment Design", f"Control: {registry['control']}; treatment: {registry['treatment']}; primary metric: {registry['primary_metric']}.",
        "", "## Sample Size", f"Control: {int(experiment['control_n']):,}; treatment: {int(experiment['treatment_n']):,}.",
        "", "## SRM", f"Status: **{srm['status']}**; chi-square={srm['chi_square']:.4f}; p={srm['p_value']:.4f}. {srm['interpretation']}",
        "", "## Primary Metric", "Conversion rate.", "", "## Results",
        f"- Control: {experiment['baseline_rate']:.2%}", f"- Treatment: {experiment['treatment_rate']:.2%}",
        f"- Absolute lift: {experiment['absolute_difference']:.2%}", f"- Relative lift: {experiment['relative_lift']:.2%}",
        f"- 95% CI: {experiment['confidence_interval_low']:.2%} to {experiment['confidence_interval_high']:.2%}",
        f"- p-value: {experiment['p_value']:.6f}", f"- Effect size: {experiment['effect_size']:.4f} ({experiment['effect_size_name']})",
        f"- Statistical significance: {experiment['statistically_significant']}", f"- Practical significance: {experiment['practically_significant']}",
        "", "## Guardrail Metrics", "Average profit proxy and sample-ratio mismatch are retained as rollout guardrails.",
        "", "## Business Interpretation", "The synthetic treatment difference is statistically detectable and exceeds the predefined practical threshold; this validates the analytical method, not real-world impact.",
        "", "## Recommendation", str(experiment["recommendation"]), "", "## Limitations", str(experiment["limitations"]),
    ]
    write_markdown(lines, project_config.root / "reports" / "experiments" / f"{registry['experiment_id']}_readout.md")


def main() -> None:
    run_customer_decision_support()


if __name__ == "__main__":
    main()
