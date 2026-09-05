# Data Dictionary

Important fields used across source data, features, marts, model outputs, and activation exports.

| Field Name | Table | Type | Description | Grain | Example Value | Quality Rule |
|---|---|---|---|---|---|---|
| customer_id | customers / customer marts | string | Unique customer identifier. | customer | C000123 | Not null and unique in dim_customer. |
| order_id | transactions / fact_orders | string | Unique order identifier. | order | O000456 | Not null and unique in fact_orders. |
| product_id | products / product marts | string | Unique product identifier. | product | P001 | Must exist in dim_product for order facts. |
| order_date | transactions | date | Date of customer order. | order | 2025-11-18 | Cannot be impossible or outside generated date range. |
| net_revenue | fact_orders | float | Revenue after discounts/status adjustments. | order | 129.99 | Must be nonnegative. |
| return_adjusted_profit | fact_orders / marts | float | Profit after return impact. | order/customer/product | 42.50 | Monitor negative anomalies. |
| discount_dependency | customer/product features | float | Share of value tied to discounts. | customer/product | 0.34 | Between 0 and 1. |
| return_rate | customer/product features | float | Returned orders divided by orders. | customer/product | 0.12 | Between 0 and 1. |
| churn_probability | mart_churn_risk | float | Modeled probability of churn. | customer | 0.82 | Between 0 and 1. |
| churn_risk_tier | mart_churn_risk | string | Business tier based on churn probability. | customer | High | Accepted values: Low, Medium, High, Critical. |
| predicted_12m_clv | mart_clv | float | Estimated 12-month customer value. | customer | 1430.25 | Numeric and monitored by distribution. |
| clv_band | mart_clv | string | Business value band. | customer | Platinum | Not null for scored customers. |
| cohort_month | mart_cohort_retention | string | Customer acquisition cohort month. | cohort month | 2025-03 | Valid month format. |
| cohort_index | mart_cohort_retention | integer | Months since cohort month. | cohort month | 3 | Between 0 and 12 for dashboard retention. |
| retention_rate | mart_cohort_retention | float | Customers retained divided by cohort size. | cohort month | 0.24 | Between 0 and 1. |
| affinity_score | mart_product_affinity | float | Cross-sell strength using confidence and lift. | product/category pair | 0.69 | Nonnegative. |
| priority_score | activation exports | float | Campaign priority score. | customer | 98.5 | Between 0 and 100 in activation samples. |
| recommended_action | activation exports | string | Suggested lifecycle action. | customer | Retention save journey | Not null in activation exports. |
