# Data Contracts

Data contracts define required columns, grains, freshness expectations, and blocking rules.

## Critical Contracts

- fact_orders must have unique order_id, valid customer_id/product_id, nonnegative net_revenue, and accepted order_status.
- mart_churn_risk must have one row per customer_id, churn_probability between 0 and 1, and accepted risk tiers.
- mart_clv must have one row per customer_id and non-null CLV band for scored customers.
- mart_product_profitability must have one row per product_id and return_rate between 0 and 1.
- kpi_summary must reconcile total net revenue to fact_orders.

## Severity Rules

- P1 failures block executive dashboard refresh.
- P2 failures require data-steward review before publication.
- P3 failures can publish with a release note if business impact is low.

## Freshness

- Daily marts should refresh within 24 hours in a real warehouse.
- Local simulation treats mart outputs older than 14 days as stale for validation examples.
