# Source-to-Target Mapping

This mapping summarizes how source-like tables flow into warehouse and BI outputs.

| Source | Staged Target | Final Target | Key | Transformation Rule |
|---|---|---|---|---|
| raw.customers | customers_clean | dim_customer, customer_features | customer_id | Standardize demographics, acquisition channel, loyalty tier, churn status. |
| raw.transactions | transactions_clean | fact_orders, fact_returns | order_id | Normalize revenue, cost, discounts, status, return flags, dates, and product/customer keys. |
| raw.products | products_clean | dim_product, mart_product_profitability | product_id | Standardize catalog, category, lifecycle, margin, return, and retention profiles. |
| raw.web_behavior | web_behavior_clean | fact_sessions, customer_engagement_features | session_id | Normalize sessions, devices, source labels, page views, time spent, and bounce flags. |
| raw.engagement | engagement_clean | fact_engagement, customer_engagement_features | customer_id | Calculate engagement score and campaign responsiveness. |
| processed.customer_features | feature tables | mart_churn_risk, mart_clv, mart_customer_segments | customer_id | Aggregate behavior, monetary, engagement, return, discount, and retention features. |
