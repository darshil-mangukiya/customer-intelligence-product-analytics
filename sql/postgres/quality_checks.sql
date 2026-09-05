SELECT 'fact_orders_without_customer' AS check_name, COUNT(*) AS failing_rows
FROM marts.fact_orders o
LEFT JOIN marts.dim_customer c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL
UNION ALL
SELECT 'fact_orders_without_product' AS check_name, COUNT(*) AS failing_rows
FROM marts.fact_orders o
LEFT JOIN marts.dim_product p ON o.product_id = p.product_id
WHERE p.product_id IS NULL
UNION ALL
SELECT 'negative_net_revenue_completed_orders' AS check_name, COUNT(*) AS failing_rows
FROM marts.fact_orders
WHERE is_completed_order = TRUE AND net_revenue < 0
UNION ALL
SELECT 'cohort_retention_over_100_percent' AS check_name, COUNT(*) AS failing_rows
FROM marts.fact_cohort_retention
WHERE retention_rate > 1.0;

