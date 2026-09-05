# Warehouse Performance Optimization

Performance notes describe how this local production simulation would scale in a warehouse.

## Incremental Strategy

- Load orders incrementally by order_date and order_id watermark.
- Refresh customer-level features for customers with changed orders, sessions, engagement, support, or scoring updates.
- Rebuild cohort and product affinity outputs on a scheduled batch cadence.

## Partitioning

- Partition fact_orders and fact_sessions by date_key or order/session month.
- Partition large activation exports by campaign run date.
- Cluster customer marts by customer_id and churn_risk_tier for targeted retrieval.

## Indexing

- Index fact_orders(order_id), fact_orders(customer_id), fact_orders(product_id), fact_orders(date_key).
- Index mart_churn_risk(customer_id, churn_risk_tier), mart_clv(customer_id, clv_band), mart_customer_segments(segment_name).
- Index mart_product_profitability(product_id, category).

## Query Tuning

- Use mart tables for dashboard queries instead of recomputing joins.
- Use semantic KPI logic for reusable definitions.
- Pre-aggregate cohort, segment, and product dashboard views by expected filter grain.
