from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


SEGMENT_FEATURES = [
    "recency_days",
    "orders",
    "net_revenue",
    "return_adjusted_profit",
    "avg_order_value",
    "purchase_frequency_30d",
    "discount_dependency",
    "return_rate",
    "sessions",
    "avg_page_views",
    "bounce_rate",
    "engagement_score",
    "category_diversity",
]


RECOMMENDATIONS = {
    "High Value Loyal Customers": "Protect margin and loyalty. Prioritize early product access, premium service recovery, and retention-triggered offers that avoid unnecessary discounting.",
    "New High Intent Buyers": "Convert intent into second purchase. Use onboarding journeys, category-specific bundles, and first-30-day replenishment prompts.",
    "Discount-driven Buyers": "Manage promo dependency. Shift from blanket discounts to threshold offers, bundles, and margin-safe loyalty incentives.",
    "At-risk Customers": "Intercept churn. Trigger win-back journeys based on recency, declining engagement, return friction, and category abandonment.",
    "One-time Buyers": "Improve first-to-second purchase. Personalize follow-up around first category, reduce post-purchase friction, and test low-cost reactivation.",
    "Category Explorers": "Increase share of wallet. Recommend adjacent categories and cross-sell paths from observed browsing and purchase diversity.",
}


def _rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True).fillna(0.5)


def _assign_business_names(profile: pd.DataFrame) -> pd.DataFrame:
    profile = profile.copy()
    median_orders = profile["orders"].median()
    median_recency = profile["recency_days"].median()
    q_revenue = profile["net_revenue"].quantile(0.65)
    q_discount = profile["discount_dependency"].quantile(0.65)
    q_sessions = profile["sessions"].quantile(0.60)
    q_engagement = profile["engagement_score"].quantile(0.60)

    assigned: dict[int, str] = {}
    for row in profile.sort_values("net_revenue", ascending=False).to_dict("records"):
        cluster = int(row["cluster_id"])
        if row["orders"] >= median_orders and row["net_revenue"] >= q_revenue and row["recency_days"] <= median_recency:
            name = "High Value Loyal Customers"
        elif row["orders"] <= 1.35:
            name = "One-time Buyers"
        elif row["recency_days"] > median_recency * 1.25 and row["engagement_score"] < q_engagement:
            name = "At-risk Customers"
        elif row["discount_dependency"] >= q_discount:
            name = "Discount-driven Buyers"
        elif row["sessions"] >= q_sessions and row["engagement_score"] >= q_engagement:
            name = "New High Intent Buyers"
        else:
            name = "Category Explorers"
        assigned[cluster] = name

    used: dict[str, int] = {}
    final_names: dict[int, str] = {}
    for cluster, name in assigned.items():
        used[name] = used.get(name, 0) + 1
        final_names[cluster] = name if used[name] == 1 else f"{name} {used[name]}"

    profile["segment_name"] = profile["cluster_id"].map(final_names)
    profile["business_recommendation"] = profile["segment_name"].str.replace(r" \d+$", "", regex=True).map(RECOMMENDATIONS).fillna(RECOMMENDATIONS["Category Explorers"])
    return profile


