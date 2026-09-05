/*
Business question:
How should customers be grouped using recency, frequency, and monetary behavior for lifecycle actioning?

Source marts/tables:
- marts.dim_customer
- marts.fact_customer_value

Output:
Customer-level RFM scores, segment labels, and recommended action fields for
segmentation dashboards and lifecycle exports.
*/

WITH rfm_base AS (
    SELECT
        c.customer_id,
        c.acquisition_channel,
        c.loyalty_tier,
        c.preferred_category,
        COALESCE(cv.recency_days, 999) AS recency_days,
        COALESCE(cv.orders, 0) AS frequency_orders,
        COALESCE(cv.net_revenue, 0) AS monetary_revenue,
        COALESCE(cv.return_adjusted_profit, 0) AS monetary_profit,
        COALESCE(cv.repeat_purchase_flag, 0) AS repeat_purchase_flag,
        COALESCE(cv.churn_label, 0) AS churn_label
    FROM marts.dim_customer c
    LEFT JOIN marts.fact_customer_value cv
        ON c.customer_id = cv.customer_id
),
rfm_scores AS (
    SELECT
        *,
        6 - NTILE(5) OVER (ORDER BY recency_days ASC) AS recency_score,
        NTILE(5) OVER (ORDER BY frequency_orders ASC) AS frequency_score,
        NTILE(5) OVER (ORDER BY monetary_revenue ASC) AS monetary_score
    FROM rfm_base
),
segmented AS (
    SELECT
        *,
        recency_score + frequency_score + monetary_score AS rfm_total_score,
        CONCAT(recency_score, frequency_score, monetary_score) AS rfm_code
    FROM rfm_scores
)
SELECT
    customer_id,
    acquisition_channel,
    loyalty_tier,
    preferred_category,
    recency_days,
    frequency_orders,
    monetary_revenue,
    monetary_profit,
    recency_score,
    frequency_score,
    monetary_score,
    rfm_total_score,
    rfm_code,
    churn_label,
    CASE
        WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'Champions'
        WHEN recency_score >= 3 AND frequency_score >= 4 THEN 'Loyal Customers'
        WHEN recency_score >= 4 AND frequency_score BETWEEN 2 AND 3 THEN 'Potential Loyalists'
        WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At Risk'
        WHEN recency_score = 1 AND frequency_score <= 2 THEN 'Lost Customers'
        ELSE 'Developing Customers'
    END AS rfm_segment,
    CASE
        WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'VIP retention and referral offer'
        WHEN recency_score >= 3 AND frequency_score >= 4 THEN 'Cross-sell category expansion'
        WHEN recency_score >= 4 AND frequency_score BETWEEN 2 AND 3 THEN 'Second or third purchase trigger'
        WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'Win-back with value reminder'
        WHEN recency_score = 1 AND frequency_score <= 2 THEN 'Low-cost reactivation only'
        ELSE 'Standard lifecycle nurture'
    END AS recommended_action
FROM segmented
ORDER BY rfm_total_score DESC, monetary_revenue DESC;
