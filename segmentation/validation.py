from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown
from segmentation.segment_customers import SEGMENT_FEATURES


def run_segmentation_validation(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    features = pd.read_csv(project_config.processed_dir / "customer_features.csv", parse_dates=["signup_date"])
    model_frame = features[SEGMENT_FEATURES].apply(pd.to_numeric, errors="coerce")
    model_frame = model_frame.fillna(model_frame.median())
    x = StandardScaler().fit_transform(model_frame)
    metrics = []
    labels_by_seed: dict[int, np.ndarray] = {}
    for k in range(3, 8):
        model = KMeans(n_clusters=k, random_state=42, n_init=20).fit(x)
        counts = np.bincount(model.labels_, minlength=k) / len(x)
        metrics.append({"k": k, "silhouette_score": silhouette_score(x, model.labels_, sample_size=min(2500, len(x)), random_state=42),
                        "davies_bouldin_score": davies_bouldin_score(x, model.labels_), "inertia": model.inertia_,
                        "minimum_cluster_share": counts.min(), "maximum_cluster_share": counts.max(),
                        "selected_operational_k": k == 5})
    for seed in [7, 21, 42, 84, 126]:
        labels_by_seed[seed] = KMeans(n_clusters=5, random_state=seed, n_init=20).fit_predict(x)
    stability = pd.DataFrame([{"seed": seed, "adjusted_rand_vs_governed_seed_42": adjusted_rand_score(labels_by_seed[42], labels),
                               "status": "STABLE" if adjusted_rand_score(labels_by_seed[42], labels) >= .90 else "REVIEW"}
                              for seed, labels in labels_by_seed.items()])
    cutoff = features["signup_date"].median()
    assigned = pd.read_csv(project_config.mart_dir / "mart_customer_segments.csv", usecols=["customer_id", "segment_name"])
    period = features[["customer_id", "signup_date"]].merge(assigned, on="customer_id")
    rows = []
    for segment, group in period.groupby("segment_name"):
        ref = int(group["signup_date"].le(cutoff).sum())
        cur = int(group["signup_date"].gt(cutoff).sum())
        ref_total = int(period["signup_date"].le(cutoff).sum())
        cur_total = len(period) - ref_total
        shift = cur / cur_total - ref / ref_total
        rows.append({"segment_name": segment, "reference_customers": ref, "current_customers": cur,
                     "reference_share": ref / ref_total, "current_share": cur / cur_total,
                     "percentage_point_shift": shift, "status": "WATCH" if abs(shift) >= .05 else "STABLE"})
    period_stability = pd.DataFrame(rows)
    write_csv(pd.DataFrame(metrics), project_config.export_dir / "segmentation_validation_metrics.csv")
    write_csv(stability, project_config.export_dir / "segmentation_seed_stability.csv")
    write_csv(period_stability, project_config.export_dir / "segment_stability_summary.csv")
    write_markdown([
        "# Customer Segmentation Validation", "",
        "The governed five-cluster solution was challenged against k=3..7 using silhouette, Davies–Bouldin, inertia, cluster balance, seed stability, and time-slice mix stability.", "",
        "K=5 remains the operational choice for interpretable customer-strategy coverage; it is not presented as a mathematical optimum. All inputs are synthetic.", "",
        f"- Mean adjusted Rand index across seeds: {stability['adjusted_rand_vs_governed_seed_42'].mean():.4f}",
        f"- Time-slice segments requiring review: {period_stability['status'].eq('WATCH').sum()}",
        "- RFM migration outputs remain the source for customer movement; this validation measures K-Means robustness.",
    ], project_config.report_dir / "segmentation_validation.md")
    return {"metrics": pd.DataFrame(metrics), "seed_stability": stability, "period_stability": period_stability}


if __name__ == "__main__":
    run_segmentation_validation()
