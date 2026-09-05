# Business Question to Artifact Map

| Business Question | Source Tables | Transformed Features | Marts | KPIs | Model Outputs | Dashboard Pages | Activation Exports | Stakeholder Decision |
|---|---|---|---|---|---|---|---|---|
| Who are our most valuable customers? | customers, transactions | historical_clv, predicted_12m_clv | mart_clv | CLV, revenue per customer | CLV bands | CLV dashboard | high CLV export | Retention and loyalty investment. |
| Which customers are most likely to churn? | customers, transactions, engagement | recency, engagement, return, discount | mart_churn_risk | churn rate | churn_probability | churn dashboard | churn campaign export | Retention save targeting. |
| Why do customers leave after first purchase? | transactions, engagement, sessions | orders, recency, days_since_engagement | mart_churn_risk, cohort mart | repeat purchase rate | drivers | churn/cohort dashboards | win-back export | First-to-second purchase journey. |
| Which products drive long-term retention? | products, transactions | repeat_customer_rate, retention_profile | mart_product_profitability | retention rate | product retention drivers | product dashboard | cross-sell targets | Merchandising and onboarding strategy. |
| Which products create revenue leakage? | products, orders | return_rate, discount_dependency | mart_product_profitability | return-adjusted margin | product flags | revenue leakage dashboard | none | Product quality and pricing review. |
| Which channels bring high-CLV customers? | customers, orders | acquisition_channel, predicted_clv | mart_clv | predicted CLV | CLV by channel | acquisition quality dashboard | high CLV export | Growth budget allocation. |
| Which segments deserve retention investment? | customer features | segment, churn, CLV, profit | mart_customer_segments | segment contribution | risk/value scores | segment strategy dashboard | loyalty upgrade export | Lifecycle prioritization. |
| Which cohorts are weakening over time? | orders, customers | cohort_month, cohort_index | mart_cohort_retention | cohort retention | health score | cohort dashboard | first-purchase follow-up | Onboarding and acquisition quality review. |
