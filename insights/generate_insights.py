from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def generate_business_insights(project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    project_config.ensure_directories()
    kpis = _read(project_config.export_dir / "kpi_summary.csv")
    segments = _read(project_config.export_dir / "segment_kpi_comparison.csv")
    churn_drivers = _read(project_config.export_dir / "churn_driver_summary.csv")
    category_profitability = _read(project_config.mart_dir / "mart_category_profitability.csv")
    clv_channel = _read(project_config.export_dir / "clv_by_acquisition_channel.csv")
    cohort = _read(project_config.mart_dir / "mart_cohort_retention.csv")
    affinity = _read(project_config.mart_dir / "mart_product_affinity.csv")
    return_heavy = _read(project_config.export_dir / "return_heavy_products.csv")

    insights: list[dict[str, object]] = []

    _add_kpi_insight(kpis, "Churn Rate", insights, "Retention Risk", "Customer Analytics", "High")
    _add_kpi_insight(kpis, "Revenue Leakage from Returns and Discounts", insights, "Revenue Leakage", "Finance Analytics", "High")

    if len(segments):
        top_profit = segments.sort_values("profit", ascending=False).iloc[0]
        high_churn = segments.sort_values("churn_rate", ascending=False).iloc[0]
        insights.append(
            _row(
                "Customer Value",
                f"{top_profit['segment_name']} is the most profitable customer segment.",
                f"Segment contributes ${top_profit['profit']:,.0f} profit and {top_profit['profit_share']:.1%} of total segment profit.",
                "Protect this segment with margin-aware loyalty benefits and service recovery triggers.",
                "Customer Analytics",
                "High",
            )
        )
        insights.append(
            _row(
                "Retention Risk",
                f"{high_churn['segment_name']} has the highest churn exposure.",
                f"Churn rate is {high_churn['churn_rate']:.1%} across {int(high_churn['customers']):,} customers.",
                "Use win-back journeys only where expected value is positive; suppress low-value inactive customers.",
                "Lifecycle Marketing",
                "High",
            )
        )

    if len(churn_drivers):
        driver = churn_drivers.iloc[0]
        insights.append(
            _row(
                "Churn Driver",
                f"`{driver['feature']}` is the strongest churn model driver.",
                driver.get("business_interpretation", "Behavioral signal has high influence in the churn model."),
                "Add this driver to the churn dashboard and monitor it by segment and acquisition channel.",
                "Customer Analytics",
                "High",
            )
        )

    if len(category_profitability):
        return_risk = category_profitability.sort_values("return_rate", ascending=False).iloc[0]
        low_margin = category_profitability.sort_values("return_adjusted_margin", ascending=True).iloc[0]
        insights.append(
            _row(
                "Product Returns",
                f"{return_risk['category']} shows the highest category return rate.",
                f"Return rate is {return_risk['return_rate']:.1%} with ${return_risk['return_adjusted_profit']:,.0f} profit.",
                "Review product content, sizing, delivery promises, and post-purchase support for this category.",
                "Product Analytics",
                "Medium",
            )
        )
        insights.append(
            _row(
                "Profitability",
                f"{low_margin['category']} has the weakest return-adjusted margin.",
                f"Margin is {low_margin['return_adjusted_margin']:.1%} after returns and discounts.",
                "Prioritize margin repair through pricing, vendor cost review, promotion rules, and bundle design.",
                "Merchandising",
                "High",
            )
        )

    if len(clv_channel):
        risk_channel = clv_channel.sort_values("expected_clv_at_risk", ascending=False).iloc[0]
        insights.append(
            _row(
                "CLV Risk",
                f"{risk_channel['acquisition_channel']} has the highest CLV at risk.",
                f"Expected CLV at risk is ${risk_channel['expected_clv_at_risk']:,.0f}; churn rate is {risk_channel['churn_rate']:.1%}.",
                "Evaluate acquisition quality and launch channel-specific retention interventions.",
                "Growth Analytics",
                "High",
            )
        )

    if len(cohort):
        month_1 = cohort.loc[cohort["cohort_index"].eq(1), "retention_rate"].mean()
        month_6 = cohort.loc[cohort["cohort_index"].eq(6), "retention_rate"].mean()
        insights.append(
            _row(
                "Cohort Retention",
                "Retention decays materially between early and mid-life cohorts.",
                f"Average Month 1 retention is {month_1:.1%}; average Month 6 retention is {month_6:.1%}.",
                "Strengthen first-60-day onboarding, replenishment prompts, and second-purchase offers.",
                "Customer Analytics",
                "Medium",
            )
        )

    if len(affinity):
        pair = affinity.iloc[0]
        insights.append(
            _row(
                "Cross-sell",
                f"{pair['source_category']} to {pair['target_category']} is the strongest cross-sell path.",
                f"Affinity score is {pair['affinity_score']:.3f} with {pair['lift']:.2f}x lift.",
                "Test this pair in recommendation modules, email journeys, and product detail page bundles.",
                "Product Analytics",
                "Medium",
            )
        )

    if len(return_heavy):
        product = return_heavy.iloc[0]
        insights.append(
            _row(
                "Product Quality",
                f"{product['product_name']} is a top return-heavy product.",
                f"Return rate is {product['return_rate']:.1%} across {int(product['orders']):,} orders.",
                "Audit product content, fulfillment issues, reviews, and category fit before increasing promotion.",
                "Merchandising",
                "Medium",
            )
        )

    output = pd.DataFrame(insights)
    write_csv(output, project_config.export_dir / "stakeholder_insights.csv")
    _write_report(output, project_config)
    return output


def _add_kpi_insight(kpis: pd.DataFrame, kpi_name: str, insights: list[dict[str, object]], insight_type: str, owner: str, priority: str) -> None:
    if not len(kpis) or kpi_name not in set(kpis["kpi_name"]):
        return
    row = kpis.loc[kpis["kpi_name"].eq(kpi_name)].iloc[0]
    value = row["value"]
    formatted = f"{value:.1%}" if row["display_format"] == "Percent" else f"${value:,.0f}" if row["display_format"] == "Currency" else f"{value:,.2f}"
    insights.append(
        _row(
            insight_type,
            f"{kpi_name} is currently {formatted}.",
            f"Governed threshold: {row['threshold']}. Grain: {row['grain']}.",
            "Monitor trend by segment, channel, cohort, and product category before taking broad action.",
            owner,
            priority,
        )
    )


def _row(insight_type: str, insight: str, evidence: str, recommended_action: str, owner: str, priority: str) -> dict[str, object]:
    return {
        "insight_type": insight_type,
        "insight": insight,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "owner": owner,
        "priority": priority,
    }


def _write_report(insights: pd.DataFrame, project_config: ProjectConfig) -> None:
    lines = [
        "# Stakeholder Insights",
        "",
        "The following insights are generated from the governed marts, model outputs, and KPI engine.",
        "",
    ]
    for row in insights.to_dict("records"):
        lines.extend(
            [
                f"## {row['insight_type']}: {row['insight']}",
                f"- Evidence: {row['evidence']}",
                f"- Recommended action: {row['recommended_action']}",
                f"- Owner: {row['owner']}",
                f"- Priority: {row['priority']}",
                "",
            ]
        )
    write_markdown(lines, project_config.report_dir / "business_insights.md")


def main() -> None:
    generate_business_insights()


if __name__ == "__main__":
    main()

