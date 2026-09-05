from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


BASELINE_PATH = "model_monitoring_baseline.json"


def _read(path: Path, usecols: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, usecols=usecols)


def _psi(expected: pd.Series, actual: pd.Series, buckets: int = 10) -> float:
    expected = pd.to_numeric(expected, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    actual = pd.to_numeric(actual, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if expected.empty or actual.empty:
        return 0.0
    quantiles = np.unique(np.quantile(expected, np.linspace(0, 1, buckets + 1)))
    if len(quantiles) <= 2:
        return 0.0
    expected_bins = pd.cut(expected, bins=quantiles, include_lowest=True, duplicates="drop")
    actual_bins = pd.cut(actual, bins=quantiles, include_lowest=True, duplicates="drop")
    expected_pct = expected_bins.value_counts(normalize=True, sort=False).replace(0, 0.0001)
    actual_pct = actual_bins.value_counts(normalize=True, sort=False).reindex(expected_pct.index).fillna(0.0001).replace(0, 0.0001)
    return float(((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)).sum())


def _mix(series: pd.Series) -> dict[str, float]:
    return series.fillna("Unknown").value_counts(normalize=True).sort_index().round(6).to_dict()


def _mix_delta(current: dict[str, float], baseline: dict[str, float]) -> float:
    keys = set(current).union(baseline)
    return float(sum(abs(current.get(key, 0) - baseline.get(key, 0)) for key in keys) / 2)


def run_model_monitoring(project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    project_config.ensure_directories()
    churn = _read(project_config.mart_dir / "mart_churn_risk.csv", ["customer_id", "churn_probability", "churn_risk_tier"])
    clv = _read(project_config.mart_dir / "mart_clv.csv", ["customer_id", "predicted_12m_clv", "clv_band", "churn_label"])
    segments = _read(project_config.mart_dir / "mart_customer_segments.csv", ["customer_id", "segment_name"])
    kpis = _read(project_config.export_dir / "kpi_summary.csv")
    churn_metrics = _read_json(project_config.model_dir / "churn_metrics.json")
    clv_metrics = _read_json(project_config.model_dir / "clv_model_metrics.json")
    segmentation_metrics = _read_json(project_config.model_dir / "segmentation_metrics.json")

    current = {
        "churn_probability_mean": float(churn["churn_probability"].mean()) if len(churn) else 0,
        "churn_probability_p95": float(churn["churn_probability"].quantile(0.95)) if len(churn) else 0,
        "churn_risk_mix": _mix(churn["churn_risk_tier"]) if len(churn) else {},
        "predicted_clv_mean": float(clv["predicted_12m_clv"].mean()) if len(clv) else 0,
        "predicted_clv_p95": float(clv["predicted_12m_clv"].quantile(0.95)) if len(clv) else 0,
        "clv_band_mix": _mix(clv["clv_band"]) if len(clv) else {},
        "segment_mix": _mix(segments["segment_name"]) if len(segments) else {},
        "churn_auc": churn_metrics.get("roc_auc"),
        "churn_recall": churn_metrics.get("recall"),
        "clv_r2": clv_metrics.get("r2"),
        "segmentation_silhouette": segmentation_metrics.get("silhouette_score"),
    }

    baseline_file = project_config.audit_dir / BASELINE_PATH
    baseline_created = False
    if baseline_file.exists():
        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    else:
        baseline = current.copy()
        baseline["churn_probability_sample"] = churn["churn_probability"].sample(min(50_000, len(churn)), random_state=42).tolist() if len(churn) else []
        baseline["predicted_clv_sample"] = clv["predicted_12m_clv"].sample(min(50_000, len(clv)), random_state=42).tolist() if len(clv) else []
        baseline_file.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        baseline_created = True

    monitoring_rows = [
        _row("data_freshness", "mart_churn_risk_rows", len(churn), ">= 100000", len(churn) >= 100_000, "Customer scoring coverage"),
        _row("data_freshness", "mart_clv_rows", len(clv), ">= 100000", len(clv) >= 100_000, "CLV scoring coverage"),
        _row("model_quality", "churn_roc_auc", current["churn_auc"], ">= 0.75", current["churn_auc"] is not None and current["churn_auc"] >= 0.75, "Churn ranking quality"),
        _row("model_quality", "churn_recall", current["churn_recall"], ">= 0.60", current["churn_recall"] is not None and current["churn_recall"] >= 0.60, "Risk capture quality"),
        _row("model_quality", "clv_r2", current["clv_r2"], ">= 0.10", current["clv_r2"] is not None and current["clv_r2"] >= 0.10, "Forward-value signal strength"),
        _row("model_quality", "segmentation_silhouette", current["segmentation_silhouette"], ">= 0.20", current["segmentation_silhouette"] is not None and current["segmentation_silhouette"] >= 0.20, "Cluster separation"),
    ]

    churn_psi = _psi(pd.Series(baseline.get("churn_probability_sample", churn["churn_probability"])), churn["churn_probability"]) if len(churn) else 0
    clv_psi = _psi(pd.Series(baseline.get("predicted_clv_sample", clv["predicted_12m_clv"])), clv["predicted_12m_clv"]) if len(clv) else 0
    risk_mix_delta = _mix_delta(current["churn_risk_mix"], baseline.get("churn_risk_mix", current["churn_risk_mix"]))
    segment_mix_delta = _mix_delta(current["segment_mix"], baseline.get("segment_mix", current["segment_mix"]))

    monitoring_rows.extend(
        [
            _row("score_drift", "churn_probability_psi", round(churn_psi, 4), "<= 0.10", churn_psi <= 0.10, "Population stability index for churn scores"),
            _row("score_drift", "predicted_clv_psi", round(clv_psi, 4), "<= 0.10", clv_psi <= 0.10, "Population stability index for CLV scores"),
            _row("mix_drift", "churn_risk_mix_delta", round(risk_mix_delta, 4), "<= 0.08", risk_mix_delta <= 0.08, "Risk tier distribution shift"),
            _row("mix_drift", "segment_mix_delta", round(segment_mix_delta, 4), "<= 0.08", segment_mix_delta <= 0.08, "Segment distribution shift"),
            _row("baseline", "baseline_status", "created" if baseline_created else "loaded", "baseline available", True, "Monitoring baseline state"),
        ]
    )

    if len(kpis):
        leakage = kpis.loc[kpis["kpi_name"].eq("Revenue Leakage from Returns and Discounts"), "value"]
        retention = kpis.loc[kpis["kpi_name"].eq("Retention Rate"), "value"]
        if not leakage.empty:
            monitoring_rows.append(_row("kpi_watch", "revenue_leakage", float(leakage.iloc[0]), "tracked", True, "Executive leakage watchlist"))
        if not retention.empty:
            monitoring_rows.append(_row("kpi_watch", "retention_rate", float(retention.iloc[0]), ">= 0.65", float(retention.iloc[0]) >= 0.65, "Executive retention watchlist"))

    output = pd.DataFrame(monitoring_rows)
    write_csv(output, project_config.export_dir / "model_monitoring_summary.csv")
    _write_monitoring_report(output, current, project_config)
    return output


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _row(category: str, signal_name: str, observed_value: object, threshold: str, passed: bool, business_meaning: str) -> dict[str, object]:
    return {
        "category": category,
        "signal_name": signal_name,
        "observed_value": observed_value,
        "threshold": threshold,
        "status": "PASS" if passed else "WATCH",
        "business_meaning": business_meaning,
    }


def _write_monitoring_report(results: pd.DataFrame, current: dict[str, object], project_config: ProjectConfig) -> None:
    watch = results.loc[results["status"].eq("WATCH")]
    customer_volume = int(results.loc[results["signal_name"].eq("mart_churn_risk_rows"), "observed_value"].iloc[0])
    profile = "sample_5k" if customer_volume == 5_000 else "full_250k" if customer_volume == 250_000 else "volume_unspecified"
    if profile == "sample_5k":
        role = "authoritative current model evidence"
    elif profile == "full_250k":
        role = "full-volume monitoring evidence; not authoritative for current 5K model KPIs"
    else:
        role = "unclassified-volume monitoring evidence; not authoritative for current 5K model KPIs"
    lines = [
        "# Model Monitoring Report",
        "",
        f"> Evidence profile: `{profile}` ({customer_volume:,} customers) — {role}.",
        "",
        f"- Signals evaluated: {len(results):,}",
        f"- Passing signals: {results['status'].eq('PASS').sum():,}",
        f"- Watch signals: {len(watch):,}",
        "",
        "## Current Score Snapshot",
        f"- Average churn probability: {current['churn_probability_mean']:.1%}",
        f"- P95 churn probability: {current['churn_probability_p95']:.1%}",
        f"- Average predicted CLV: ${current['predicted_clv_mean']:,.0f}",
        f"- P95 predicted CLV: ${current['predicted_clv_p95']:,.0f}",
        "",
        "| Category | Signal | Observed | Threshold | Status | Meaning |",
        "|---|---|---:|---|---|---|",
    ]
    for row in results.to_dict("records"):
        lines.append(
            f"| {row['category']} | `{row['signal_name']}` | {row['observed_value']} | {row['threshold']} | {row['status']} | {row['business_meaning']} |"
        )
    if len(watch):
        lines.extend(["", "## Watch Items"])
        for row in watch.to_dict("records"):
            lines.append(f"- {row['signal_name']}: observed `{row['observed_value']}` against `{row['threshold']}`.")
    write_markdown(lines, project_config.report_dir / "model_monitoring_report.md")


def main() -> None:
    run_model_monitoring()


if __name__ == "__main__":
    main()
