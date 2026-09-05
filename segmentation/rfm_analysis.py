from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def _qscore(series: pd.Series, ascending: bool = True) -> pd.Series:
    clean = series.replace([np.inf, -np.inf], np.nan).fillna(series.median() if series.notna().any() else 0)
    rank = clean.rank(method="first", ascending=ascending)
    try:
        return pd.qcut(rank, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        pct = rank.rank(pct=True)
        return np.ceil(pct * 5).clip(1, 5).astype(int)


def _segment(row: pd.Series) -> str:
    r, f, m = int(row["recency_score"]), int(row["frequency_score"]), int(row["monetary_score"])
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if f >= 4 and m >= 3:
        return "Loyal Customers"
    if r >= 4 and f in [2, 3]:
        return "Potential Loyalists"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2:
        return "Lost Customers"
    return "Needs Nurture"


def run_rfm_analysis(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    features = pd.read_csv(project_config.processed_dir / "customer_features.csv")
    rfm = features[
        [
            "customer_id",
            "recency_days",
            "orders",
            "net_revenue",
            "return_adjusted_profit",
            "acquisition_channel",
            "loyalty_tier",
            "top_purchase_category",
        ]
    ].copy()
    rfm = rfm.rename(columns={"orders": "frequency", "net_revenue": "monetary_value"})
    rfm["recency_score"] = _qscore(rfm["recency_days"], ascending=False)
    rfm["frequency_score"] = _qscore(rfm["frequency"], ascending=True)
    rfm["monetary_score"] = _qscore(rfm["monetary_value"], ascending=True)
    rfm["rfm_score"] = (
        rfm["recency_score"].astype(str)
        + rfm["frequency_score"].astype(str)
        + rfm["monetary_score"].astype(str)
    )
    rfm["rfm_total_score"] = rfm["recency_score"] + rfm["frequency_score"] + rfm["monetary_score"]
    rfm["rfm_segment"] = rfm.apply(_segment, axis=1)

    distribution = (
        rfm.groupby("rfm_segment")
        .agg(customers=("customer_id", "nunique"), avg_recency_days=("recency_days", "mean"), avg_frequency=("frequency", "mean"), avg_monetary_value=("monetary_value", "mean"))
        .reset_index()
    )
    distribution["customer_share"] = distribution["customers"] / distribution["customers"].sum()

    revenue_contribution = (
        rfm.groupby("rfm_segment")
        .agg(revenue=("monetary_value", "sum"), profit=("return_adjusted_profit", "sum"), customers=("customer_id", "nunique"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    revenue_contribution["revenue_share"] = revenue_contribution["revenue"] / revenue_contribution["revenue"].sum()
    revenue_contribution["profit_share"] = revenue_contribution["profit"] / revenue_contribution["profit"].sum()

    write_csv(rfm, project_config.mart_dir / "mart_rfm_segments.csv")
    write_csv(distribution, project_config.export_dir / "rfm_distribution_analysis.csv")
    write_csv(revenue_contribution, project_config.export_dir / "rfm_revenue_contribution.csv")
    _write_recommendations(revenue_contribution, project_config)
    return {"rfm": rfm, "distribution": distribution, "revenue_contribution": revenue_contribution}


def _write_recommendations(revenue_contribution: pd.DataFrame, project_config: ProjectConfig) -> None:
    action_map = {
        "Champions": "Give early access, loyalty recognition, and referral asks while protecting margin.",
        "Loyal Customers": "Promote replenishment, subscription-style bundles, and category expansion.",
        "Potential Loyalists": "Push second and third purchase journeys based on first category and browsing intent.",
        "At Risk": "Use targeted win-back incentives and service recovery based on recency and product issues.",
        "Lost Customers": "Limit expensive discounts; test low-cost reactivation and suppress persistently unresponsive users.",
        "Needs Nurture": "Use education, recommendations, and light-touch lifecycle messaging.",
    }
    lines = [
        "# RFM Action Recommendations",
        "",
        "| Segment | Revenue Share | Profit Share | Recommended Action |",
        "|---|---:|---:|---|",
    ]
    for row in revenue_contribution.to_dict("records"):
        lines.append(
            f"| {row['rfm_segment']} | {row['revenue_share']:.1%} | {row['profit_share']:.1%} | {action_map.get(row['rfm_segment'], action_map['Needs Nurture'])} |"
        )
    write_markdown(lines, project_config.report_dir / "rfm_action_recommendations.md")


def main() -> None:
    run_rfm_analysis()


if __name__ == "__main__":
    main()