def run_segmentation(project_config: ProjectConfig = CONFIG, n_clusters: int = 5) -> dict[str, pd.DataFrame | dict[str, float]]:
    project_config.ensure_directories()
    base = pd.read_csv(project_config.processed_dir / "segmentation_base.csv")
    customer_features = pd.read_csv(project_config.processed_dir / "customer_features.csv")

    features = base[SEGMENT_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    actual_clusters = max(2, min(n_clusters, len(features)))
    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", KMeans(n_clusters=actual_clusters, random_state=42, n_init=20)),
        ]
    )
    cluster_id = pipeline.fit_predict(features)
    base["cluster_id"] = cluster_id

    sample_features = features.sample(min(10_000, len(features)), random_state=42)
    sample_labels = base.loc[sample_features.index, "cluster_id"]
    silhouette = float(silhouette_score(StandardScaler().fit_transform(sample_features), sample_labels)) if sample_labels.nunique() > 1 else 0.0

    profile = (
        base.groupby("cluster_id")
        .agg(
            customers=("customer_id", "nunique"),
            recency_days=("recency_days", "mean"),
            orders=("orders", "mean"),
            net_revenue=("net_revenue", "mean"),
            return_adjusted_profit=("return_adjusted_profit", "mean"),
            avg_order_value=("avg_order_value", "mean"),
            purchase_frequency_30d=("purchase_frequency_30d", "mean"),
            discount_dependency=("discount_dependency", "mean"),
            return_rate=("return_rate", "mean"),
            sessions=("sessions", "mean"),
            engagement_score=("engagement_score", "mean"),
            category_diversity=("category_diversity", "mean"),
        )
        .reset_index()
    )
    profile["customer_share"] = profile["customers"] / profile["customers"].sum()
    profile["value_score"] = _rank(profile["net_revenue"]) + _rank(profile["return_adjusted_profit"]) + (1 - _rank(profile["recency_days"]))
    profile = _assign_business_names(profile)

    assignments = base[["customer_id", "cluster_id"]].merge(profile[["cluster_id", "segment_name", "business_recommendation"]], on="cluster_id", how="left")
    assignments = assignments.merge(
        customer_features[
            [
                "customer_id",
                "acquisition_channel",
                "loyalty_tier",
                "top_purchase_category",
                "orders",
                "net_revenue",
                "return_adjusted_profit",
                "recency_days",
                "historical_clv",
                "churn_label",
            ]
        ],
        on="customer_id",
        how="left",
    )

    segment_kpis = (
        assignments.groupby("segment_name")
        .agg(
            customers=("customer_id", "nunique"),
            revenue=("net_revenue", "sum"),
            profit=("return_adjusted_profit", "sum"),
            avg_orders=("orders", "mean"),
            avg_recency_days=("recency_days", "mean"),
            avg_historical_clv=("historical_clv", "mean"),
            churn_rate=("churn_label", "mean"),
        )
        .reset_index()
        .sort_values("profit", ascending=False)
    )
    segment_kpis["revenue_share"] = segment_kpis["revenue"] / segment_kpis["revenue"].sum()
    segment_kpis["profit_share"] = segment_kpis["profit"] / segment_kpis["profit"].sum()

    metrics = {
        "n_clusters": actual_clusters,
        "silhouette_score": round(silhouette, 4),
        "customers_scored": int(len(assignments)),
    }

    write_csv(assignments, project_config.mart_dir / "mart_customer_segments.csv")
    write_csv(profile, project_config.export_dir / "segment_profiles.csv")
    write_csv(segment_kpis, project_config.export_dir / "segment_kpi_comparison.csv")
    (project_config.model_dir / "segmentation_model.joblib").parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, project_config.model_dir / "segmentation_model.joblib")
    (project_config.model_dir / "segmentation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    lines = [
        "# Customer Segment Recommendations",
        "",
        f"Model silhouette score: `{metrics['silhouette_score']}` across `{metrics['n_clusters']}` clusters.",
        "",
    ]
    for row in profile.sort_values("value_score", ascending=False).to_dict("records"):
        lines.extend(
            [
                f"## {row['segment_name']}",
                f"- Customers: {int(row['customers']):,} ({row['customer_share']:.1%})",
                f"- Average revenue: ${row['net_revenue']:,.0f}",
                f"- Average profit: ${row['return_adjusted_profit']:,.0f}",
                f"- Average recency: {row['recency_days']:.0f} days",
                f"- Recommended action: {row['business_recommendation']}",
                "",
            ]
        )
    write_markdown(lines, project_config.report_dir / "segment_recommendations.md")

    return {"assignments": assignments, "profile": profile, "segment_kpis": segment_kpis, "metrics": metrics}


def main() -> None:
    run_segmentation()


if __name__ == "__main__":
    main()

