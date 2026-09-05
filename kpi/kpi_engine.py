from __future__ import annotations

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def calculate_kpis(project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    project_config.ensure_directories()
    orders = pd.read_csv(project_config.mart_dir / "fact_orders.csv")
    customers = pd.read_csv(project_config.processed_dir / "customer_features.csv")
    cohort = pd.read_csv(project_config.mart_dir / "mart_cohort_retention.csv")
    engagement = pd.read_csv(project_config.mart_dir / "fact_engagement.csv")
    product_affinity_path = project_config.mart_dir / "mart_product_affinity.csv"
    clv_path = project_config.mart_dir / "mart_clv.csv"
    clv = pd.read_csv(clv_path) if clv_path.exists() else pd.DataFrame()
    affinity = pd.read_csv(product_affinity_path) if product_affinity_path.exists() else pd.DataFrame()

    completed_orders = orders.loc[orders["is_completed_order"].astype(str).isin(["True", "1", "true"])]
    total_customers = customers["customer_id"].nunique()
    total_orders = orders["order_id"].nunique()
    total_revenue = orders["net_revenue"].sum()
    total_profit = orders["return_adjusted_profit"].sum()
    total_discount = orders["discount_amount"].sum()
    total_return_loss = orders["return_loss"].sum()

    metrics = [
        _metric("Churn Rate", customers["churn_label"].mean(), "Percent", "Customer", "Customer Analytics", "Below 25%"),
        _metric("Retention Rate", 1 - customers["churn_label"].mean(), "Percent", "Customer", "Customer Analytics", "Above 75%"),
        _metric("Repeat Purchase Rate", customers["repeat_purchase_flag"].mean(), "Percent", "Customer", "Customer Analytics", "Above 45%"),
        _metric("Average Order Value", total_revenue / max(completed_orders["order_id"].nunique(), 1), "Currency", "Order", "BI", "Monitor by segment"),
        _metric("Revenue Per Customer", total_revenue / max(total_customers, 1), "Currency", "Customer", "Finance Analytics", "Increasing MoM"),
        _metric("Return Rate", orders["return_flag"].astype(str).isin(["True", "1", "true"]).mean(), "Percent", "Order", "Product Analytics", "Below 10%"),
        _metric("Average Historical CLV", customers["historical_clv"].mean(), "Currency", "Customer", "Customer Analytics", "Increasing QoQ"),
        _metric("Predicted CLV", clv["predicted_12m_clv"].mean() if len(clv) else customers["historical_clv"].mean(), "Currency", "Customer", "Customer Analytics", "Increasing QoQ"),
        _metric("Return-adjusted Margin", total_profit / max(total_revenue, 1), "Percent", "Order", "Finance Analytics", "Above 30%"),
        _metric("Month 3 Cohort Retention", cohort.loc[cohort["cohort_index"].eq(3), "retention_rate"].mean(), "Percent", "Cohort Month", "Customer Analytics", "Above 35%"),
        _metric("Engagement Rate", engagement["engagement_rate"].mean(), "Percent", "Customer", "Lifecycle Marketing", "Above 20%"),
        _metric("Top Product Affinity Score", affinity["affinity_score"].max() if len(affinity) else 0, "Decimal", "Product Pair", "Product Analytics", "Prioritize top decile"),
        _metric("Revenue Leakage from Returns and Discounts", total_return_loss + total_discount, "Currency", "Order", "Finance Analytics", "Reduce MoM"),
        _metric("Total Net Revenue", total_revenue, "Currency", "Business", "Executive", "Growth target"),
        _metric("Total Return-adjusted Profit", total_profit, "Currency", "Business", "Executive", "Growth target"),
        _metric("Total Orders", total_orders, "Integer", "Order", "Executive", "Growth target"),
    ]
    kpi_summary = pd.DataFrame(metrics)
    write_csv(kpi_summary, project_config.export_dir / "kpi_summary.csv")
    _write_kpi_governance(project_config)
    _write_dax_catalog(project_config)
    return kpi_summary


def _metric(name: str, value: float, display_format: str, grain: str, owner: str, threshold: str) -> dict[str, object]:
    return {
        "kpi_name": name,
        "value": round(float(value), 4) if pd.notna(value) else 0,
        "display_format": display_format,
        "grain": grain,
        "owner": owner,
        "threshold": threshold,
    }


def _write_kpi_governance(project_config: ProjectConfig) -> None:
    definitions = [
        ("Churn Rate", "Churned customers / total customers", "Share of customers likely inactive or lapsed.", "Customer Analytics", "Percent", "Customer", "Below 25%"),
        ("Retention Rate", "1 - churn rate", "Share of customers retained over the measurement window.", "Customer Analytics", "Percent", "Customer", "Above 75%"),
        ("Repeat Purchase Rate", "Customers with 2+ orders / total customers", "First-to-repeat purchase health.", "Customer Analytics", "Percent", "Customer", "Above 45%"),
        ("Average Order Value", "Net revenue / completed orders", "Average completed order size after returns and cancellations.", "BI", "Currency", "Order", "Monitor by segment"),
        ("Revenue Per Customer", "Net revenue / unique customers", "Customer monetization rate.", "Finance Analytics", "Currency", "Customer", "Increasing MoM"),
        ("Return Rate", "Returned orders / total orders", "Product quality, fit, and experience leakage.", "Product Analytics", "Percent", "Order", "Below 10%"),
        ("Customer Lifetime Value", "Historical profit + predicted future profit", "Expected customer economic value.", "Customer Analytics", "Currency", "Customer", "Increasing QoQ"),
        ("Segment Contribution %", "Segment revenue / total revenue", "Segment share of business performance.", "BI", "Percent", "Segment", "Monitor mix shifts"),
        ("Category Profitability", "Return-adjusted profit by category", "Category contribution after return leakage.", "Product Analytics", "Currency", "Category", "Positive margin"),
        ("Return-adjusted Margin", "Return-adjusted profit / net revenue", "Margin after returns and cancellations.", "Finance Analytics", "Percent", "Category or Business", "Above 30%"),
        ("Cohort Retention %", "Active cohort customers / month 0 cohort customers", "Repeat activity by acquisition month.", "Customer Analytics", "Percent", "Cohort Month", "Above target by month"),
        ("Engagement Rate", "Clicks / email opens", "Lifecycle audience responsiveness.", "Lifecycle Marketing", "Percent", "Customer", "Above 20%"),
        ("Product Affinity Score", "Confidence x lift", "Cross-sell strength between categories or products.", "Product Analytics", "Decimal", "Product Pair", "Prioritize top decile"),
        ("Revenue Leakage", "Return loss + discount amount", "Revenue and margin lost to returns and promotions.", "Finance Analytics", "Currency", "Order", "Reduce MoM"),
    ]
    lines = [
        "# KPI Governance Catalog",
        "",
        "| KPI Name | Formula | Business Meaning | Owner | Format | Grain | Threshold |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in definitions:
        lines.append("| " + " | ".join(row) + " |")
    write_markdown(lines, project_config.report_dir / "kpi_governance.md")


def _write_dax_catalog(project_config: ProjectConfig) -> None:
    lines = [
        "# Power BI Semantic Model and DAX Measure Catalog",
        "",
        "Recommended star schema relationships:",
        "- `fact_orders[customer_id]` to `dim_customer[customer_id]`",
        "- `fact_orders[product_id]` to `dim_product[product_id]`",
        "- `fact_orders[date_key]` to `dim_date[date_key]`",
        "- `fact_sessions[customer_id]` to `dim_customer[customer_id]`",
        "- `fact_customer_value[customer_id]` to `dim_customer[customer_id]`",
        "",
        "```DAX",
        "Total Net Revenue = SUM(fact_orders[net_revenue])",
        "Return Adjusted Profit = SUM(fact_orders[return_adjusted_profit])",
        "Return Adjusted Margin = DIVIDE([Return Adjusted Profit], [Total Net Revenue])",
        "Completed Orders = CALCULATE(DISTINCTCOUNT(fact_orders[order_id]), fact_orders[is_completed_order] = TRUE())",
        "Average Order Value = DIVIDE([Total Net Revenue], [Completed Orders])",
        "Customers = DISTINCTCOUNT(dim_customer[customer_id])",
        "Repeat Purchase Rate = AVERAGE(fact_customer_value[repeat_purchase_flag])",
        "Churn Rate = AVERAGE(fact_customer_value[churn_label])",
        "Retention Rate = 1 - [Churn Rate]",
        "Return Rate = DIVIDE(CALCULATE(DISTINCTCOUNT(fact_orders[order_id]), fact_orders[return_flag] = TRUE()), DISTINCTCOUNT(fact_orders[order_id]))",
        "Revenue Leakage = SUM(fact_orders[return_loss]) + SUM(fact_orders[discount_amount])",
        "Predicted CLV = AVERAGE(mart_clv[predicted_12m_clv])",
        "Cohort Retention % = AVERAGE(fact_cohort_retention[retention_rate])",
        "```",
    ]
    write_markdown(lines, project_config.report_dir / "powerbi_semantic_model_notes.md")


def main() -> None:
    calculate_kpis()


if __name__ == "__main__":
    main()

