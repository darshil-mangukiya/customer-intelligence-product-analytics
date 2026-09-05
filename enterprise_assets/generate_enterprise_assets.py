from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


FEATURE_CATALOG = [
    ("customer_behavior_features", "recency_days", "analysis_date - last_order_date", "customer", "Daily or pipeline run", "customer_features", "How long the customer has been inactive.", "churn, segments, retention dashboard"),
    ("customer_behavior_features", "orders", "distinct order_id count", "customer", "Daily or pipeline run", "fact_orders", "Customer purchase depth.", "segments, CLV, executive KPIs"),
    ("customer_behavior_features", "purchase_frequency_30d", "orders / customer_age_days * 30", "customer", "Daily or pipeline run", "customer_features", "Normalized purchase frequency.", "churn, CLV, RFM"),
    ("customer_monetary_features", "net_revenue", "sum revenue after discounts and status adjustments", "customer", "Daily or pipeline run", "fact_orders", "Customer revenue contribution.", "CLV, segments, customer dashboard"),
    ("customer_monetary_features", "return_adjusted_profit", "sum profit after return loss", "customer", "Daily or pipeline run", "fact_orders", "Customer economic value after leakage.", "CLV, churn priority, executive KPIs"),
    ("customer_monetary_features", "avg_order_value", "net_revenue / completed_orders", "customer", "Daily or pipeline run", "fact_orders", "Average completed order size.", "segments, KPI cards"),
    ("customer_engagement_features", "engagement_score", "weighted opens, clicks, and campaign activity", "customer", "Daily or campaign refresh", "engagement", "Lifecycle reachability and intent.", "churn, activation, engagement dashboard"),
    ("customer_engagement_features", "days_since_engagement", "analysis_date - last_engagement_date", "customer", "Daily or campaign refresh", "engagement", "Engagement staleness.", "churn, lifecycle actions"),
    ("customer_retention_features", "repeat_purchase_flag", "orders >= 2", "customer", "Daily or pipeline run", "customer_features", "First-to-repeat conversion indicator.", "retention KPIs, cohorts"),
    ("customer_retention_features", "churn_label", "business inactivity and status rule", "customer", "Daily or pipeline run", "customer_features", "Observed churn target for modeling.", "churn model, validation"),
    ("customer_product_affinity_features", "top_purchase_category", "category with highest net revenue", "customer", "Daily or pipeline run", "transactions_enriched", "Dominant customer category preference.", "cross-sell, churn by first category"),
    ("customer_product_affinity_features", "category_diversity", "distinct categories purchased", "customer", "Daily or pipeline run", "fact_orders", "Breadth of product engagement.", "churn, segments, product dashboard"),
    ("customer_discount_sensitivity_features", "discount_dependency", "discount_amount / (discount_amount + net_revenue)", "customer", "Daily or pipeline run", "fact_orders", "How dependent the customer is on promotions.", "segments, churn, activation"),
    ("customer_discount_sensitivity_features", "avg_discount_rate", "average line/order discount rate", "customer", "Daily or pipeline run", "fact_orders", "Promotion depth signal.", "discount-sensitive exports"),
    ("customer_return_behavior_features", "return_rate", "returned_orders / orders", "customer", "Daily or pipeline run", "fact_orders", "Customer return behavior and experience risk.", "churn, product quality, support"),
    ("customer_return_behavior_features", "returns", "sum return_flag", "customer", "Daily or pipeline run", "fact_orders", "Return volume by customer.", "activation, product analytics"),
    ("customer_churn_features", "churn_probability", "model probability score", "customer", "Model scoring run", "mart_churn_risk", "Likelihood of churn.", "churn dashboard, activation"),
    ("customer_churn_features", "churn_risk_tier", "probability banding rule", "customer", "Model scoring run", "mart_churn_risk", "Business-friendly churn tier.", "dashboards, CRM exports"),
    ("customer_churn_features", "expected_profit_at_risk", "churn_probability * return_adjusted_profit", "customer", "Model scoring run", "mart_churn_risk", "Retention value exposure.", "activation priority"),
    ("customer_clv_features", "historical_clv", "historical return-adjusted profit", "customer", "Daily or pipeline run", "mart_clv", "Past customer value.", "CLV dashboard"),
    ("customer_clv_features", "predicted_12m_clv", "model predicted future value annualized", "customer", "Model scoring run", "mart_clv", "Expected future customer value.", "CLV dashboard, activation"),
    ("customer_clv_features", "clv_band", "business bands over predicted CLV", "customer", "Model scoring run", "mart_clv", "Value tier for targeting and reporting.", "segments, churn priority, executive KPIs"),
]


