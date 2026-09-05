# Power BI Dashboard Build Guide

## Data Sources

Import or DirectQuery the CSV marts from `data/marts/` or the PostgreSQL tables/views from `marts`.

Recommended tables:

- `dim_customer`
- `dim_product`
- `dim_date`
- `fact_orders`
- `fact_sessions`
- `fact_engagement`
- `fact_customer_value`
- `mart_customer_segments`
- `mart_churn_risk`
- `mart_rfm_segments`
- `mart_cohort_retention`
- `mart_product_profitability`
- `mart_product_affinity`
- `mart_clv`

## Global Filters

- Date range
- Acquisition channel
- Sales channel
- Region
- Customer segment
- Loyalty tier
- Category
- CLV band
- Churn risk tier

## Page 1: Customer Overview

Visuals:

- KPI cards: Customers, net revenue, repeat purchase rate, churn rate, retention rate, average CLV
- Donut or bar: customer segment breakdown
- Matrix: segment KPI comparison with customers, revenue, profit, churn rate, CLV
- Scatter: recency vs predicted CLV by segment
- Table: high-value customers

Drilldowns:

- Segment to customer list
- Channel to segment mix
- Category to customer value

## Page 2: Cohort Dashboard

Visuals:

- Matrix heatmap: cohort month by month index with retention rate
- Line chart: revenue retention by cohort month
- Bar chart: Month 3 retention by acquisition channel
- Bar chart: Month 3 retention by first product category

Drilldowns:

- Cohort month to customer segment
- Channel to first product category

## Page 3: Product Dashboard

Visuals:

- KPI cards: product revenue, return-adjusted profit, return rate, return-adjusted margin
- Scatter: order volume vs return-adjusted margin
- Table: low-margin high-volume products
- Table: return-heavy products
- Network-style matrix: product/category affinity and cross-sell lift

Drilldowns:

- Category to product
- Product to customer segment

## Page 4: CLV Dashboard

Visuals:

- Histogram: predicted CLV distribution
- Bar chart: CLV by segment
- Bar chart: CLV by acquisition channel
- Line chart: CLV by acquisition cohort
- Table: high-CLV customers with churn exposure

Drilldowns:

- CLV band to customer list
- Channel to CLV band

## Page 5: Churn Dashboard

Visuals:

- KPI cards: churn rate, high-risk customers, expected profit at risk
- Bar chart: churn risk tiers
- Table: at-risk customers
- Bar chart: churn drivers
- Scatter: churn probability vs CLV

Drilldowns:

- Risk tier to customer
- Driver to segment/channel

## Page 6: Executive Insights

Visuals:

- KPI cards: revenue, profit, margin, churn, retention, leakage, predicted CLV
- Top risk areas from `stakeholder_insights.csv`
- Top customer growth opportunities
- Product profitability opportunities
- Retention levers by segment and channel

## DAX Notes

Use `reports/powerbi_semantic_model_notes.md` as the measure catalog. Keep all executive cards tied to governed measures rather than visual-level calculations.

