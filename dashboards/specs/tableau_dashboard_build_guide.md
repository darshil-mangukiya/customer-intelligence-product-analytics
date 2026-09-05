# Tableau Dashboard Build Guide

## Recommended Connection

Use PostgreSQL marts for a connected deployment or import `data/marts/*.csv` for a portable local workbook.

## Workbook Tabs

1. Executive Overview
2. Customer Segments
3. Churn Risk
4. Cohort Retention
5. Product Profitability
6. CLV Explorer

## Calculated Fields

```text
Return Adjusted Margin = SUM([return_adjusted_profit]) / SUM([net_revenue])
Repeat Purchase Rate = AVG([repeat_purchase_flag])
Churn Rate = AVG([churn_label])
Retention Rate = 1 - [Churn Rate]
Revenue Leakage = SUM([return_loss]) + SUM([discount_amount])
Average CLV = AVG([predicted_12m_clv])
```

## Dashboard Behaviors

- Use segment, channel, category, date, region, and CLV band as global filters.
- Add dashboard actions from segment summary to customer detail.
- Add product category drilldowns from category profitability to product table.
- Add cohort month filter actions from the heatmap to segment/channel detail.
- Use stakeholder insight text as annotations on executive pages.
