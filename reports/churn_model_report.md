# Churn Model Report

The churn model estimates the probability that a customer is inactive or likely to lapse based on purchase, engagement, return, session, discount, and tenure behavior.

## Evaluation
- precision: `0.9966`
- recall: `0.9525`
- roc_auc: `0.9958`
- confusion_matrix: `[[320, 3], [44, 883]]`
- test_rows: `1250`
- positive_rate: `0.742`

## Top Churn Drivers
- `recency_days`: Increases churn risk - Longer time since last purchase is a direct churn warning.
- `orders`: Reduces churn risk - Higher purchase count usually indicates stronger relationship depth.
- `channel_diversity`: Reduces churn risk - Behavioral signal used in churn risk scoring.
- `category_diversity`: Reduces churn risk - Behavioral signal used in churn risk scoring.
- `return_rate`: Reduces churn risk - Returns can indicate product fit, experience, or quality issues.
- `discount_dependency`: Increases churn risk - High promo dependency may signal weak full-price loyalty.
- `product_diversity`: Increases churn risk - Behavioral signal used in churn risk scoring.
- `net_revenue`: Reduces churn risk - Customer value changes the priority and risk economics of retention outreach.
- `avg_page_views`: Reduces churn risk - Behavioral signal used in churn risk scoring.
- `customer_age_days`: Increases churn risk - Behavioral signal used in churn risk scoring.
- `purchase_frequency_30d`: Reduces churn risk - Frequent purchasing behavior indicates habit formation.
- `days_since_engagement`: Increases churn risk - A long engagement gap weakens retention intervention effectiveness.

## Explainability Notes
- Logistic regression is used for transparent coefficient-based interpretation.
- Risk tiers are exported as governed reporting fields for BI filtering and retention operations.
- Expected profit at risk prioritizes retention efforts by combining churn probability with return-adjusted profit.
