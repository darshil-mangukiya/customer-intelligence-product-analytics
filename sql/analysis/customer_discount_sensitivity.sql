/*
Business question:
Which customers rely on discounts, and does that behavior reduce margin or increase churn risk?

Source marts/tables:
- marts.dim_customer
- marts.fact_orders
- marts.fact_customer_value

Output:
Customer-level discount sensitivity scoring with segment, margin, churn label,
and recommended lifecycle action.
*/

WITH customer_discount AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT o.order_id) AS completed_orders,
        SUM(o.net_revenue) AS net_revenue,
        SUM(o.discount_amount) AS discount_amount,
        SUM(o.return_adjusted_profit) AS return_adjusted_profit,
        AVG(CASE WHEN o.discount_amount > 0 THEN 1 ELSE 0 END)::NUMERIC AS discounted_order_rate,
        MAX(o.order_date) AS last_order_date
    FROM marts.fact_orders o
    WHERE o.is_completed_order = TRUE
    GROUP BY o.customer_id
),
scored AS (
    SELECT
        c.customer_id,
        c.acquisition_channel,
        c.loyalty_tier,
        c.preferred_category,
        COALESCE(cd.completed_orders, 0) AS completed_orders,
        COALESCE(cd.net_revenue, 0) AS net_revenue,
        COALESCE(cd.discount_amount, 0) AS discount_amount,
        COALESCE(cd.return_adjusted_profit, 0) AS return_adjusted_profit,
        COALESCE(cd.discounted_order_rate, 0) AS discounted_order_rate,
        COALESCE(cv.recency_days, 999) AS recency_days,
        COALESCE(cv.repeat_purchase_flag, 0) AS repeat_purchase_flag,
        COALESCE(cv.churn_label, 0) AS churn_label,
        ROUND(COALESCE(cd.discount_amount, 0) / NULLIF(COALESCE(cd.net_revenue, 0) + COALESCE(cd.discount_amount, 0), 0), 4) AS discount_dependency_rate
    FROM marts.dim_customer c
    LEFT JOIN customer_discount cd
        ON c.customer_id = cd.customer_id
    LEFT JOIN marts.fact_customer_value cv
        ON c.customer_id = cv.customer_id
),
ranked AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY discount_dependency_rate) AS discount_sensitivity_quintile,
        RANK() OVER (ORDER BY discount_amount DESC) AS discount_dollar_rank
    FROM scored
)
SELECT
    customer_id,
    acquisition_channel,
    loyalty_tier,
    preferred_category,
    completed_orders,
    net_revenue,
    discount_amount,
    return_adjusted_profit,
    ROUND(return_adjusted_profit / NULLIF(net_revenue, 0), 4) AS return_adjusted_margin,
    discounted_order_rate,
    discount_dependency_rate,
    discount_sensitivity_quintile,
    discount_dollar_rank,
    recency_days,
    repeat_purchase_flag,
    churn_label,
    CASE
        WHEN discount_sensitivity_quintile = 5 AND return_adjusted_profit <= 0 THEN 'High discount low value'
        WHEN discount_sensitivity_quintile = 5 AND churn_label = 1 THEN 'Discount-sensitive churn risk'
        WHEN discount_sensitivity_quintile >= 4 THEN 'Discount-sensitive'
        WHEN discount_sensitivity_quintile <= 2 AND net_revenue > 0 THEN 'Low discount dependency'
        ELSE 'Moderate discount dependency'
    END AS discount_segment,
    CASE
        WHEN discount_sensitivity_quintile = 5 AND return_adjusted_profit <= 0 THEN 'Reduce blanket discounts and test margin guardrails'
        WHEN discount_sensitivity_quintile = 5 AND churn_label = 1 THEN 'Use targeted win-back with profit floor'
        WHEN discount_sensitivity_quintile >= 4 THEN 'Offer personalized bundles instead of broad discounts'
        ELSE 'Use standard lifecycle offers'
    END AS recommended_action
FROM ranked
ORDER BY discount_dollar_rank;
