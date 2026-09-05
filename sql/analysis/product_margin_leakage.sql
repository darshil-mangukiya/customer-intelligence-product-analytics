/*
Business question:
Which products leak the most margin through returns and discounting?

Source marts/tables:
- marts.mart_product_profitability
- marts.fact_orders

Output:
Product-level leakage view showing discount leakage, return leakage, margin impact,
and operational flags for merchandising and finance review.
*/

WITH order_leakage AS (
    SELECT
        product_id,
        SUM(net_revenue) AS net_revenue,
        SUM(return_adjusted_profit) AS return_adjusted_profit,
        SUM(discount_amount) AS discount_leakage,
        SUM(return_loss) AS return_leakage,
        SUM(discount_amount + return_loss) AS total_revenue_leakage,
        COUNT(DISTINCT order_id) AS completed_orders,
        SUM(CASE WHEN return_flag THEN 1 ELSE 0 END) AS returned_orders
    FROM marts.fact_orders
    WHERE is_completed_order = TRUE
    GROUP BY product_id
),
product_scored AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.sub_category,
        p.lifecycle_stage,
        p.orders,
        p.units,
        p.customers,
        COALESCE(ol.net_revenue, p.net_revenue) AS net_revenue,
        COALESCE(ol.return_adjusted_profit, p.return_adjusted_profit) AS return_adjusted_profit,
        COALESCE(ol.discount_leakage, p.discount_amount) AS discount_leakage,
        COALESCE(ol.return_leakage, 0) AS return_leakage,
        COALESCE(ol.total_revenue_leakage, p.discount_amount) AS total_revenue_leakage,
        COALESCE(ol.returned_orders::NUMERIC / NULLIF(ol.completed_orders, 0), p.return_rate) AS return_rate,
        p.return_adjusted_margin
    FROM marts.mart_product_profitability p
    LEFT JOIN order_leakage ol
        ON p.product_id = ol.product_id
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY total_revenue_leakage DESC) AS leakage_rank,
        RANK() OVER (PARTITION BY category ORDER BY total_revenue_leakage DESC) AS category_leakage_rank,
        NTILE(4) OVER (ORDER BY return_adjusted_margin) AS margin_quartile
    FROM product_scored
)
SELECT
    product_id,
    product_name,
    category,
    sub_category,
    lifecycle_stage,
    orders,
    units,
    customers,
    net_revenue,
    return_adjusted_profit,
    return_adjusted_margin,
    discount_leakage,
    return_leakage,
    total_revenue_leakage,
    ROUND(total_revenue_leakage / NULLIF(net_revenue + total_revenue_leakage, 0), 4) AS leakage_rate,
    return_rate,
    leakage_rank,
    category_leakage_rank,
    CASE
        WHEN margin_quartile = 1 AND total_revenue_leakage > 0 THEN 'Margin leakage review'
        WHEN return_rate >= 0.15 THEN 'Returns investigation'
        WHEN discount_leakage > return_leakage THEN 'Discount governance review'
        ELSE 'Stable'
    END AS leakage_action_flag
FROM ranked
ORDER BY leakage_rank;
