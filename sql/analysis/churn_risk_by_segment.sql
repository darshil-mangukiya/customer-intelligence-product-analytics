/*
Business question:
Which customer segments and channels have the highest churn exposure and profit at risk?

Source marts/tables:
- marts.dim_customer
- marts.fact_customer_value
- marts.fact_orders

Output:
Segment-level churn risk summary using observed churn labels and a transparent
rule-based risk score for analysis validation and dashboard aggregation.
*/

WITH customer_profit AS (
    SELECT
        customer_id,
        SUM(return_adjusted_profit) AS lifetime_profit,
        SUM(net_revenue) AS lifetime_revenue,
        COUNT(DISTINCT order_id) AS orders
    FROM marts.fact_orders
    WHERE is_completed_order = TRUE
    GROUP BY customer_id
),
customer_risk AS (
    SELECT
        c.customer_id,
        COALESCE(c.segment_seed, 'Unclassified') AS segment_name,
        COALESCE(c.acquisition_channel, 'Unknown') AS acquisition_channel,
        c.loyalty_tier,
        COALESCE(cv.recency_days, 999) AS recency_days,
        COALESCE(cv.purchase_frequency_30d, 0) AS purchase_frequency_30d,
        COALESCE(cv.repeat_purchase_flag, 0) AS repeat_purchase_flag,
        COALESCE(cv.churn_label, 0) AS churn_label,
        COALESCE(cp.lifetime_revenue, cv.net_revenue, 0) AS lifetime_revenue,
        COALESCE(cp.lifetime_profit, cv.return_adjusted_profit, 0) AS lifetime_profit,
        CASE
            WHEN COALESCE(cv.recency_days, 999) >= 180 THEN 0.40 ELSE 0 END
          + CASE
            WHEN COALESCE(cv.purchase_frequency_30d, 0) < 0.03 THEN 0.25 ELSE 0 END
          + CASE
            WHEN COALESCE(cv.repeat_purchase_flag, 0) = 0 THEN 0.20 ELSE 0 END
          + CASE
            WHEN COALESCE(cp.lifetime_profit, cv.return_adjusted_profit, 0) > 0 THEN 0.15 ELSE 0 END
            AS transparent_churn_risk_score
    FROM marts.dim_customer c
    LEFT JOIN marts.fact_customer_value cv
        ON c.customer_id = cv.customer_id
    LEFT JOIN customer_profit cp
        ON c.customer_id = cp.customer_id
),
segment_summary AS (
    SELECT
        segment_name,
        acquisition_channel,
        COUNT(*) AS customers,
        SUM(churn_label) AS churned_or_lapsed_customers,
        ROUND(AVG(churn_label)::NUMERIC, 4) AS observed_churn_rate,
        ROUND(AVG(transparent_churn_risk_score)::NUMERIC, 4) AS avg_transparent_risk_score,
        SUM(lifetime_revenue) AS lifetime_revenue,
        SUM(lifetime_profit) AS lifetime_profit,
        SUM(CASE WHEN transparent_churn_risk_score >= 0.60 THEN lifetime_profit ELSE 0 END) AS profit_at_risk
    FROM customer_risk
    GROUP BY segment_name, acquisition_channel
),
thresholds AS (
    SELECT
        PERCENTILE_CONT(0.80) WITHIN GROUP (ORDER BY profit_at_risk) AS profit_at_risk_p80,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY observed_churn_rate) AS churn_rate_p75
    FROM segment_summary
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY profit_at_risk DESC) AS profit_risk_rank,
        RANK() OVER (PARTITION BY acquisition_channel ORDER BY observed_churn_rate DESC, customers DESC) AS channel_churn_rank
    FROM segment_summary
)
SELECT
    segment_name,
    acquisition_channel,
    customers,
    churned_or_lapsed_customers,
    observed_churn_rate,
    avg_transparent_risk_score,
    lifetime_revenue,
    lifetime_profit,
    profit_at_risk,
    profit_risk_rank,
    channel_churn_rank,
    CASE
        WHEN profit_at_risk >= t.profit_at_risk_p80
            THEN 'Priority retention segment'
        WHEN observed_churn_rate >= t.churn_rate_p75
            THEN 'High churn segment'
        ELSE 'Monitor'
    END AS business_priority_flag
FROM ranked r
CROSS JOIN thresholds t
ORDER BY profit_risk_rank, channel_churn_rank;
