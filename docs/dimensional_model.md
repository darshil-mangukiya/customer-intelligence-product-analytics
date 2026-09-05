# Dimensional Model and Star Schema Notes

This warehouse-ready design supports BI tools with clear grains, keys, and relationship rules.

## Dimensions

- dim_customer grain: one row per customer_id.
- dim_product grain: one row per product_id.
- dim_date grain: one row per calendar date.
- dim_channel grain: one row per channel label.
- dim_region grain: one row per region/city combination.
- dim_device grain: one row per device type.

## Facts

- fact_orders grain: one row per order_id.
- fact_sessions grain: one row per session_id.
- fact_engagement grain: one row per customer engagement snapshot.
- fact_returns grain: one row per returned or cancelled order.
- fact_customer_value grain: one row per customer value snapshot.
- fact_cohort_retention grain: one row per cohort_month and cohort_index.

## Primary Keys

- dim_customer.customer_id, dim_product.product_id, dim_date.date_key, fact_orders.order_id, fact_sessions.session_id.
- Marts use customer_id, product_id, cohort_month/cohort_index, or source/target category depending on grain.

## Foreign Keys

- fact_orders.customer_id -> dim_customer.customer_id.
- fact_orders.product_id -> dim_product.product_id.
- fact_orders.date_key -> dim_date.date_key.
- fact_sessions.customer_id -> dim_customer.customer_id.
- fact_engagement.customer_id -> dim_customer.customer_id.

## Star Schema Notes

- Power BI and Tableau should use fact tables as event sources and marts as curated analytical outputs.
- Avoid many-to-many ambiguity by using dimension keys and dashboard-specific marts for advanced outputs.
