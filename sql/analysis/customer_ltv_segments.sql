/*
Business question:
Which customers create the most value, and how should value bands be prioritized for retention or growth?

Source marts/tables:
- marts.dim_customer
- marts.fact_customer_value
- marts.fact_orders

Output:
Customer-level value bands with historical CLV, revenue, profit, order behavior,
channel context, and ranking fields for dashboard drill-throughs.
*/

WITH customer_orders AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT o.order_id) AS completed_orders,
        SUM(o.net_revenue) AS net_revenue,
        SUM(o.return_adjusted_profit) AS return_adjusted_profit,
        SUM(o.discount_amount) AS discount_amount,
        SUM(o.return_loss) AS return_loss,
        MAX(o.order_date) AS last_order_date
    FROM marts.fact_orders o
    WHERE o.is_completed_order = TRUE
    GROUP BY o.customer_id
),
customer_base AS (
    SELECT
        c.customer_id,
        c.acquisition_channel,
        c.loyalty_tier,
        c.preferred_category,
        COALESCE(co.completed_orders, cv.orders, 0) AS completed_orders,
        COALESCE(co.net_revenue, cv.net_revenue, 0) AS net_revenue,
        COALESCE(co.return_adjusted_profit, cv.return_adjusted_profit, 0) AS return_adjusted_profit,
        COALESCE(cv.historical_clv, co.return_adjusted_profit, 0) AS historical_clv,
        cv.recency_days,
        cv.purchase_frequency_30d,
        cv.repeat_purchase_flag,
        cv.churn_label,
        COALESCE(co.discount_amount, 0) AS discount_amount,
        COALESCE(co.return_loss, 0) AS return_loss,
        co.last_order_date
    FROM marts.dim_customer c
    LEFT JOIN marts.fact_customer_value cv
        ON c.customer_id = cv.customer_id
    LEFT JOIN customer_orders co
        ON c.customer_id = co.customer_id
),
ranked AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY historical_clv) AS clv_quintile,
        PERCENT_RANK() OVER (ORDER BY historical_clv) AS clv_percentile,
        RANK() OVER (ORDER BY historical_clv DESC) AS customer_value_rank
    FROM customer_base
)
SELECT
    customer_id,
    acquisition_channel,
    loyalty_tier,
    preferred_category,
    completed_orders,
    net_revenue,
    return_adjusted_profit,
    historical_clv,
    ROUND(return_adjusted_profit / NULLIF(net_revenue, 0), 4) AS value_margin_rate,
    ROUND(discount_amount / NULLIF(net_revenue + discount_amount, 0), 4) AS discount_dependency_rate,
    ROUND(return_loss / NULLIF(net_revenue + return_loss, 0), 4) AS return_leakage_rate,
    recency_days,
    purchase_frequency_30d,
    repeat_purchase_flag,
    churn_label,
    clv_quintile,
    ROUND(clv_percentile::NUMERIC, 4) AS clv_percentile,
    customer_value_rank,
    CASE
        WHEN clv_quintile = 5 AND churn_label = 1 THEN 'High Value At Risk'
        WHEN clv_quintile = 5 THEN 'Top Value'
        WHEN clv_quintile >= 4 AND repeat_purchase_flag = 1 THEN 'Growth Value'
        WHEN clv_quintile <= 2 AND completed_orders <= 1 THEN 'Low Value One-Time'
        ELSE 'Core Value'
    END AS value_segment,
    CASE
        WHEN clv_quintile = 5 AND churn_label = 1 THEN 'Prioritize retention outreach'
        WHEN clv_quintile = 5 THEN 'Protect with loyalty benefits'
        WHEN clv_quintile >= 4 THEN 'Use cross-sell and category expansion'
        WHEN completed_orders <= 1 THEN 'Trigger second-purchase journey'
        ELSE 'Maintain lifecycle nurture'
    END AS recommended_action
FROM ranked
ORDER BY customer_value_rank;
