# Feature Catalog

Feature-store-style catalog for customer intelligence features.

| feature_table | feature_name | formula | grain | refresh_frequency | source_table | business_meaning | used_by |
|---|---|---|---|---|---|---|---|
| customer_behavior_features | recency_days | analysis_date - last_order_date | customer | Daily or pipeline run | customer_features | How long the customer has been inactive. | churn, segments, retention dashboard |
| customer_behavior_features | orders | distinct order_id count | customer | Daily or pipeline run | fact_orders | Customer purchase depth. | segments, CLV, executive KPIs |
| customer_behavior_features | purchase_frequency_30d | orders / customer_age_days * 30 | customer | Daily or pipeline run | customer_features | Normalized purchase frequency. | churn, CLV, RFM |
| customer_monetary_features | net_revenue | sum revenue after discounts and status adjustments | customer | Daily or pipeline run | fact_orders | Customer revenue contribution. | CLV, segments, customer dashboard |
| customer_monetary_features | return_adjusted_profit | sum profit after return loss | customer | Daily or pipeline run | fact_orders | Customer economic value after leakage. | CLV, churn priority, executive KPIs |
| customer_monetary_features | avg_order_value | net_revenue / completed_orders | customer | Daily or pipeline run | fact_orders | Average completed order size. | segments, KPI cards |
| customer_engagement_features | engagement_score | weighted opens, clicks, and campaign activity | customer | Daily or campaign refresh | engagement | Lifecycle reachability and intent. | churn, activation, engagement dashboard |
| customer_engagement_features | days_since_engagement | analysis_date - last_engagement_date | customer | Daily or campaign refresh | engagement | Engagement staleness. | churn, lifecycle actions |
| customer_retention_features | repeat_purchase_flag | orders >= 2 | customer | Daily or pipeline run | customer_features | First-to-repeat conversion indicator. | retention KPIs, cohorts |
| customer_retention_features | churn_label | business inactivity and status rule | customer | Daily or pipeline run | customer_features | Observed churn target for modeling. | churn model, validation |
| customer_product_affinity_features | top_purchase_category | category with highest net revenue | customer | Daily or pipeline run | transactions_enriched | Dominant customer category preference. | cross-sell, churn by first category |
| customer_product_affinity_features | category_diversity | distinct categories purchased | customer | Daily or pipeline run | fact_orders | Breadth of product engagement. | churn, segments, product dashboard |
| customer_discount_sensitivity_features | discount_dependency | discount_amount / (discount_amount + net_revenue) | customer | Daily or pipeline run | fact_orders | How dependent the customer is on promotions. | segments, churn, activation |
| customer_discount_sensitivity_features | avg_discount_rate | average line/order discount rate | customer | Daily or pipeline run | fact_orders | Promotion depth signal. | discount-sensitive exports |
| customer_return_behavior_features | return_rate | returned_orders / orders | customer | Daily or pipeline run | fact_orders | Customer return behavior and experience risk. | churn, product quality, support |
| customer_return_behavior_features | returns | sum return_flag | customer | Daily or pipeline run | fact_orders | Return volume by customer. | activation, product analytics |
| customer_churn_features | churn_probability | model probability score | customer | Model scoring run | mart_churn_risk | Likelihood of churn. | churn dashboard, activation |
| customer_churn_features | churn_risk_tier | probability banding rule | customer | Model scoring run | mart_churn_risk | Business-friendly churn tier. | dashboards, CRM exports |
| customer_churn_features | expected_profit_at_risk | churn_probability * return_adjusted_profit | customer | Model scoring run | mart_churn_risk | Retention value exposure. | activation priority |
| customer_clv_features | historical_clv | historical return-adjusted profit | customer | Daily or pipeline run | mart_clv | Past customer value. | CLV dashboard |
| customer_clv_features | predicted_12m_clv | model predicted future value annualized | customer | Model scoring run | mart_clv | Expected future customer value. | CLV dashboard, activation |
| customer_clv_features | clv_band | business bands over predicted CLV | customer | Model scoring run | mart_clv | Value tier for targeting and reporting. | segments, churn priority, executive KPIs |
