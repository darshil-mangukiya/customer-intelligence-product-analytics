# KPI Requirements

| KPI | Business Question | Grain | Owner | Acceptance Criteria |
|---|---|---|---|---|
| Churn Rate | What share of customers are likely lost or inactive? | Customer | Customer Analytics | Matches churn model base and dashboard definition |
| Retention Rate | Are customers repeating over time? | Customer/cohort | Customer Analytics | Can be sliced by cohort, channel, category, and segment |
| Return-adjusted Profit | Which products and customers are profitable after returns? | Order/product/customer | BI Engineering | Uses return losses and cost, not gross revenue only |
| Revenue Leakage | How much value is lost to discounts and returns? | Company/category/product | Finance / BI | Adds discount and return leakage consistently |
| Predicted CLV | Which customers are worth protecting or acquiring? | Customer | Customer Analytics | Exported with CLV bands and segment/channel cuts |
| Experiment Lift | Did the retention offer improve conversion? | Variant/segment | Lifecycle Marketing | Includes conversion rate, lift, p-value, and profit proxy |
| Action Priority Score | Which customers should teams act on first? | Customer | Lifecycle Marketing | Combines profit at risk, CLV, risk, and business rules |
| Forecast Revenue | What should leadership expect next period? | Month | Finance / BI | Includes low/base/high planning bands |
