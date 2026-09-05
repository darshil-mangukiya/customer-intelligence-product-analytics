# Source and Mart Data Contracts

| Table | Owner | Grain | Unique Key | Minimum Rows | Required Columns |
|---|---|---|---|---:|---|
| fact_orders | BI Engineering | one row per order | order_id | 100,000 | order_id, customer_id, product_id, order_date, net_revenue, return_adjusted_profit, is_completed_order |
| mart_churn_risk | Customer Analytics | one row per customer | customer_id | 100,000 | customer_id, churn_probability, churn_risk_tier, expected_profit_at_risk |
| mart_clv | Customer Analytics | one row per customer | customer_id | 100,000 | customer_id, predicted_12m_clv, clv_band, expected_clv_at_risk |
| mart_product_profitability | Product Analytics | one row per product | product_id | 1,000 | product_id, category, net_revenue, return_adjusted_profit, return_rate, return_adjusted_margin |
| kpi_summary | BI Engineering | one row per governed KPI | kpi_name | 10 | kpi_name, value, display_format, grain, owner, threshold |
| next_best_actions | Lifecycle Marketing | one row per customer action recommendation | customer_id | 100,000 | customer_id, recommended_action, action_priority_score, owner_team, success_metric |
