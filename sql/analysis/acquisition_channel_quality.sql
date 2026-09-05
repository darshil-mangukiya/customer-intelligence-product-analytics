/*
Business question:
Which acquisition channels produce durable customer value rather than only short-term order volume?

Source marts/tables:
- marts.dim_customer
- marts.fact_customer_value
- marts.fact_orders

Output:
Channel scorecard comparing revenue, profit, repeat behavior, churn, discount dependency,
and value ranking for acquisition budget decisions.
*/

WITH customer_channel AS (
    SELECT
        c.customer_id,
        COALESCE(c.acquisition_channel, 'Unknown') AS acquisition_channel,
        c.signup_date,
        COALESCE(cv.orders, 0) AS orders,
        COALESCE(cv.net_revenue, 0) AS net_revenue,
        COALESCE(cv.return_adjusted_profit, 0) AS return_adjusted_profit,
        COALESCE(cv.historical_clv, cv.return_adjusted_profit, 0) AS historical_clv,
        COALESCE(cv.repeat_purchase_flag, 0) AS repeat_purchase_flag,
        COALESCE(cv.churn_label, 0) AS churn_label
    FROM marts.dim_customer c
    LEFT JOIN marts.fact_customer_value cv
        ON c.customer_id = cv.customer_id
),
channel_discounts AS (
    SELECT
        c.acquisition_channel,
        SUM(o.discount_amount) AS discount_amount,
        SUM(o.net_revenue) AS net_revenue_from_orders,
        SUM(o.return_loss) AS return_loss,
        COUNT(DISTINCT o.order_id) AS completed_orders
    FROM marts.fact_orders o
    JOIN marts.dim_customer c
        ON o.customer_id = c.customer_id
    WHERE o.is_completed_order = TRUE
    GROUP BY c.acquisition_channel
),
channel_summary AS (
    SELECT
        cc.acquisition_channel,
        COUNT(DISTINCT cc.customer_id) AS acquired_customers,
        SUM(cc.orders) AS customer_orders,
        SUM(cc.net_revenue) AS net_revenue,
        SUM(cc.return_adjusted_profit) AS return_adjusted_profit,
        AVG(cc.historical_clv) AS avg_historical_clv,
        AVG(cc.repeat_purchase_flag)::NUMERIC AS repeat_purchase_rate,
        AVG(cc.churn_label)::NUMERIC AS churn_rate,
        COALESCE(cd.discount_amount, 0) AS discount_amount,
        COALESCE(cd.return_loss, 0) AS return_loss
    FROM customer_channel cc
    LEFT JOIN channel_discounts cd
        ON cc.acquisition_channel = cd.acquisition_channel
    GROUP BY cc.acquisition_channel, cd.discount_amount, cd.return_loss
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY return_adjusted_profit DESC) AS profit_rank,
        RANK() OVER (ORDER BY avg_historical_clv DESC) AS clv_rank,
        RANK() OVER (ORDER BY churn_rate ASC) AS retention_quality_rank
    FROM channel_summary
)
SELECT
    acquisition_channel,
    acquired_customers,
    customer_orders,
    net_revenue,
    return_adjusted_profit,
    ROUND(return_adjusted_profit / NULLIF(net_revenue, 0), 4) AS return_adjusted_margin,
    ROUND(avg_historical_clv::NUMERIC, 2) AS avg_historical_clv,
    ROUND(repeat_purchase_rate, 4) AS repeat_purchase_rate,
    ROUND(churn_rate, 4) AS churn_rate,
    ROUND(discount_amount / NULLIF(net_revenue + discount_amount, 0), 4) AS discount_dependency_rate,
    ROUND(return_loss / NULLIF(net_revenue + return_loss, 0), 4) AS return_leakage_rate,
    profit_rank,
    clv_rank,
    retention_quality_rank,
    CASE
        WHEN clv_rank <= 3 AND retention_quality_rank <= 3 THEN 'Scale quality channel'
        WHEN profit_rank <= 3 AND churn_rate > 0.30 THEN 'Profitable but retention risk'
        WHEN discount_amount / NULLIF(net_revenue + discount_amount, 0) > 0.20 THEN 'Promotion-dependent channel'
        ELSE 'Monitor channel'
    END AS channel_decision_flag
FROM ranked
ORDER BY clv_rank, retention_quality_rank;