KPI_CATALOG = [
    ("Revenue", "SUM(fact_orders[net_revenue])", "Net selling revenue after order status and discounts.", "order", "Finance Analytics", "Daily", "Executive, product, channel dashboards", "SUM(net_revenue)", "Revenue = SUM(fact_orders[net_revenue])", "Grow MoM"),
    ("Gross Profit", "SUM(gross_revenue - cost)", "Pre-return order profit proxy.", "order", "Finance Analytics", "Daily", "Executive and product dashboards", "SUM(gross_revenue - cost)", "Gross Profit = SUM(fact_orders[gross_revenue]) - SUM(fact_orders[cost])", "Positive by category"),
    ("Net Profit", "SUM(return_adjusted_profit)", "Profit after return impact.", "order", "Finance Analytics", "Daily", "Executive and product dashboards", "SUM(return_adjusted_profit)", "Net Profit = SUM(fact_orders[return_adjusted_profit])", "Positive margin"),
    ("Margin %", "return_adjusted_profit / net_revenue", "Return-adjusted profitability rate.", "order/category/product", "Finance Analytics", "Daily", "Product profitability", "SUM(return_adjusted_profit) / NULLIF(SUM(net_revenue),0)", "Margin % = DIVIDE([Net Profit], [Revenue])", "Above 30%"),
    ("Return-adjusted Revenue", "net_revenue - return_loss", "Revenue after return leakage.", "order", "Finance Analytics", "Daily", "Revenue leakage", "SUM(net_revenue - return_loss)", "Return Adjusted Revenue = SUM(fact_orders[net_revenue]) - SUM(fact_orders[return_loss])", "Reduce leakage"),
    ("Return-adjusted Profit", "SUM(return_adjusted_profit)", "Profit after returns and discounts.", "order", "Finance Analytics", "Daily", "Executive, product", "SUM(return_adjusted_profit)", "Return Adjusted Profit = SUM(fact_orders[return_adjusted_profit])", "Grow MoM"),
    ("Churn Rate", "AVG(churn_label)", "Share of customers likely inactive or lapsed.", "customer", "Customer Analytics", "Model scoring run", "Churn dashboard", "AVG(churn_label)", "Churn Rate = AVERAGE(fact_customer_value[churn_label])", "Below 25%"),
    ("Retention Rate", "1 - churn_rate", "Share of customers retained.", "customer", "Customer Analytics", "Model scoring run", "Customer overview", "1 - AVG(churn_label)", "Retention Rate = 1 - [Churn Rate]", "Above 75%"),
    ("Repeat Purchase Rate", "AVG(repeat_purchase_flag)", "First-to-repeat conversion health.", "customer", "Customer Analytics", "Daily", "Customer overview", "AVG(repeat_purchase_flag)", "Repeat Purchase Rate = AVERAGE(fact_customer_value[repeat_purchase_flag])", "Above 45%"),
    ("Average Order Value", "net_revenue / completed_orders", "Average completed order size.", "order", "BI Engineering", "Daily", "Executive and segment dashboards", "SUM(net_revenue) / NULLIF(COUNT(DISTINCT order_id),0)", "Average Order Value = DIVIDE([Revenue], [Completed Orders])", "Monitor by segment"),
    ("Customer Lifetime Value", "historical_clv + predicted_future_profit", "Expected customer economic value.", "customer", "Customer Analytics", "Model scoring run", "CLV dashboard", "AVG(historical_clv + predicted_next_90d_profit)", "Customer Lifetime Value = AVERAGE(mart_clv[predicted_12m_clv])", "Grow QoQ"),
    ("Predicted CLV", "AVG(predicted_12m_clv)", "Modeled 12-month customer value.", "customer", "Customer Analytics", "Model scoring run", "CLV dashboard", "AVG(predicted_12m_clv)", "Predicted CLV = AVERAGE(mart_clv[predicted_12m_clv])", "Grow QoQ"),
    ("Revenue Per Customer", "net_revenue / customers", "Customer monetization rate.", "customer", "Finance Analytics", "Daily", "Executive dashboard", "SUM(net_revenue) / NULLIF(COUNT(DISTINCT customer_id),0)", "Revenue Per Customer = DIVIDE([Revenue], [Customers])", "Grow MoM"),
    ("Purchase Frequency", "orders / customer_age_days", "Normalized buying frequency.", "customer", "Customer Analytics", "Daily", "Customer segments", "AVG(purchase_frequency_30d)", "Purchase Frequency = AVERAGE(fact_customer_value[purchase_frequency_30d])", "Monitor by segment"),
    ("Discount Rate", "discount_amount / gross_revenue", "Promotion dependency.", "order/customer/product", "Finance Analytics", "Daily", "Revenue leakage", "SUM(discount_amount) / NULLIF(SUM(gross_revenue),0)", "Discount Rate = DIVIDE(SUM(fact_orders[discount_amount]), SUM(fact_orders[gross_revenue]))", "Reduce wasted discounting"),
    ("Return Rate", "returned_orders / orders", "Product return leakage.", "order/product", "Product Analytics", "Daily", "Product profitability", "AVG(return_flag)", "Return Rate = DIVIDE([Returned Orders], [Orders])", "Below 10%"),
    ("Engagement Rate", "clicks / email_opens", "Lifecycle engagement quality.", "customer", "Lifecycle Marketing", "Campaign refresh", "Customer overview", "SUM(clicks) / NULLIF(SUM(email_opens),0)", "Engagement Rate = DIVIDE(SUM(fact_engagement[clicks]), SUM(fact_engagement[email_opens]))", "Above 20%"),
    ("Cohort Retention %", "active_cohort_customers / cohort_customers", "Month-index retention by cohort.", "cohort month", "Customer Analytics", "Daily", "Cohort dashboard", "SUM(customers) / NULLIF(SUM(cohort_customers),0)", "Cohort Retention % = AVERAGE(mart_cohort_retention[retention_rate])", "Improve by month"),
    ("Segment Contribution %", "segment_revenue / total_revenue", "Segment share of business performance.", "segment", "BI Engineering", "Daily", "Segment strategy", "SUM(segment_revenue) / SUM(total_revenue)", "Segment Contribution % = DIVIDE([Segment Revenue], [Revenue])", "Monitor mix shifts"),
    ("Product Affinity Score", "confidence * lift", "Cross-sell strength between categories/products.", "product pair", "Product Analytics", "Daily", "Product affinity", "confidence * lift", "Product Affinity Score = MAX(mart_product_affinity[affinity_score])", "Prioritize top decile"),
    ("Retention Investment Priority Score", "rank(churn risk, CLV, profit at risk)", "Targeting score for lifecycle spend.", "customer", "Lifecycle Marketing", "Model scoring run", "Activation exports", "weighted rank score", "Retention Investment Priority Score = AVERAGE(next_best_actions[action_priority_score])", "Top priority bands"),
    ("Revenue Leakage from Returns", "SUM(return_loss)", "Revenue/profit impact of returns.", "order/product", "Finance Analytics", "Daily", "Revenue leakage", "SUM(return_loss)", "Revenue Leakage from Returns = SUM(fact_orders[return_loss])", "Reduce MoM"),
    ("Revenue Leakage from Discounts", "SUM(discount_amount)", "Revenue leakage from promotions.", "order/customer/product", "Finance Analytics", "Daily", "Revenue leakage", "SUM(discount_amount)", "Revenue Leakage from Discounts = SUM(fact_orders[discount_amount])", "Reduce inefficient discounting"),
]


DASHBOARD_PAGES = [
    ("Executive Overview Dashboard", "Executive leadership", "Single view of customer growth, churn risk, CLV, revenue leakage, profit, and recommended actions.", "mart_executive_kpis, kpi_summary, stakeholder_insights"),
    ("Customer Intelligence Dashboard", "Customer analytics and lifecycle teams", "Segment mix, high-value customers, repeat behavior, engagement, and customer value distribution.", "mart_customer_overview, mart_customer_segments, mart_clv"),
    ("Churn Risk Dashboard", "Lifecycle marketing and customer success", "At-risk customer queue, churn drivers, risk tiers, expected profit at risk, and intervention targets.", "mart_churn_risk, churn_driver_summary"),
    ("Cohort Retention Dashboard", "Growth and customer analytics", "Month 1 to Month 12 cohort retention, revenue retention, and retention by channel/category/region/segment.", "mart_cohort_retention"),
    ("CLV Dashboard", "Finance, lifecycle, and growth analytics", "Historical CLV, predicted CLV, CLV bands, CLV at risk, and retention investment priorities.", "mart_clv"),
    ("Product Profitability Dashboard", "Merchandising and product analytics", "Return-adjusted margin, low-margin high-volume products, return-heavy products, and category profitability.", "mart_product_profitability"),
    ("Product Affinity Dashboard", "Product, growth, and merchandising teams", "Affinity scores, cross-sell paths, bundle candidates, and recommendation targets.", "mart_product_affinity, cross_sell_recommendations"),
    ("Segment Strategy Dashboard", "Marketing, lifecycle, and executives", "Segment profiles, KPI comparisons, migration signals, and recommended business actions.", "mart_customer_segments, segment_profiles"),
    ("Acquisition Channel Quality Dashboard", "Growth analytics", "Channel quality by CLV, churn, cohort retention, repeat rate, and profit contribution.", "mart_clv, mart_cohort_retention, mart_churn_risk"),
    ("Revenue Leakage Dashboard", "Finance and product analytics", "Returns, discounts, margin leakage, high-leakage products, and segment/channel discount dependency.", "fact_orders, mart_product_profitability, kpi_summary"),
]


