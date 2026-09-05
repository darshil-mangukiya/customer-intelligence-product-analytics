# BI Semantic Layer Expansion

## Business Dimensions

- Customer: acquisition channel, region, loyalty tier, seed segment, churn status.
- Product: category, sub-category, lifecycle stage, profitability profile, return profile.
- Time: date, month, quarter, year, weekend flag.
- Behavior: device, traffic source, sales channel.

## Governed Measures

Power BI measures are documented in `dashboards/specs/dax_measure_catalog.md`. The core rule is that executive pages should use semantic measures only, not visual-level formulas.

## Drilldown Design

- Executive KPI to segment/customer/product detail.
- Segment to customer list and churn queue.
- Cohort month to acquisition channel and first product category.
- Product category to SKU-level return-adjusted profitability.
- CLV band to retention action queue.

## Refresh Strategy

- Raw data generation or ingestion runs first.
- Cleaning and feature engineering refresh marts.
- Model scoring updates churn, segmentation, and CLV outputs.
- Validation and monitoring run last.
- BI refresh reads only `data/marts` and `data/exports` or PostgreSQL `marts` schema.
