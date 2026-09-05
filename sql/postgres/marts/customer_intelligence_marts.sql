CREATE OR REPLACE VIEW marts.mart_customer_overview AS
SELECT
    c.customer_id,
    c.acquisition_channel,
    c.loyalty_tier,
    c.segment_seed,
    c.preferred_category,
    cv.orders,
    cv.net_revenue,
    cv.return_adjusted_profit,
    cv.historical_clv,
    cv.customer_value_band,
    cv.recency_days,
    cv.purchase_frequency_30d,
    cv.repeat_purchase_flag,
    cv.churn_label
FROM marts.dim_customer c
LEFT JOIN marts.fact_customer_value cv
    ON c.customer_id = cv.customer_id;

CREATE OR REPLACE VIEW marts.mart_product_profitability AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.lifecycle_stage,
    COUNT(DISTINCT o.order_id) AS orders,
    SUM(o.quantity) AS units,
    COUNT(DISTINCT o.customer_id) AS customers,
    SUM(o.net_revenue) AS net_revenue,
    SUM(o.return_adjusted_profit) AS return_adjusted_profit,
    SUM(o.discount_amount) AS discount_amount,
    SUM(CASE WHEN o.return_flag THEN 1 ELSE 0 END)::NUMERIC / NULLIF(COUNT(DISTINCT o.order_id), 0) AS return_rate,
    SUM(o.return_adjusted_profit) / NULLIF(SUM(o.net_revenue), 0) AS return_adjusted_margin
FROM marts.dim_product p
LEFT JOIN marts.fact_orders o
    ON p.product_id = o.product_id
GROUP BY
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.lifecycle_stage;

CREATE OR REPLACE VIEW marts.mart_churn_risk_base AS
SELECT
    c.customer_id,
    c.acquisition_channel,
    c.loyalty_tier,
    c.segment_seed,
    cv.orders,
    cv.net_revenue,
    cv.return_adjusted_profit,
    cv.recency_days,
    cv.purchase_frequency_30d,
    cv.churn_label
FROM marts.dim_customer c
JOIN marts.fact_customer_value cv
    ON c.customer_id = cv.customer_id;

CREATE OR REPLACE VIEW marts.mart_category_profitability AS
SELECT
    p.category,
    COUNT(DISTINCT o.order_id) AS orders,
    COUNT(DISTINCT o.customer_id) AS customers,
    SUM(o.net_revenue) AS net_revenue,
    SUM(o.return_adjusted_profit) AS return_adjusted_profit,
    SUM(o.discount_amount) AS discount_amount,
    SUM(CASE WHEN o.return_flag THEN 1 ELSE 0 END)::NUMERIC / NULLIF(COUNT(DISTINCT o.order_id), 0) AS return_rate,
    SUM(o.return_adjusted_profit) / NULLIF(SUM(o.net_revenue), 0) AS return_adjusted_margin
FROM marts.fact_orders o
JOIN marts.dim_product p
    ON o.product_id = p.product_id
GROUP BY p.category;

CREATE OR REPLACE VIEW marts.mart_executive_kpis AS
SELECT
    SUM(net_revenue) AS total_net_revenue,
    SUM(return_adjusted_profit) AS total_return_adjusted_profit,
    SUM(return_loss + discount_amount) AS revenue_leakage,
    SUM(return_adjusted_profit) / NULLIF(SUM(net_revenue), 0) AS return_adjusted_margin,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_id) AS purchasing_customers
FROM marts.fact_orders;

