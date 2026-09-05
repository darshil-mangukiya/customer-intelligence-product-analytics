from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


MONITORED_FEATURES = [
    "recency_days", "orders", "net_revenue", "engagement_score", "return_rate",
    "discount_dependency", "support_cases", "tenure_days",
]


def population_stability_index(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    ref = pd.to_numeric(reference, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    cur = pd.to_numeric(current, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if ref.empty or cur.empty:
        return 0.0
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref_counts = pd.cut(ref, edges, include_lowest=True, duplicates="drop").value_counts(sort=False)
    cur_counts = pd.cut(cur, edges, include_lowest=True, duplicates="drop").value_counts(sort=False).reindex(ref_counts.index, fill_value=0)
    ref_pct = np.maximum(ref_counts.to_numpy() / len(ref), 1e-6)
    cur_pct = np.maximum(cur_counts.to_numpy() / len(cur), 1e-6)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def drift_status(psi: float, missing_delta: float = 0.0) -> str:
    if psi >= 0.25 or missing_delta >= 0.10:
        return "MATERIAL_DRIFT"
    if psi >= 0.10 or missing_delta >= 0.05:
        return "WATCH"
    return "STABLE"


def run_drift_monitoring(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    features = pd.read_csv(project_config.processed_dir / "customer_features.csv", parse_dates=["signup_date"])
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv", usecols=["customer_id", "churn_probability", "churn_risk_tier"])
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv", usecols=["customer_id", "predicted_12m_clv"])
    segments = pd.read_csv(project_config.mart_dir / "mart_customer_segments.csv", usecols=["customer_id", "segment_name"])
    frame = features.merge(churn, on="customer_id").merge(clv, on="customer_id").merge(segments, on="customer_id")
    cutoff = frame["signup_date"].median()
    reference = frame.loc[frame["signup_date"].le(cutoff)].copy()
    current = frame.loc[frame["signup_date"].gt(cutoff)].copy()
    if reference.empty or current.empty:
        raise ValueError("reference and current monitoring periods must both contain customers")

    feature_rows = []
    for feature in MONITORED_FEATURES:
        ref_values, cur_values = reference[feature], current[feature]
        psi = population_stability_index(ref_values, cur_values)
        missing_delta = abs(float(cur_values.isna().mean()) - float(ref_values.isna().mean()))
        finite_ref = pd.to_numeric(ref_values, errors="coerce").dropna()
        finite_cur = pd.to_numeric(cur_values, errors="coerce").dropna()
        ks_stat, ks_p = ks_2samp(finite_ref, finite_cur) if len(finite_ref) and len(finite_cur) else (0.0, 1.0)
        feature_rows.append({
            "feature": feature, "reference_customers": len(reference), "current_customers": len(current),
            "reference_mean": float(finite_ref.mean()) if len(finite_ref) else 0.0, "current_mean": float(finite_cur.mean()) if len(finite_cur) else 0.0,
            "reference_missing_rate": float(ref_values.isna().mean()), "current_missing_rate": float(cur_values.isna().mean()),
            "missingness_delta": missing_delta, "psi": psi, "ks_statistic": float(ks_stat), "ks_p_value": float(ks_p),
            "status": drift_status(psi, missing_delta), "threshold_rationale": "PSI <0.10 stable; 0.10–0.25 watch; >=0.25 material. Missingness delta >=5pp watch, >=10pp material.",
        })
    feature_drift = pd.DataFrame(feature_rows)

    prediction_rows = []
    for metric in ["churn_probability", "predicted_12m_clv"]:
        psi = population_stability_index(reference[metric], current[metric])
        prediction_rows.append({
            "signal": metric, "reference_mean": float(reference[metric].mean()), "current_mean": float(current[metric].mean()),
            "reference_median": float(reference[metric].median()), "current_median": float(current[metric].median()),
            "psi": psi, "absolute_change": float(current[metric].mean() - reference[metric].mean()), "status": drift_status(psi),
            "interpretation": "Distribution shift is a review signal, not proof that model performance degraded.",
        })
    for tier in sorted(frame["churn_risk_tier"].unique()):
        ref_share = float(reference["churn_risk_tier"].eq(tier).mean())
        cur_share = float(current["churn_risk_tier"].eq(tier).mean())
        prediction_rows.append({
            "signal": f"churn_tier_{tier}", "reference_mean": ref_share, "current_mean": cur_share,
            "reference_median": ref_share, "current_median": cur_share, "psi": 0.0,
            "absolute_change": cur_share - ref_share, "status": "WATCH" if abs(cur_share - ref_share) >= 0.05 else "STABLE",
            "interpretation": "Tier-mix shift uses a 5 percentage-point review threshold.",
        })
    prediction_drift = pd.DataFrame(prediction_rows)

    segment_rows = []
    for segment in sorted(frame["segment_name"].unique()):
        ref = reference.loc[reference["segment_name"].eq(segment)]
        cur = current.loc[current["segment_name"].eq(segment)]
        ref_share, cur_share = len(ref) / len(reference), len(cur) / len(current)
        segment_rows.append({
            "segment_name": segment, "reference_customers": len(ref), "current_customers": len(cur),
            "reference_share": ref_share, "current_share": cur_share, "percentage_point_shift": cur_share - ref_share,
            "relative_change": (cur_share - ref_share) / ref_share if ref_share else 0.0,
            "customer_count_change": len(cur) - len(ref), "reference_avg_clv": float(ref["predicted_12m_clv"].mean()) if len(ref) else 0.0,
            "current_avg_clv": float(cur["predicted_12m_clv"].mean()) if len(cur) else 0.0,
            "clv_change": float(cur["predicted_12m_clv"].mean() - ref["predicted_12m_clv"].mean()) if len(ref) and len(cur) else 0.0,
            "status": "WATCH" if abs(cur_share - ref_share) >= 0.05 else "STABLE",
        })
    segment_drift = pd.DataFrame(segment_rows)

    write_csv(feature_drift, project_config.export_dir / "model_feature_drift.csv")
    write_csv(prediction_drift, project_config.export_dir / "model_prediction_drift.csv")
    write_csv(segment_drift, project_config.export_dir / "segment_drift_monitoring.csv")
    _write_report(feature_drift, prediction_drift, segment_drift, cutoff, project_config)
    return {"feature": feature_drift, "prediction": prediction_drift, "segment": segment_drift}


def _write_report(feature: pd.DataFrame, prediction: pd.DataFrame, segment: pd.DataFrame, cutoff: pd.Timestamp, project_config: ProjectConfig) -> None:
    lines = [
        "# Reproducible Model Monitoring Framework", "",
        "Recorded baselines use generated project data and explicit review thresholds.", "",
        f"- Reference period: signup date <= {cutoff.date()}", f"- Current period: signup date > {cutoff.date()}",
        f"- Feature signals: {len(feature)}; watch/material: {feature['status'].ne('STABLE').sum()}",
        f"- Prediction signals: {len(prediction)}; watch/material: {prediction['status'].ne('STABLE').sum()}",
        f"- Segment signals: {len(segment)}; watch: {segment['status'].ne('STABLE').sum()}", "",
        "PSI below 0.10 is stable, 0.10–0.25 is watch, and >=0.25 is material drift. KS statistics supplement PSI for continuous features; p-values reflect detectability and are not severity measures. Shift alone does not prove performance degradation.",
    ]
    write_markdown(lines, project_config.report_dir / "model_drift_monitoring.md")


if __name__ == "__main__":
    run_drift_monitoring()
