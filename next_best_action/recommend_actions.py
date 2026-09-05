from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def _assign_action(row: pd.Series) -> str:
    if row["churn_risk_tier"] in {"Critical", "High"} and row["clv_band"] in {"Elite", "Platinum"}:
        return "High-touch retention save"
    if row["churn_risk_tier"] in {"Critical", "High"} and row["discount_dependency"] >= 0.20:
        return "Margin-controlled winback offer"
    if row["orders"] <= 1:
        return "First-to-second purchase journey"
    if row["return_rate"] >= 0.25:
        return "Returns experience recovery"
    if row["churn_risk_tier"] == "Low" and row["clv_band"] in {"Elite", "Platinum"}:
        return "VIP loyalty expansion"
    return "Category cross-sell nurture"


def build_next_best_actions(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv")
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv", usecols=["customer_id", "predicted_12m_clv", "clv_band"])
    segments = pd.read_csv(project_config.mart_dir / "mart_customer_segments.csv", usecols=["customer_id", "segment_name", "business_recommendation"])
    affinity = pd.read_csv(project_config.mart_dir / "mart_product_affinity.csv")
    products = pd.read_csv(
        project_config.mart_dir / "mart_product_profitability.csv",
        usecols=["product_id", "product_name", "category", "return_adjusted_profit", "return_rate", "return_adjusted_margin"],
    )

    product_rank = (
        products.sort_values(["category", "return_adjusted_profit", "return_adjusted_margin"], ascending=[True, False, False])
        .groupby("category", as_index=False)
        .head(3)
    )
    top_product = product_rank.groupby("category").first().reset_index()
    category_affinity = (
        affinity.sort_values(["source_category", "affinity_score", "lift"], ascending=[True, False, False])
        .groupby("source_category", as_index=False)
        .first()[["source_category", "target_category", "affinity_score", "lift"]]
    )

    base = churn.merge(clv, on="customer_id", how="left").merge(segments, on="customer_id", how="left")
    base["recommended_action"] = base.apply(_assign_action, axis=1)
    base = base.merge(category_affinity, left_on="top_purchase_category", right_on="source_category", how="left")
    base["recommended_category"] = base["target_category"].fillna(base["top_purchase_category"])
    base = base.merge(top_product, left_on="recommended_category", right_on="category", how="left", suffixes=("", "_recommended"))
    base["action_priority_score"] = (
        base["expected_profit_at_risk"].fillna(0) * 0.45
        + base["predicted_12m_clv"].fillna(0) * 0.35
        + base["churn_probability"].fillna(0) * 750
        + np.where(base["clv_band"].isin(["Elite", "Platinum"]), 250, 0)
    )
    base["owner_team"] = np.select(
        [
            base["recommended_action"].str.contains("retention|winback", case=False, regex=True),
            base["recommended_action"].str.contains("Returns", case=False, regex=False),
            base["recommended_action"].str.contains("VIP", case=False, regex=False),
        ],
        ["Lifecycle Marketing", "Customer Experience", "Loyalty"],
        default="Growth Marketing",
    )
    base["success_metric"] = np.select(
        [
            base["recommended_action"].eq("High-touch retention save"),
            base["recommended_action"].eq("Margin-controlled winback offer"),
            base["recommended_action"].eq("First-to-second purchase journey"),
            base["recommended_action"].eq("Returns experience recovery"),
        ],
        ["Retained CLV at risk", "Incremental profit after discount", "Second purchase conversion", "Reduced returns and support contacts"],
        default="Cross-sell conversion",
    )

    columns = [
        "customer_id",
        "recommended_action",
        "owner_team",
        "success_metric",
        "action_priority_score",
        "churn_risk_tier",
        "churn_probability",
        "expected_profit_at_risk",
        "predicted_12m_clv",
        "clv_band",
        "segment_name",
        "top_purchase_category",
        "recommended_category",
        "product_id",
        "product_name",
        "affinity_score",
        "lift",
        "business_recommendation",
    ]
    actions = base[columns].sort_values("action_priority_score", ascending=False)
    retention_queue = actions.loc[actions["recommended_action"].isin(["High-touch retention save", "Margin-controlled winback offer"])].head(50_000)
    cross_sell = actions.loc[actions["recommended_category"].ne(actions["top_purchase_category"])].head(50_000)

    write_csv(actions, project_config.export_dir / "next_best_actions.csv")
    write_csv(retention_queue, project_config.export_dir / "retention_offer_queue.csv")
    write_csv(cross_sell, project_config.export_dir / "cross_sell_recommendations.csv")
    _write_report(actions, project_config)
    return {"actions": actions, "retention_queue": retention_queue, "cross_sell": cross_sell}


def _write_report(actions: pd.DataFrame, project_config: ProjectConfig) -> None:
    action_mix = actions.groupby("recommended_action", as_index=False).agg(
        customers=("customer_id", "nunique"),
        expected_profit_at_risk=("expected_profit_at_risk", "sum"),
        avg_predicted_clv=("predicted_12m_clv", "mean"),
    )
    action_mix = action_mix.sort_values("expected_profit_at_risk", ascending=False)
    lines = [
        "# Next Best Action Report",
        "",
        "The next-best-action layer turns churn, CLV, segment, product affinity, and profitability signals into a prioritized action queue.",
        "",
        "| Action | Customers | Profit at Risk | Avg Predicted CLV |",
        "|---|---:|---:|---:|",
    ]
    for row in action_mix.to_dict("records"):
        lines.append(
            f"| {row['recommended_action']} | {row['customers']:,.0f} | ${row['expected_profit_at_risk']:,.0f} | ${row['avg_predicted_clv']:,.0f} |"
        )
    lines.extend(
        [
            "",
            "## Operating Guidance",
            "- Use the retention queue for high-touch save treatments and controlled offer tests.",
            "- Use cross-sell recommendations only where the recommended category has positive affinity and healthy return-adjusted margin.",
            "- Keep holdout groups in each major action family to measure incremental profit, not just response rate.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "next_best_action_report.md")


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Build customer-level next-best-action outputs.").parse_args()


def main() -> None:
    parse_args()
    build_next_best_actions()


if __name__ == "__main__":
    main()
