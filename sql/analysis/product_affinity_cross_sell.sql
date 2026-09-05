/*
Business question:
Which product categories are commonly purchased by the same customers and can support cross-sell recommendations?

Source marts/tables:
- marts.fact_orders
- marts.dim_product

Output:
Category-to-category affinity pairs with support, confidence, lift, and ranked cross-sell
recommendations. This uses customer-level co-purchase behavior and is intended as a
transparent analyst version of the product affinity mart.
*/

WITH customer_category AS (
    SELECT DISTINCT
        o.customer_id,
        p.category
    FROM marts.fact_orders o
    JOIN marts.dim_product p
        ON o.product_id = p.product_id
    WHERE o.is_completed_order = TRUE
      AND p.category IS NOT NULL
),
category_counts AS (
    SELECT
        category,
        COUNT(DISTINCT customer_id) AS category_customers
    FROM customer_category
    GROUP BY category
),
customer_count AS (
    SELECT COUNT(DISTINCT customer_id) AS total_customers
    FROM customer_category
),
category_pairs AS (
    SELECT
        a.category AS source_category,
        b.category AS recommended_category,
        COUNT(DISTINCT a.customer_id) AS customers_with_both
    FROM customer_category a
    JOIN customer_category b
        ON a.customer_id = b.customer_id
       AND a.category <> b.category
    GROUP BY a.category, b.category
),
scored AS (
    SELECT
        cp.source_category,
        cp.recommended_category,
        cp.customers_with_both,
        source.category_customers AS source_category_customers,
        target.category_customers AS recommended_category_customers,
        cc.total_customers,
        ROUND(cp.customers_with_both::NUMERIC / NULLIF(source.category_customers, 0), 4) AS confidence,
        ROUND(target.category_customers::NUMERIC / NULLIF(cc.total_customers, 0), 4) AS baseline_category_rate,
        ROUND(
            (cp.customers_with_both::NUMERIC / NULLIF(source.category_customers, 0))
            / NULLIF(target.category_customers::NUMERIC / NULLIF(cc.total_customers, 0), 0),
            4
        ) AS affinity_lift
    FROM category_pairs cp
    JOIN category_counts source
        ON cp.source_category = source.category
    JOIN category_counts target
        ON cp.recommended_category = target.category
    CROSS JOIN customer_count cc
),
ranked AS (
    SELECT
        *,
        RANK() OVER (
            PARTITION BY source_category
            ORDER BY affinity_lift DESC, confidence DESC, customers_with_both DESC
        ) AS cross_sell_rank
    FROM scored
    WHERE customers_with_both >= 25
)
SELECT
    source_category,
    recommended_category,
    customers_with_both,
    source_category_customers,
    recommended_category_customers,
    confidence,
    baseline_category_rate,
    affinity_lift,
    cross_sell_rank,
    CASE
        WHEN affinity_lift >= 1.50 AND confidence >= 0.20 THEN 'Strong bundle candidate'
        WHEN affinity_lift >= 1.20 THEN 'Cross-sell test candidate'
        ELSE 'Low priority'
    END AS cross_sell_action_flag
FROM ranked
WHERE cross_sell_rank <= 5
ORDER BY source_category, cross_sell_rank;
