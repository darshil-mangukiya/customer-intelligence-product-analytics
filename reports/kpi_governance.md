# KPI Governance Catalog

| KPI Name | Formula | Business Meaning | Owner | Format | Grain | Threshold |
|---|---|---|---|---|---|---|
| Churn Rate | Churned customers / total customers | Share of customers likely inactive or lapsed. | Customer Analytics | Percent | Customer | Below 25% |
| Retention Rate | 1 - churn rate | Share of customers retained over the measurement window. | Customer Analytics | Percent | Customer | Above 75% |
| Repeat Purchase Rate | Customers with 2+ orders / total customers | First-to-repeat purchase health. | Customer Analytics | Percent | Customer | Above 45% |
| Average Order Value | Net revenue / completed orders | Average completed order size after returns and cancellations. | BI | Currency | Order | Monitor by segment |
| Revenue Per Customer | Net revenue / unique customers | Customer monetization rate. | Finance Analytics | Currency | Customer | Increasing MoM |
| Return Rate | Returned orders / total orders | Product quality, fit, and experience leakage. | Product Analytics | Percent | Order | Below 10% |
| Customer Lifetime Value | Historical profit + predicted future profit | Expected customer economic value. | Customer Analytics | Currency | Customer | Increasing QoQ |
| Segment Contribution % | Segment revenue / total revenue | Segment share of business performance. | BI | Percent | Segment | Monitor mix shifts |
| Category Profitability | Return-adjusted profit by category | Category contribution after return leakage. | Product Analytics | Currency | Category | Positive margin |
| Return-adjusted Margin | Return-adjusted profit / net revenue | Margin after returns and cancellations. | Finance Analytics | Percent | Category or Business | Above 30% |
| Cohort Retention % | Active cohort customers / month 0 cohort customers | Repeat activity by acquisition month. | Customer Analytics | Percent | Cohort Month | Above target by month |
| Engagement Rate | Clicks / email opens | Lifecycle audience responsiveness. | Lifecycle Marketing | Percent | Customer | Above 20% |
| Product Affinity Score | Confidence x lift | Cross-sell strength between categories or products. | Product Analytics | Decimal | Product Pair | Prioritize top decile |
| Revenue Leakage | Return loss + discount amount | Revenue and margin lost to returns and promotions. | Finance Analytics | Currency | Order | Reduce MoM |
