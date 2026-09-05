# Data Lineage

Lineage documents how each analytical output is derived from raw source-like data.

## Customer Lineage

- raw.customers -> customers_clean -> customer_features -> mart_customer_overview, mart_customer_segments, mart_clv, mart_churn_risk

## Order Lineage

- raw.transactions -> transactions_clean -> transactions_enriched -> fact_orders, fact_returns, fact_customer_value, product profitability marts

## Session and Engagement Lineage

- raw.web_behavior and raw.engagement -> cleaned facts -> engagement, churn, retention, and lifecycle features

## Product Lineage

- raw.products + enriched transactions -> product_features -> mart_product_profitability, affinity outputs, cross-sell recommendations

## Cohort Lineage

- transactions_enriched + customer first order date -> cohort_base -> mart_cohort_retention and cohort dashboard exports

## Model Lineage

- feature bases -> churn, segmentation, and CLV models -> scored marts -> dashboard, API, and activation outputs
