/*
Business question:
Which products are the strongest return-adjusted profit contributors, and are any dependent on high discounts?

Source marts/tables:
- marts.mart_product_profitability

Output:
Ranked product profitability list with category share, profit concentration,
and discount/return warning flags for BI product dashboards.
*/

WITH product_base AS (
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
        discount_amount,
        return_rate,
        return_adjusted_margin
    FROM marts.mart_product_profitability
    WHERE net_revenue > 0
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY return_adjusted_profit DESC) AS overall_profit_rank,
        RANK() OVER (PARTITION BY category ORDER BY return_adjusted_profit DESC) AS category_profit_rank,
        SUM(return_adjusted_profit) OVER () AS total_profit,
        SUM(return_adjusted_profit) OVER (PARTITION BY category) AS category_profit,
        AVG(return_adjusted_margin) OVER (PARTITION BY category) AS category_avg_margin
    FROM product_base
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
    ROUND(return_adjusted_profit / NULLIF(total_profit, 0), 4) AS total_profit_contribution_pct,
    ROUND(return_adjusted_profit / NULLIF(category_profit, 0), 4) AS category_profit_contribution_pct,
    return_adjusted_margin,
    ROUND(return_adjusted_margin - category_avg_margin, 4) AS margin_vs_category_avg,
    ROUND(discount_amount / NULLIF(net_revenue + discount_amount, 0), 4) AS discount_dependency_rate,
    return_rate,
    overall_profit_rank,
    category_profit_rank,
    CASE
        WHEN overall_profit_rank <= 25 AND return_rate < 0.10 THEN 'Scale winner'
        WHEN overall_profit_rank <= 25 AND return_rate >= 0.10 THEN 'High profit with return exposure'
        WHEN return_adjusted_margin < category_avg_margin THEN 'Margin below category'
        ELSE 'Monitor'
    END AS product_strategy_flag
FROM ranked
ORDER BY overall_profit_rank
LIMIT 250;
