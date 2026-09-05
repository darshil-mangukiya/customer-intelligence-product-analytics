/*
Business question:
How are cohort revenue retention and customer retention trending month over month?

Source marts/tables:
- marts.fact_cohort_retention

Output:
Monthly cohort-index trend with rolling retention, revenue retention, and trend
direction flags for executive retention reporting.
*/

WITH monthly_retention AS (
    SELECT
        cohort_month::DATE AS cohort_month,
        cohort_index,
        SUM(customers) AS active_customers,
        SUM(cohort_customers) AS cohort_customers,
        SUM(net_revenue) AS retained_revenue,
        SUM(profit) AS retained_profit,
        ROUND(SUM(customers)::NUMERIC / NULLIF(SUM(cohort_customers), 0), 4) AS customer_retention_rate
    FROM marts.fact_cohort_retention
    WHERE cohort_index BETWEEN 0 AND 12
    GROUP BY cohort_month::DATE, cohort_index
),
cohort_revenue_base AS (
    SELECT
        cohort_month,
        retained_revenue AS month_0_revenue
    FROM monthly_retention
    WHERE cohort_index = 0
),
trend AS (
    SELECT
        mr.cohort_month,
        mr.cohort_index,
        mr.active_customers,
        mr.cohort_customers,
        mr.retained_revenue,
        mr.retained_profit,
        mr.customer_retention_rate,
        ROUND(mr.retained_revenue::NUMERIC / NULLIF(crb.month_0_revenue, 0), 4) AS revenue_retention_rate,
        AVG(mr.customer_retention_rate) OVER (
            PARTITION BY mr.cohort_index
            ORDER BY mr.cohort_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS trailing_3_cohort_customer_retention,
        LAG(mr.customer_retention_rate) OVER (
            PARTITION BY mr.cohort_index
            ORDER BY mr.cohort_month
        ) AS prior_cohort_same_month_retention,
        LAG(ROUND(mr.retained_revenue::NUMERIC / NULLIF(crb.month_0_revenue, 0), 4)) OVER (
            PARTITION BY mr.cohort_index
            ORDER BY mr.cohort_month
        ) AS prior_cohort_same_month_revenue_retention
    FROM monthly_retention mr
    JOIN cohort_revenue_base crb
        ON mr.cohort_month = crb.cohort_month
)
SELECT
    cohort_month,
    cohort_index AS months_since_acquisition,
    active_customers,
    cohort_customers,
    customer_retention_rate,
    revenue_retention_rate,
    retained_revenue,
    retained_profit,
    ROUND(trailing_3_cohort_customer_retention::NUMERIC, 4) AS trailing_3_cohort_customer_retention,
    ROUND(customer_retention_rate - COALESCE(prior_cohort_same_month_retention, customer_retention_rate), 4) AS customer_retention_delta,
    ROUND(revenue_retention_rate - COALESCE(prior_cohort_same_month_revenue_retention, revenue_retention_rate), 4) AS revenue_retention_delta,
    CASE
        WHEN customer_retention_rate < trailing_3_cohort_customer_retention - 0.05 THEN 'Below recent trend'
        WHEN customer_retention_rate > trailing_3_cohort_customer_retention + 0.05 THEN 'Above recent trend'
        ELSE 'Stable trend'
    END AS retention_trend_flag
FROM trend
ORDER BY cohort_month, months_since_acquisition;
