from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, roc_auc_score

from config.settings import CONFIG
from etl.io_utils import write_csv, write_markdown


MIN_CLASS_COUNT = 20


def group_metrics(group_type: str, group_value: str, frame: pd.DataFrame) -> dict[str, object]:
    actual = frame["churn_label"].astype(int).to_numpy()
    score = frame["churn_probability"].astype(float).to_numpy()
    positives = int(actual.sum())
    negatives = int(len(actual) - positives)
    sufficient = positives >= MIN_CLASS_COUNT and negatives >= MIN_CLASS_COUNT
    row: dict[str, object] = {
        "group_type": group_type,
        "group_value": group_value,
        "observations": len(frame),
        "positives": positives,
        "negatives": negatives,
        "status": "EVALUATED" if sufficient else "INSUFFICIENT_SAMPLE",
    }
    if not sufficient:
        row.update({metric: np.nan for metric in ("roc_auc", "pr_auc", "precision", "recall", "false_positive_rate", "false_negative_rate", "top_10pct_lift", "brier_score", "calibration_gap")})
        return row

    predicted = (score >= 0.5).astype(int)
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(actual, predicted, labels=[0, 1]).ravel()
    top_n = max(1, int(np.ceil(len(frame) * 0.10)))
    top_rate = actual[np.argsort(score)[-top_n:]].mean()
    baseline_rate = actual.mean()
    row.update(
        {
            "roc_auc": roc_auc_score(actual, score),
            "pr_auc": average_precision_score(actual, score),
            "precision": true_positive / max(true_positive + false_positive, 1),
            "recall": true_positive / max(true_positive + false_negative, 1),
            "false_positive_rate": false_positive / max(false_positive + true_negative, 1),
            "false_negative_rate": false_negative / max(false_negative + true_positive, 1),
            "top_10pct_lift": top_rate / max(baseline_rate, np.finfo(float).eps),
            "brier_score": brier_score_loss(actual, score),
            "calibration_gap": abs(float(score.mean() - baseline_rate)),
        }
    )
    return row


def main() -> None:
    features = pd.read_csv(CONFIG.processed_dir / "customer_features.csv")
    scores = pd.read_csv(CONFIG.mart_dir / "mart_churn_risk.csv", usecols=["customer_id", "churn_probability"])
    frame = features.merge(scores, on="customer_id", how="inner", validate="one_to_one")
    frame["tenure_band"] = pd.cut(
        frame["tenure_days"],
        bins=[-1, 365, 730, 1095, np.inf],
        labels=["0-1 year", "1-2 years", "2-3 years", "3+ years"],
    ).astype(str)
    frame["activity_level"] = pd.cut(
        frame["orders"],
        bins=[-1, 0, 2, 5, np.inf],
        labels=["no orders", "1-2 orders", "3-5 orders", "6+ orders"],
    ).astype(str)

    dimensions = {
        "region": "region_id",
        "tenure_band": "tenure_band",
        "value_tier": "customer_value_band",
        "activity_level": "activity_level",
    }
    rows: list[dict[str, object]] = []
    for group_type, column in dimensions.items():
        for group_value, group in frame.groupby(column, observed=True, dropna=False):
            rows.append(group_metrics(group_type, str(group_value), group))
    results = pd.DataFrame(rows)
    write_csv(results, CONFIG.audit_dir / "synthetic_subgroup_model_risk.csv")

    evaluated = results.loc[results["status"].eq("EVALUATED")]
    insufficient = results.loc[results["status"].eq("INSUFFICIENT_SAMPLE")]
    report = [
        "# Synthetic Subgroup Model-Risk Check",
        "",
        "This evaluates subgroup-analysis methodology on synthetic data and does not establish real-world fairness.",
        "",
        f"- Groups evaluated: {len(evaluated)}",
        f"- Insufficient-sample groups: {len(insufficient)}",
        f"- Minimum required positives and negatives per group: {MIN_CLASS_COUNT}",
        "- Metrics: ROC-AUC, PR-AUC, precision, recall, false-positive rate, false-negative rate, top-10% lift, Brier score, and calibration gap.",
        "",
        "| Dimension | Evaluated | Insufficient | ROC-AUC range | PR-AUC range |",
        "|---|---:|---:|---:|---:|",
    ]
    for group_type in dimensions:
        subset = results.loc[results["group_type"].eq(group_type)]
        valid = subset.loc[subset["status"].eq("EVALUATED")]
        roc_range = f"{valid['roc_auc'].min():.3f}-{valid['roc_auc'].max():.3f}" if len(valid) else "N/A"
        pr_range = f"{valid['pr_auc'].min():.3f}-{valid['pr_auc'].max():.3f}" if len(valid) else "N/A"
        report.append(
            f"| {group_type} | {valid.shape[0]} | {subset['status'].eq('INSUFFICIENT_SAMPLE').sum()} | {roc_range} | {pr_range} |"
        )
    report.extend(
        [
            "",
            "Observed subgroup differences are diagnostic review signals on deterministic synthetic data. They must not be interpreted as protected-class fairness results, causal effects, or evidence of real-world model performance.",
        ]
    )
    write_markdown(report, CONFIG.report_dir / "synthetic_subgroup_model_risk.md")


if __name__ == "__main__":
    main()
