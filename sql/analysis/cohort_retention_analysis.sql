/*
Business question:
Which acquisition cohorts retain customers through Month 12, and where does retention decay fastest?

Source marts/tables:
- marts.dim_customer
- marts.fact_orders

Output:
One row per cohort month and cohort index with customer retention, revenue retention,
channel mix, and month-over-month retention movement. Use this for cohort dashboard
heatmaps and acquisition-retention analysis.
*/

WITH first_purchase AS (
    SELECT
        o.customer_id,
        DATE_TRUNC('month', MIN(o.order_date))::DATE AS cohort_month
    FROM marts.fact_orders o
    WHERE o.is_completed_order = TRUE
    GROUP BY o.customer_id
),
cohort_orders AS (
    SELECT
        fp.cohort_month,
        (
            (DATE_PART('year', DATE_TRUNC('month', o.order_date)) - DATE_PART('year', fp.cohort_month)) * 12
            + (DATE_PART('month', DATE_TRUNC('month', o.order_date)) - DATE_PART('month', fp.cohort_month))
        )::INTEGER AS cohort_index,
        o.customer_id,
        c.acquisition_channel,
        SUM(o.net_revenue) AS net_revenue,
        SUM(o.return_adjusted_profit) AS return_adjusted_profit
    FROM first_purchase fp
    JOIN marts.fact_orders o
        ON fp.customer_id = o.customer_id
    JOIN marts.dim_customer c
        ON fp.customer_id = c.customer_id
    WHERE o.is_completed_order = TRUE
      AND o.order_date >= fp.cohort_month
      AND o.order_date < fp.cohort_month + INTERVAL '13 months'
    GROUP BY
        fp.cohort_month,
        cohort_index,
        o.customer_id,
        c.acquisition_channel
),
retention AS (
    SELECT
        cohort_month,
        cohort_index,
        COUNT(DISTINCT customer_id) AS active_customers,
        SUM(net_revenue) AS retained_revenue,
        SUM(return_adjusted_profit) AS retained_profit,
        MODE() WITHIN GROUP (ORDER BY acquisition_channel) AS leading_channel
    FROM cohort_orders
    GROUP BY cohort_month, cohort_index
),
cohort_base AS (
    SELECT
        cohort_month,
        active_customers AS cohort_customers,
        retained_revenue AS cohort_month_0_revenue
    FROM retention
    WHERE cohort_index = 0
),
scored AS (
    SELECT
        r.cohort_month,
        r.cohort_index,
        b.cohort_customers,
        r.active_customers,
        ROUND(r.active_customers::NUMERIC / NULLIF(b.cohort_customers, 0), 4) AS retention_rate,
        ROUND(r.retained_revenue / NULLIF(b.cohort_month_0_revenue, 0), 4) AS revenue_retention_rate,
        r.retained_revenue,
        r.retained_profit,
        r.leading_channel,
        LAG(ROUND(r.active_customers::NUMERIC / NULLIF(b.cohort_customers, 0), 4))
            OVER (PARTITION BY r.cohort_month ORDER BY r.cohort_index) AS prior_month_retention
    FROM retention r
    JOIN cohort_base b
        ON r.cohort_month = b.cohort_month
    WHERE r.cohort_index BETWEEN 0 AND 12
)
SELECT
    cohort_month,
    cohort_index AS months_since_first_purchase,
    cohort_customers,
    active_customers,
    retention_rate,
    revenue_retention_rate,
    retained_revenue,
    retained_profit,
    leading_channel,
    ROUND(retention_rate - COALESCE(prior_month_retention, retention_rate), 4) AS retention_point_change,
    CASE
        WHEN cohort_index = 0 THEN 'Acquisition Month'
        WHEN retention_rate >= 0.60 THEN 'Healthy Retention'
        WHEN retention_rate >= 0.35 THEN 'Monitor'
        ELSE 'Retention Risk'
    END AS cohort_health_flag
FROM scored
ORDER BY cohort_month, months_since_first_purchase;
