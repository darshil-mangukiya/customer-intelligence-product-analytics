# Customer Dashboard Wireframe

- Business purpose: Analyze customer base health, segments, value, and engagement.
- Target audience: Customer analytics and lifecycle teams
- Source mart: mart_customer_overview, mart_customer_segments, mart_clv
- Screenshot: add a capture from the built dashboard.

## Markdown Wireframe

```text
+--------------------------------------------------------------+
| Customer Dashboard Wireframe                                 |
+----------------------+----------------------+----------------+
| KPI Card 1           | KPI Card 2           | KPI Card 3     |
+----------------------+----------------------+----------------+
| Main trend / heatmap / comparison chart                       |
+--------------------------------------+-----------------------+
| Ranked detail table                  | Filters and drilldown |
+--------------------------------------+-----------------------+
| Insight notes and recommended action                         |
+--------------------------------------------------------------+
```

## KPI Cards

- Revenue, profit, churn, retention, CLV, return rate, or activation count depending on page.

## Filters

- Date, segment, channel, category, region, CLV band, churn risk tier.

## Charts

- KPI cards, trend chart, ranked table, distribution, cohort heatmap, or affinity matrix depending on page.

## Drilldowns

- Customer, product, segment, channel, cohort, or activation list detail.

## Sample Interpretation

- Use the page to identify the highest-priority risk, opportunity, or action list at the correct grain.

## QA Checks

- KPI cards reconcile to source mart.
- Filters preserve intended grain.
- Empty states are handled.
- Tooltips explain KPI definitions.