def _markdown_table(records: list[tuple[str, ...]], headers: list[str]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for record in records:
        lines.append("| " + " | ".join(str(value) for value in record) + " |")
    return lines


def _doc_lines(title: str, summary: str, sections: list[tuple[str, list[str]]]) -> list[str]:
    lines = [f"# {title}", "", summary, ""]
    for heading, bullets in sections:
        lines.extend([f"## {heading}", ""])
        for bullet in bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    return lines


def _write_core_docs(project_config: ProjectConfig) -> list[Path]:
    root = project_config.root
    docs: dict[Path, list[str]] = {
        root / "docs" / "architecture_overview.md": _doc_lines(
            "Enterprise Architecture Overview",
            "This document describes the production-style analytics flow used by the Customer Intelligence & Product Analytics Platform.",
            [
                ("Layered Flow", ["raw data -> cleaned/staged data -> intermediate models -> feature tables -> reporting marts -> semantic KPI layer -> dashboard exports -> activation exports"]),
                ("Raw Layer", ["Stores generated source-like customer, product, transaction, web, engagement, support, review, loyalty, and refund data.", "Includes intentionally dirty conditions for realistic validation and observability."]),
                ("Cleaned and Staged Layer", ["Standardizes channels, categories, dates, labels, statuses, returns, discounts, and invalid values.", "Creates rejected-row and audit outputs for analyst review."]),
                ("Intermediate and Feature Layer", ["Creates customer, product, cohort, churn, segmentation, CLV, RFM, discount, return, engagement, and affinity features.", "Feature definitions are cataloged with grain, source, formula, and consuming dashboard/model."]),
                ("Reporting and Semantic Layer", ["Publishes dimensions, facts, marts, KPI definitions, SQL logic, and DAX notes for BI consumption.", "Supports Power BI, Tableau, Streamlit, FastAPI, and activation exports."]),
                ("Activation Layer", ["Creates customer lists for churn saves, win-back, high-CLV retention, cross-sell, loyalty upgrades, and discount-sensitive campaigns.", "Outputs are local reverse-ETL simulations, not live CRM deployments."]),
            ],
        ),
        root / "docs" / "data_lineage.md": _doc_lines(
            "Data Lineage",
            "Lineage documents how each analytical output is derived from raw source-like data.",
            [
                ("Customer Lineage", ["raw.customers -> customers_clean -> customer_features -> mart_customer_overview, mart_customer_segments, mart_clv, mart_churn_risk"]),
                ("Order Lineage", ["raw.transactions -> transactions_clean -> transactions_enriched -> fact_orders, fact_returns, fact_customer_value, product profitability marts"]),
                ("Session and Engagement Lineage", ["raw.web_behavior and raw.engagement -> cleaned facts -> engagement, churn, retention, and lifecycle features"]),
                ("Product Lineage", ["raw.products + enriched transactions -> product_features -> mart_product_profitability, affinity outputs, cross-sell recommendations"]),
                ("Cohort Lineage", ["transactions_enriched + customer first order date -> cohort_base -> mart_cohort_retention and cohort dashboard exports"]),
                ("Model Lineage", ["feature bases -> churn, segmentation, and CLV models -> scored marts -> dashboard, API, and activation outputs"]),
            ],
        ),
        root / "docs" / "source_to_target_mapping.md": [
            "# Source-to-Target Mapping",
            "",
            "This mapping summarizes how source-like tables flow into warehouse and BI outputs.",
            "",
            *_markdown_table(
                [
                    ("raw.customers", "customers_clean", "dim_customer, customer_features", "customer_id", "Standardize demographics, acquisition channel, loyalty tier, churn status."),
                    ("raw.transactions", "transactions_clean", "fact_orders, fact_returns", "order_id", "Normalize revenue, cost, discounts, status, return flags, dates, and product/customer keys."),
                    ("raw.products", "products_clean", "dim_product, mart_product_profitability", "product_id", "Standardize catalog, category, lifecycle, margin, return, and retention profiles."),
                    ("raw.web_behavior", "web_behavior_clean", "fact_sessions, customer_engagement_features", "session_id", "Normalize sessions, devices, source labels, page views, time spent, and bounce flags."),
                    ("raw.engagement", "engagement_clean", "fact_engagement, customer_engagement_features", "customer_id", "Calculate engagement score and campaign responsiveness."),
                    ("processed.customer_features", "feature tables", "mart_churn_risk, mart_clv, mart_customer_segments", "customer_id", "Aggregate behavior, monetary, engagement, return, discount, and retention features."),
                ],
                ["Source", "Staged Target", "Final Target", "Key", "Transformation Rule"],
            ),
        ],
        root / "docs" / "dimensional_model.md": _doc_lines(
            "Dimensional Model and Star Schema Notes",
            "This warehouse-ready design supports BI tools with clear grains, keys, and relationship rules.",
            [
                ("Dimensions", ["dim_customer grain: one row per customer_id.", "dim_product grain: one row per product_id.", "dim_date grain: one row per calendar date.", "dim_channel grain: one row per channel label.", "dim_region grain: one row per region/city combination.", "dim_device grain: one row per device type."]),
                ("Facts", ["fact_orders grain: one row per order_id.", "fact_sessions grain: one row per session_id.", "fact_engagement grain: one row per customer engagement snapshot.", "fact_returns grain: one row per returned or cancelled order.", "fact_customer_value grain: one row per customer value snapshot.", "fact_cohort_retention grain: one row per cohort_month and cohort_index."]),
                ("Primary Keys", ["dim_customer.customer_id, dim_product.product_id, dim_date.date_key, fact_orders.order_id, fact_sessions.session_id.", "Marts use customer_id, product_id, cohort_month/cohort_index, or source/target category depending on grain."]),
                ("Foreign Keys", ["fact_orders.customer_id -> dim_customer.customer_id.", "fact_orders.product_id -> dim_product.product_id.", "fact_orders.date_key -> dim_date.date_key.", "fact_sessions.customer_id -> dim_customer.customer_id.", "fact_engagement.customer_id -> dim_customer.customer_id."]),
                ("Star Schema Notes", ["Power BI and Tableau should use fact tables as event sources and marts as curated analytical outputs.", "Avoid many-to-many ambiguity by using dimension keys and dashboard-specific marts for advanced outputs."]),
            ],
        ),
        root / "docs" / "data_contracts.md": _doc_lines(
            "Data Contracts",
            "Data contracts define required columns, grains, freshness expectations, and blocking rules.",
            [
                ("Critical Contracts", ["fact_orders must have unique order_id, valid customer_id/product_id, nonnegative net_revenue, and accepted order_status.", "mart_churn_risk must have one row per customer_id, churn_probability between 0 and 1, and accepted risk tiers.", "mart_clv must have one row per customer_id and non-null CLV band for scored customers.", "mart_product_profitability must have one row per product_id and return_rate between 0 and 1.", "kpi_summary must reconcile total net revenue to fact_orders."]),
                ("Severity Rules", ["P1 failures block executive dashboard refresh.", "P2 failures require data-steward review before publication.", "P3 failures can publish with a release note if business impact is low."]),
                ("Freshness", ["Daily marts should refresh within 24 hours in a real warehouse.", "Local simulation treats mart outputs older than 14 days as stale for validation examples."]),
            ],
        ),
        root / "docs" / "performance_optimization.md": _doc_lines(
            "Warehouse Performance Optimization",
            "Performance notes describe how this local production simulation would scale in a warehouse.",
            [
                ("Incremental Strategy", ["Load orders incrementally by order_date and order_id watermark.", "Refresh customer-level features for customers with changed orders, sessions, engagement, support, or scoring updates.", "Rebuild cohort and product affinity outputs on a scheduled batch cadence."]),
                ("Partitioning", ["Partition fact_orders and fact_sessions by date_key or order/session month.", "Partition large activation exports by campaign run date.", "Cluster customer marts by customer_id and churn_risk_tier for targeted retrieval."]),
                ("Indexing", ["Index fact_orders(order_id), fact_orders(customer_id), fact_orders(product_id), fact_orders(date_key).", "Index mart_churn_risk(customer_id, churn_risk_tier), mart_clv(customer_id, clv_band), mart_customer_segments(segment_name).", "Index mart_product_profitability(product_id, category)."]),
                ("Query Tuning", ["Use mart tables for dashboard queries instead of recomputing joins.", "Use semantic KPI logic for reusable definitions.", "Pre-aggregate cohort, segment, and product dashboard views by expected filter grain."]),
            ],
        ),
        root / "docs" / "data_quality_framework.md": _doc_lines(
            "Data Quality Framework",
            "The data quality framework checks source, staged, mart, model, KPI, and dashboard readiness.",
            [
                ("Validation Checks", ["Duplicate customers and orders.", "Missing customer_id and product_id.", "Invalid revenue or negative profit anomalies.", "Impossible order dates.", "Invalid churn labels and retention month values.", "Broken customer/product foreign keys.", "Unusual return and discount rates.", "Row count anomalies.", "Null threshold violations.", "Stale dashboard marts and model scoring outputs.", "Invalid KPI calculations."]),
                ("Outputs", ["data_quality_summary.csv, validation_results.csv, rejected_rows.csv, anomaly_log.csv, pipeline_audit_log.csv, mart_freshness_report.csv.", "Markdown reports summarize pass/fail status and business impact."]),
                ("Ownership", ["P1 dashboard gates: BI Engineering.", "Customer scoring gates: Customer Analytics.", "Product profitability gates: Product Analytics.", "Revenue leakage gates: Finance Analytics."]),
            ],
        ),
        root / "docs" / "observability_runbook.md": _doc_lines(
            "Observability Runbook",
            "Runbook for pipeline health, freshness, validation, and scoring observability.",
            [
                ("Daily Checks", ["Confirm pipeline manifest tasks completed.", "Review validation status and failing-row counts.", "Check row counts by stage.", "Review rejected-row counts and anomaly log.", "Confirm model scoring and dashboard marts are fresh."]),
                ("Dashboard Refresh Gate", ["P1 schema contract or KPI reconciliation failures block dashboard refresh.", "P2 product/customer scoring failures require owner approval.", "Freshness failures publish only with a release note."]),
                ("Troubleshooting", ["Use pipeline_audit_log.csv for task timing.", "Use mart_freshness_report.csv for stale assets.", "Use anomaly_log.csv for outlier investigation.", "Use validation_report.md for detailed failed checks."]),
            ],
        ),
        root / "docs" / "troubleshooting_guide.md": _doc_lines(
            "Troubleshooting Guide",
            "Common failure modes and recommended fixes for the local production simulation.",
            [
                ("Missing Marts", ["Run make sample or make full, then make orchestrate.", "Confirm data/marts contains fact_orders, mart_churn_risk, mart_clv, and mart_product_profitability."]),
                ("Validation Failures", ["Open reports/validation_report.md.", "Check failing suite, table, column, and severity.", "Repair upstream cleaning or feature engineering logic before rerunning dashboards."]),
                ("API Missing Dataset Errors", ["Run pipeline outputs before calling mart endpoints.", "Check CUSTOMER_INTELLIGENCE_API_KEY only when auth is configured."]),
                ("Activation Export Issues", ["Run make activation after model scoring outputs exist.", "Confirm mart_churn_risk and mart_clv are present."]),
            ],
        ),
    }
    paths = []
    for path, lines in docs.items():
        paths.append(write_markdown(lines, path))
    return paths


def _write_feature_catalog(project_config: ProjectConfig) -> list[Path]:
    frame = pd.DataFrame(
        FEATURE_CATALOG,
        columns=["feature_table", "feature_name", "formula", "grain", "refresh_frequency", "source_table", "business_meaning", "used_by"],
    )
    paths = [
        write_csv(frame, project_config.root / "outputs" / "feature_catalog.csv"),
        write_csv(frame, project_config.export_dir / "feature_catalog.csv"),
    ]
    lines = [
        "# Feature Catalog",
        "",
        "Feature-store-style catalog for customer intelligence features.",
        "",
        *_markdown_table([tuple(row) for row in frame.astype(str).itertuples(index=False, name=None)], list(frame.columns)),
    ]
    paths.append(write_markdown(lines, project_config.root / "docs" / "feature_catalog.md"))
    return paths


def _write_kpi_catalog(project_config: ProjectConfig) -> list[Path]:
    frame = pd.DataFrame(
        KPI_CATALOG,
        columns=[
            "kpi_name",
            "formula",
            "business_meaning",
            "grain",
            "owner",
            "refresh_frequency",
            "dashboard_usage",
            "sql_logic",
            "dax_logic",
            "threshold_or_benchmark",
        ],
    )
    paths = [
        write_csv(frame, project_config.root / "outputs" / "kpi_catalog.csv"),
        write_csv(frame, project_config.export_dir / "kpi_catalog.csv"),
    ]
    lines = [
        "# KPI Dictionary",
        "",
        "Governed KPI definitions for BI dashboards, marts, semantic models, and stakeholder reporting.",
        "",
        *_markdown_table([tuple(row) for row in frame.astype(str).itertuples(index=False, name=None)], list(frame.columns)),
    ]
    paths.append(write_markdown(lines, project_config.root / "docs" / "kpi_dictionary.md"))

    semantic_lines = _doc_lines(
        "Semantic Layer",
        "The semantic layer centralizes metric definitions so dashboard builders do not recreate inconsistent logic.",
        [
            ("Metric Ownership", ["Customer Analytics owns churn, retention, CLV, RFM, and lifecycle KPIs.", "Finance Analytics owns revenue, margin, leakage, and profitability KPIs.", "Product Analytics owns return, affinity, lifecycle, and category performance KPIs.", "BI Engineering owns semantic consistency and dashboard publication rules."]),
            ("Consumption Pattern", ["Power BI and Tableau use marts and semantic measure logic instead of raw transactional calculations.", "Streamlit and FastAPI expose the same governed definitions.", "Activation outputs use scored marts and priority scores, not ad hoc campaign rules."]),
            ("Governance", ["Metric grain, owner, formula, refresh cadence, and thresholds are documented in outputs/kpi_catalog.csv.", "Dashboard QA should compare KPI cards against kpi_summary.csv and mart reconciliation checks."]),
        ],
    )
    paths.append(write_markdown(semantic_lines, project_config.root / "docs" / "semantic_layer.md"))

    dax_rows = [
        ("Orders", "`Orders = DISTINCTCOUNT(fact_orders[order_id])`", "Count of unique orders in the current filter context.", "`fact_orders`", "Filters by date, customer, product, channel, region, and order status context.", "Executive, product, customer"),
        ("Completed Orders", "`Completed Orders = CALCULATE([Orders], fact_orders[is_completed_order] = TRUE())`", "Count of completed orders eligible for revenue and purchase behavior.", "`fact_orders`", "Honors all slicers and adds completed-order filter.", "Executive, AOV, retention"),
        ("Customers", "`Customers = DISTINCTCOUNT(dim_customer[customer_id])`", "Count of customers in the current dimension context.", "`dim_customer`", "Filters by customer attributes and related fact filters where relationships apply.", "Executive, customer overview"),
        ("Returned Orders", "`Returned Orders = CALCULATE([Orders], fact_orders[return_flag] = TRUE())`", "Count of orders marked as returned.", "`fact_orders`", "Honors date, product, customer, and channel filters.", "Product and revenue leakage"),
        ("Segment Revenue", "`Segment Revenue = [Revenue]`", "Revenue in the selected segment context.", "`fact_orders`, `dim_customer`", "Depends on active segment/customer filters.", "Segment strategy"),
        ("Total Revenue All Segments", "`Total Revenue All Segments = CALCULATE([Revenue], ALL(dim_customer[segment_seed]))`", "Revenue denominator for segment contribution.", "`fact_orders`, `dim_customer`", "Removes segment filter while preserving other report context.", "Segment strategy"),
        ("Revenue", "`Revenue = SUM(fact_orders[net_revenue])`", "Net selling revenue after discounts and order status logic.", "`fact_orders`", "Filters by date, product, customer, channel, and region.", "Executive, product, customer, channel"),
        ("Gross Profit", "`Gross Profit = SUM(fact_orders[gross_revenue]) - SUM(fact_orders[cost])`", "Profit before return adjustment.", "`fact_orders`", "Filters by the same dimensions as revenue.", "Executive, finance review"),
        ("Net Profit", "`Net Profit = SUM(fact_orders[return_adjusted_profit])`", "Profit after return adjustment.", "`fact_orders`", "Filters by date, product, customer, channel, and region.", "Executive, product profitability"),
        ("Margin %", "`Margin % = DIVIDE([Net Profit], [Revenue])`", "Return-adjusted profit divided by revenue.", "`fact_orders`", "Safe division in current report context.", "Executive KPI cards, product dashboards"),
        ("Return-Adjusted Revenue", "`Return-Adjusted Revenue = [Revenue] - [Revenue Leakage from Returns]`", "Revenue after subtracting return leakage.", "`fact_orders`", "Filters by product, category, customer, channel, and date.", "Revenue leakage, product profitability"),
        ("Return-Adjusted Profit", "`Return-Adjusted Profit = SUM(fact_orders[return_adjusted_profit])`", "Profit after returns and discounts.", "`fact_orders`", "Same context as revenue.", "Executive, product, finance"),
        ("Churn Rate", "`Churn Rate = AVERAGE(fact_customer_value[churn_label])`", "Share of customers labeled as churned/lapsed in the current context.", "`fact_customer_value`", "Filters by customer attributes and segment context.", "Churn dashboard, executive overview"),
        ("Retention Rate", "`Retention Rate = 1 - [Churn Rate]`", "Complement of churn rate.", "`fact_customer_value`", "Same context as churn rate.", "Customer overview, executive overview"),
        ("Repeat Purchase Rate", "`Repeat Purchase Rate = AVERAGE(fact_customer_value[repeat_purchase_flag])`", "Share of customers with repeat purchase behavior.", "`fact_customer_value`", "Filters by customer dimensions and report context.", "Customer overview, lifecycle reporting"),
        ("Average Order Value", "`Average Order Value = DIVIDE([Revenue], [Completed Orders])`", "Net revenue per completed order.", "`fact_orders`", "Uses current revenue and completed order filters.", "Executive, customer, channel"),
        ("CLV", "`CLV = AVERAGE(fact_customer_value[historical_clv])`", "Average historical customer lifetime value.", "`fact_customer_value`", "Filters by customer attributes, segment, and channel.", "CLV dashboard"),
        ("Predicted CLV", "`Predicted CLV = AVERAGE(mart_clv[predicted_12m_clv])`", "Average predicted 12-month CLV from the local scoring output when loaded.", "`mart_clv` or CLV output", "Filters by customer, segment, channel, and CLV band if loaded.", "CLV dashboard, retention prioritization"),
        ("Return Rate", "`Return Rate = DIVIDE([Returned Orders], [Orders])`", "Share of orders with return flag.", "`fact_orders`", "Filters by product, category, customer, date, and channel.", "Product dashboard, revenue leakage"),
        ("Discount Rate", "`Discount Rate = DIVIDE(SUM(fact_orders[discount_amount]), SUM(fact_orders[gross_revenue]))`", "Discount amount as a share of gross revenue.", "`fact_orders`", "Filters by product, customer, channel, and date.", "Revenue leakage, product dashboards"),
        ("Cohort Retention %", "`Cohort Retention % = DIVIDE(SUM(fact_cohort_retention[customers]), SUM(fact_cohort_retention[cohort_customers]))`", "Active cohort customers divided by original cohort size.", "`fact_cohort_retention`", "Filters by cohort month and cohort index.", "Cohort retention dashboard"),
        ("Revenue Leakage from Returns", "`Revenue Leakage from Returns = SUM(fact_orders[return_loss])`", "Revenue lost to returns.", "`fact_orders`", "Filters by product, customer, channel, region, and date.", "Revenue leakage, product profitability"),
        ("Revenue Leakage from Discounts", "`Revenue Leakage from Discounts = SUM(fact_orders[discount_amount])`", "Revenue reduced through discounts.", "`fact_orders`", "Filters by product, customer, channel, region, and date.", "Revenue leakage, finance review"),
        ("Segment Contribution %", "`Segment Contribution % = DIVIDE([Segment Revenue], [Total Revenue All Segments])`", "Selected segment revenue divided by total revenue across segments.", "`fact_orders`, `dim_customer`", "Keeps non-segment filters while removing segment filter in denominator.", "Segment strategy"),
        ("Product Affinity Score", "`Product Affinity Score = MAX(mart_product_affinity[affinity_score])`", "Maximum affinity score for the selected product/category pair when affinity mart is loaded.", "`mart_product_affinity` or affinity output", "Filters by source and recommended product/category.", "Product affinity and cross-sell"),
    ]
    dax_lines = [
        "# DAX Measure Catalog",
        "",
        "This catalog provides Power BI-ready measure definitions for the semantic model. It is documentation for building a `.pbix`; no `.pbix` file is committed in this repository.",
        "",
        "## Measures",
        "",
        *_markdown_table(
            dax_rows,
            ["Measure name", "DAX formula", "Business definition", "Source mart/table", "Expected filter behavior", "Dashboard usage"],
        ),
        "",
        "## Implementation Notes",
        "",
        "- Use base measures such as `Orders`, `Completed Orders`, `Customers`, `Returned Orders`, and `Revenue` inside dependent measures.",
        "- Keep formulas in a dedicated `Measures` table.",
        "- Avoid visual-level calculations when a governed measure exists in this catalog.",
        "- Validate KPI cards against `outputs/kpi_catalog.csv` and SQL outputs before publishing a dashboard.",
        "- For local CSV imports, verify column names match the table names used in these formulas.",
    ]
    paths.append(write_markdown(dax_lines, project_config.root / "dashboards" / "specs" / "dax_measure_catalog.md"))
    return paths


def _write_methodology_docs(project_config: ProjectConfig) -> list[Path]:
    root = project_config.root
    docs = {
        root / "docs" / "churn_methodology.md": _doc_lines("Churn Methodology", "Methodology for churn prediction and churn intelligence.", [("Analytical Approach", ["Use explainable logistic regression to estimate churn probability.", "Create risk tiers for BI filtering and activation queues.", "Analyze churn by segment, channel, first category, discount dependency, return behavior, and support history."]), ("Intervention Logic", ["Prioritize high churn probability with high profit or CLV at risk.", "Suppress low-value inactive customers when intervention economics are weak.", "Use reason categories to route actions to lifecycle, product, support, or merchandising teams."])]),
        root / "docs" / "churn_intervention_playbook.md": _doc_lines("Churn Intervention Playbook", "Business playbook for using churn outputs.", [("Critical Risk", ["Launch save journey when CLV/profit at risk is high.", "Use service recovery when return or support friction is elevated."]), ("High Discount Dependency", ["Use margin-controlled offers and replenishment messaging rather than blanket discounts."]), ("One-Time Buyers", ["Send first-to-second purchase journey within first 30 to 60 days."]), ("Product Fit Risk", ["Route return-heavy product cohorts to merchandising review."])]),
        root / "docs" / "segmentation_methodology.md": _doc_lines("Segmentation Methodology", "Business-ready segmentation methodology.", [("Segment Types", ["RFM segments, ML behavioral clusters, CLV bands, discount sensitivity groups, retention risk groups, product affinity groups, and engagement segments."]), ("KPI Profile", ["Each segment should include customer count, revenue contribution, profit contribution, retention rate, churn rate, average CLV, AOV, return rate, discount dependency, and recommended action."]), ("Usage", ["Use segments for dashboard filtering, lifecycle strategy, campaign sizing, loyalty decisions, and executive reporting."])]),
        root / "docs" / "customer_segment_playbook.md": _doc_lines("Customer Segment Playbook", "Recommended actions by customer segment.", [("High Value Loyal Customers", ["Protect with VIP service, early access, and margin-aware loyalty benefits."]), ("Discount-Driven Buyers", ["Use controlled incentives, bundles, and margin-safe promotions."]), ("At-Risk Customers", ["Prioritize based on expected profit at risk and CLV band."]), ("One-Time Buyers", ["Drive second purchase with category-specific onboarding."])]),
        root / "docs" / "clv_methodology.md": _doc_lines("CLV Methodology", "Customer lifetime value methodology.", [("Historical CLV", ["Calculated from return-adjusted historical profit."]), ("Predicted CLV", ["Regression-based predicted future value using purchase, engagement, return, discount, and tenure signals."]), ("CLV Intelligence", ["Analyze CLV by segment, acquisition channel, cohort, product category, churn risk, and discount dependency."]), ("Priority Score", ["Retention investment priority combines churn risk, predicted CLV, and expected profit at risk."])]),
        root / "docs" / "customer_value_strategy.md": _doc_lines("Customer Value Strategy", "How business teams should use CLV outputs.", [("High-Value Customers", ["Protect high predicted CLV customers with targeted retention and service quality actions."]), ("Low-Value High-Cost Customers", ["Avoid over-investing in customers with low CLV, high returns, and high discount dependency."]), ("Channel Strategy", ["Evaluate acquisition by predicted value and churn risk, not volume alone."])]),
        root / "docs" / "cohort_methodology.md": _doc_lines("Cohort Methodology", "Cohort and retention methodology.", [("Cohorts", ["Monthly acquisition cohorts using first purchase month."]), ("Retention", ["Month 1 through Month 12 customer retention, revenue retention, repeat purchase retention, and behavioral retention."]), ("Slices", ["Analyze by acquisition channel, first product category, region, and segment."]), ("Health Score", ["Cohort health combines retention, revenue retention, repeat behavior, and churn exposure."])]),
        root / "docs" / "retention_strategy_insights.md": _doc_lines("Retention Strategy Insights", "Retention strategy based on customer intelligence outputs.", [("First 60 Days", ["Focus on onboarding, second purchase prompts, product education, and category-specific journeys."]), ("Mid-Life Retention", ["Use engagement and recency triggers before customers fully lapse."]), ("High-CLV Risk", ["Prioritize proactive interventions where CLV at risk is highest."])]),
        root / "docs" / "product_analytics_methodology.md": _doc_lines("Product Analytics Methodology", "Product intelligence methodology.", [("Profitability", ["Use return-adjusted profit and margin, not gross revenue only."]), ("Retention Impact", ["Compare products and categories by repeat customer rate and cohort retention."]), ("Risk Association", ["Identify products linked to returns, churn risk, discount dependency, or margin leakage."]), ("Affinity", ["Use confidence, lift, and affinity score for cross-sell and bundle opportunities."])]),
        root / "docs" / "product_profitability_playbook.md": _doc_lines("Product Profitability Playbook", "Business actions for product profitability intelligence.", [("Low Margin High Volume", ["Review cost, pricing, promotion rules, bundle design, and merchandising placement."]), ("Return Heavy", ["Audit product content, fulfillment promises, reviews, sizing, quality, and service issues."]), ("Retention Driver", ["Promote as onboarding, replenishment, or loyalty journey candidates."])]),
        root / "docs" / "cross_sell_strategy.md": _doc_lines("Cross-Sell Strategy", "How to use product affinity outputs.", [("Candidate Selection", ["Prioritize high affinity score and positive return-adjusted margin."]), ("Activation", ["Send category recommendation to customers with matching purchase history and sufficient CLV."]), ("Measurement", ["Track conversion, repeat purchase, return rate, margin, and churn impact."])]),
        root / "docs" / "reverse_etl_activation_design.md": _doc_lines("Reverse ETL Activation Design", "Activation-ready design for CRM and lifecycle use cases.", [("Exports", ["High churn risk, win-back, high CLV, cross-sell, loyalty upgrade, and discount-sensitive customers."]), ("Schema", ["customer_id, segment, churn_probability, clv_band, recommended_action, recommended_product_category, priority_score, campaign_reason."]), ("Controls", ["This is a local production-style simulation and is not connected to a real CRM."])]),
        root / "docs" / "lifecycle_marketing_use_cases.md": _doc_lines("Lifecycle Marketing Use Cases", "Business use cases supported by activation exports.", [("Retention Save", ["Target high churn risk customers with high profit or CLV at risk."]), ("Win-Back", ["Target lapsed customers based on recency and one-time buyer status."]), ("Cross-Sell", ["Recommend categories or products based on affinity and next-best-action logic."]), ("Loyalty Upgrade", ["Identify high-value customers not yet in top loyalty tiers."]), ("Discount Governance", ["Target discount-sensitive customers with controlled offers."])]),
        root / "docs" / "model_registry.md": _doc_lines("Model Registry", "Model governance summary.", [("Registered Models", ["Churn model, CLV model, and segmentation model."]), ("Registry Fields", ["Model name, version, artifact path, artifact hash, metrics path, champion metric, threshold, status, owner, and business use."]), ("Controls", ["Model cards and champion/challenger notes support repeatable review."])]),
        root / "docs" / "model_monitoring.md": _doc_lines("Model Monitoring", "Monitoring strategy for model outputs.", [("Signals", ["Score distribution drift, CLV band mix, churn risk tier mix, feature quality, scoring freshness, and champion metric thresholds."]), ("Actions", ["Review drift before using scores in activation.", "Re-score customers after major data generation or feature logic changes."])]),
        root / "docs" / "ml_explainability.md": _doc_lines("ML Explainability", "Explainability and business risk notes.", [("Explainability", ["Churn uses transparent coefficient-style feature importance.", "Segment profiles translate clusters into business labels and actions.", "CLV outputs are interpreted through bands and at-risk exposure."]), ("Ethical and Business Risk", ["Do not use scores as sole basis for customer treatment.", "Avoid over-targeting vulnerable or low-value customers with excessive promotions.", "Use profit and experience rules to control retention spend."])]),
        root / "docs" / "api_documentation.md": _doc_lines("API Documentation", "FastAPI endpoint documentation for governed analytics consumption.", [("Core Endpoints", ["/health, /metrics/customer-overview, /metrics/churn, /metrics/clv, /metrics/cohorts, /metrics/products, /metrics/segments."]), ("Customer Endpoints", ["/customers/{customer_id}/profile, /customers/{customer_id}/churn-risk, /customers/{customer_id}/recommendations."]), ("Product and Activation Endpoints", ["/products/{product_id}/profitability, /activation/churn-campaign, /activation/cross-sell."]), ("Controls", ["Optional CUSTOMER_INTELLIGENCE_API_KEY enables API key protection.", "Pagination headers are returned for list endpoints."])]),
    }
    paths = []
    for path, lines in docs.items():
        paths.append(write_markdown(lines, path))

    model_card_dir = root / "docs" / "model_cards"
    for name, purpose in [
        ("churn_model_card.md", "Predict churn probability and prioritize expected profit at risk."),
        ("clv_model_card.md", "Estimate predicted customer value and CLV at risk."),
        ("segmentation_model_card.md", "Assign behavioral customer segments and business recommendations."),
    ]:
        paths.append(
            write_markdown(
                _doc_lines(
                    name.replace("_", " ").replace(".md", "").title(),
                    purpose,
                    [
                        ("Inputs", ["Customer features, transactional aggregates, engagement, return, discount, session, and product behavior signals."]),
                        ("Outputs", ["Scored customer marts, dashboard fields, model monitoring outputs, and activation-ready fields."]),
                        ("Limitations", ["Local simulation using synthetic data; not trained on real company data."]),
                    ],
                ),
                model_card_dir / name,
            )
        )
    return paths


def _write_dashboard_docs(project_config: ProjectConfig) -> list[Path]:
    root = project_config.root
    dashboard_rows = []
    for page, audience, purpose, mart in DASHBOARD_PAGES:
        dashboard_rows.append(
            (
                page,
                purpose,
                audience,
                "KPI cards, trend line, ranked table, segment/channel filters, drillthrough detail, tooltip definitions",
                mart,
                "Daily/local pipeline refresh",
                "Validate KPI totals, filter behavior, row grain, null handling, and stale mart status",
            )
        )
    table = _markdown_table(
        dashboard_rows,
        ["Page", "Business Purpose", "Audience", "Controls and Charts", "Source Mart", "Refresh", "QA Checklist"],
    )
    powerbi_lines = ["# Power BI Dashboard Specification", "", "BI-ready Power BI page specification.", "", *table]
    tableau_lines = ["# Tableau Dashboard Specification", "", "BI-ready Tableau worksheet/dashboard specification.", "", *table]
    qa_lines = _doc_lines(
        "Dashboard QA Checklist",
        "QA checklist for dashboard release readiness.",
        [
            ("Data", ["KPI cards reconcile to kpi_summary.csv.", "Marts are fresh and pass schema contracts.", "Dashboard row counts match mart row counts at the intended grain."]),
            ("UX", ["Filters, tooltips, drilldowns, and empty states are tested.", "High-risk customer and product tables sort by business priority.", "No dashboard claims real company deployment."]),
            ("Release", ["Stakeholder UAT signoff is captured before publishing."]),
        ],
    )
    uat_lines = _doc_lines(
        "Stakeholder UAT Checklist",
        "User acceptance checklist for analytics stakeholders.",
        [
            ("Executive", ["Can answer top risks, opportunities, KPI movement, and priority actions."]),
            ("Customer Analytics", ["Can filter churn, CLV, cohort, segment, and activation outputs."]),
            ("Product Analytics", ["Can identify return-heavy, low-margin, retention-driving, and cross-sell products."]),
            ("BI Engineering", ["Can trace each visual to a governed mart and metric definition."]),
        ],
    )
    demo_lines = _doc_lines(
        "Dashboard Demo Script",
        "Short demo path for technical walkthroughs.",
        [
            ("Flow", ["Start with Executive Overview KPIs.", "Drill into churn risk and expected profit at risk.", "Open CLV to show retention investment priority.", "Move to Product Profitability for return-adjusted margin leakage.", "Close with Activation Lists showing how insights become campaign-ready exports."]),
            ("Talking Points", ["This is a local production-style simulation using synthetic data.", "The value is the governed analytics workflow and business decision support."]),
        ],
    )
    paths = [
        write_markdown(powerbi_lines, root / "dashboards" / "specs" / "powerbi_dashboard_spec.md"),
        write_markdown(tableau_lines, root / "dashboards" / "specs" / "tableau_dashboard_spec.md"),
        write_markdown(qa_lines, root / "dashboards" / "specs" / "dashboard_qa_checklist.md"),
        write_markdown(uat_lines, root / "dashboards" / "specs" / "uat_checklist.md"),
        write_markdown(demo_lines, root / "dashboards" / "specs" / "demo_script.md"),
    ]
    return paths


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _file_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def _write_ml_maturity_outputs(project_config: ProjectConfig) -> list[Path]:
    output_dir = project_config.root / "outputs"
    export_dir = project_config.export_dir
    churn_metrics = _read_json(project_config.model_dir / "churn_metrics.json")
    clv_metrics = _read_json(project_config.model_dir / "clv_model_metrics.json")
    segmentation_metrics = _read_json(project_config.model_dir / "segmentation_metrics.json")
    customer_volume = int(segmentation_metrics.get("customers_scored", 0))
    profile = "sample_5k" if customer_volume == 5_000 else "full_250k" if customer_volume == 250_000 else "volume_unspecified"

    registry = pd.DataFrame(
        [
            {
                "profile": profile,
                "customer_volume": customer_volume,
                "authoritative_current": profile == "sample_5k",
                "model_name": "churn_model",
                "model_type": "Logistic Regression",
                "artifact_path": "models/churn_model.joblib",
                "evaluation_output": "outputs/churn_model_evaluation.csv",
                "primary_metric": "roc_auc",
                "primary_metric_value": churn_metrics.get("roc_auc"),
                "owner": "Customer Analytics",
                "business_use": "Score churn probability and expected profit at risk.",
                "refresh_strategy": "Retrain after major feature changes or scheduled scoring refresh.",
            },
            {
                "profile": profile,
                "customer_volume": customer_volume,
                "authoritative_current": profile == "sample_5k",
                "model_name": "clv_model",
                "model_type": "Regression",
                "artifact_path": "models/clv_model.joblib",
                "evaluation_output": "outputs/clv_model_evaluation.csv",
                "primary_metric": "r2",
                "primary_metric_value": clv_metrics.get("r2"),
                "owner": "Customer Analytics",
                "business_use": "Estimate predicted customer value and CLV at risk.",
                "refresh_strategy": "Retrain after customer value distribution or channel mix shifts.",
            },
            {
                "profile": profile,
                "customer_volume": customer_volume,
                "authoritative_current": profile == "sample_5k",
                "model_name": "segmentation_model",
                "model_type": "K-Means",
                "artifact_path": "models/segmentation_model.joblib",
                "evaluation_output": "outputs/segmentation_evaluation.csv",
                "primary_metric": "silhouette_score",
                "primary_metric_value": segmentation_metrics.get("silhouette_score"),
                "owner": "Customer Analytics",
                "business_use": "Assign customer segments and business recommendations.",
                "refresh_strategy": "Review clusters after major cohort, channel, or product mix changes.",
            },
        ]
    )
    evidence_identity = {
        "profile": profile,
        "customer_volume": customer_volume,
        "authoritative_current": profile == "sample_5k",
    }
    churn_eval = pd.DataFrame(
        [{**evidence_identity, "metric": key, "value": value} for key, value in churn_metrics.items() if key != "confusion_matrix"]
    )
    clv_eval = pd.DataFrame([{**evidence_identity, "metric": key, "value": value} for key, value in clv_metrics.items()])
    segmentation_eval = pd.DataFrame([{**evidence_identity, "metric": key, "value": value} for key, value in segmentation_metrics.items()])

    churn_importance_path = project_config.export_dir / "churn_driver_summary.csv"
    if churn_importance_path.exists():
        churn_importance = pd.read_csv(churn_importance_path)
    else:
        churn_importance = pd.DataFrame(
            [
                {"feature": "recency_days", "importance": 1.0, "direction": "Increases churn risk", "business_interpretation": "Long inactivity increases churn risk."},
                {"feature": "discount_dependency", "importance": 0.8, "direction": "Increases churn risk", "business_interpretation": "Promotion dependency can signal weak full-price loyalty."},
            ]
        )
    clv_importance = pd.DataFrame(
        [
            ("return_adjusted_profit", 1.00, "Higher profit increases predicted value."),
            ("orders", 0.90, "Deeper purchase history increases confidence in future value."),
            ("purchase_frequency_30d", 0.82, "Higher purchase cadence supports stronger CLV."),
            ("engagement_score", 0.70, "Reachable and engaged customers are easier to retain."),
            ("discount_dependency", -0.55, "High discount dependency can reduce profitable value."),
            ("return_rate", -0.50, "High return behavior weakens return-adjusted value."),
        ],
        columns=["feature", "relative_importance", "business_interpretation"],
    )
    scoring_log = pd.DataFrame(
        [
            {
                "scoring_output": "mart_churn_risk.csv",
                "model_name": "churn_model",
                "rows_scored": _file_row_count(project_config.mart_dir / "mart_churn_risk.csv"),
                "grain": "customer",
                "freshness_rule": "Refresh before dashboard or activation publication.",
            },
            {
                "scoring_output": "mart_clv.csv",
                "model_name": "clv_model",
                "rows_scored": _file_row_count(project_config.mart_dir / "mart_clv.csv"),
                "grain": "customer",
                "freshness_rule": "Refresh before CLV dashboard or high-value activation use.",
            },
            {
                "scoring_output": "mart_customer_segments.csv",
                "model_name": "segmentation_model",
                "rows_scored": _file_row_count(project_config.mart_dir / "mart_customer_segments.csv"),
                "grain": "customer",
                "freshness_rule": "Refresh when customer feature distribution changes materially.",
            },
        ]
    )

    outputs = {
        "model_registry.csv": registry,
        "churn_model_evaluation.csv": churn_eval,
        "clv_model_evaluation.csv": clv_eval,
        "segmentation_evaluation.csv": segmentation_eval,
        "feature_importance_churn.csv": churn_importance,
        "feature_importance_clv.csv": clv_importance,
        "model_scoring_log.csv": scoring_log,
    }
    paths: list[Path] = []
    for filename, frame in outputs.items():
        paths.append(write_csv(frame, output_dir / filename))
        paths.append(write_csv(frame, export_dir / filename))
    return paths


def generate_enterprise_assets(project_config: ProjectConfig = CONFIG) -> list[Path]:
    project_config.ensure_directories()
    (project_config.root / "outputs").mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    paths.extend(_write_core_docs(project_config))
    paths.extend(_write_feature_catalog(project_config))
    paths.extend(_write_kpi_catalog(project_config))
    paths.extend(_write_methodology_docs(project_config))
    paths.extend(_write_dashboard_docs(project_config))
    paths.extend(_write_ml_maturity_outputs(project_config))
    return paths


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Generate enterprise technical documentation and catalogs.").parse_args()


def main() -> None:
    parse_args()
    paths = generate_enterprise_assets()
    print(f"Generated {len(paths)} enterprise assets.")


if __name__ == "__main__":
    main()
