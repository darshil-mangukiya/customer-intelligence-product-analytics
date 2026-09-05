# Power BI Implementation Guide

This guide documents the local Power BI implementation for the customer intelligence platform and can also be used to rebuild or extend the report from the project outputs.

Completed local dashboard asset:

- PBIX: `dashboards/powerbi/Customer_Intelligence_Product_Analytics.pbix`
- Screenshots: `dashboards/powerbi/screenshots/`

## Recommended Dataset Files / Tables

Preferred source options:

- PostgreSQL tables/views under the `marts` schema
- Generated CSV marts under `data/marts/` after a local pipeline run
- Committed sample outputs under `outputs/` for review of catalogs, activation exports, quality reports, and scoring artifacts

Recommended report tables:

| Table | Role | Grain |
|---|---|---|
| `dim_customer` | Customer dimension | One row per customer |
| `dim_product` | Product dimension | One row per product |
| `dim_date` | Date dimension | One row per calendar date |
| `fact_orders` | Order fact | One row per order |
| `fact_sessions` | Session fact | One row per web session |
| `fact_customer_value` | Customer value fact | One row per customer value snapshot |
| `fact_cohort_retention` | Cohort fact | One row per cohort month and cohort index |
| `mart_customer_overview` | Customer reporting mart | One row per customer |
| `mart_product_profitability` | Product profitability mart | One row per product |
| `mart_churn_risk` or churn output | Churn reporting layer | One row per scored customer |
| `mart_clv` or CLV output | CLV reporting layer | One row per customer |

## Star Schema Relationship Plan

| From table | From column | To table | To column | Cardinality | Filter direction |
|---|---|---|---|---|---|
| `dim_customer` | `customer_id` | `fact_orders` | `customer_id` | One-to-many | Single |
| `dim_product` | `product_id` | `fact_orders` | `product_id` | One-to-many | Single |
| `dim_date` | `date_key` | `fact_orders` | `date_key` | One-to-many | Single |
| `dim_customer` | `customer_id` | `fact_sessions` | `customer_id` | One-to-many | Single |
| `dim_date` | `date_key` | `fact_sessions` | `date_key` | One-to-many | Single |
| `dim_customer` | `customer_id` | `fact_customer_value` | `customer_id` | One-to-one or one-to-many snapshot | Single |

Avoid bidirectional filters unless a specific page requires them and the ambiguity has been tested.

## Date Table Guidance

- Mark `dim_date` as the official date table.
- Use `dim_date[date]` for reporting filters.
- Join `dim_date[date_key]` to facts that carry a date key.
- For cohort pages, use cohort month and cohort index from `fact_cohort_retention` rather than forcing cohort logic through the order date relationship.

## Measure Table Guidance

Create a disconnected `Measures` table to store all DAX measures. Hide technical columns where possible and keep business-facing fields visible.

Recommended measure folders:

- Revenue and profit
- Customer and retention
- CLV and value
- Product and leakage
- Cohort
- Activation

## DAX Measures To Implement

Use the formulas in [DAX measure catalog](dax_measure_catalog.md) as the governed measure starting point. Measures should be placed in the `Measures` table and used consistently across dashboard pages.

Core measures:

- Revenue
- Gross Profit
- Net Profit
- Margin %
- Return-Adjusted Revenue
- Return-Adjusted Profit
- Churn Rate
- Retention Rate
- Repeat Purchase Rate
- Average Order Value
- CLV
- Predicted CLV
- Return Rate
- Discount Rate
- Cohort Retention %
- Revenue Leakage from Returns
- Revenue Leakage from Discounts
- Segment Contribution %
- Product Affinity Score

## Slicers

Global slicers:

- Date range
- Acquisition channel
- Sales channel
- Region
- Customer segment
- Loyalty tier
- Category
- CLV band
- Churn risk tier

Page-specific slicers:

- Cohort month and cohort index for retention pages
- Product lifecycle stage for product pages
- Activation list type for lifecycle pages
- Device and traffic source for web behavior pages

## Drillthrough Pages

| Drillthrough page | Source context | Target grain |
|---|---|---|
| Customer detail | Segment, churn tier, CLV band, activation list | Customer |
| Product detail | Category, product, leakage flag | Product |
| Cohort detail | Cohort month and cohort index | Cohort month/index |
| Channel detail | Acquisition channel | Channel |

## Tooltip Pages

Recommended tooltip pages:

- Customer KPI tooltip: orders, revenue, CLV, churn tier, last purchase recency
- Product KPI tooltip: revenue, return-adjusted profit, return rate, discount rate
- Cohort tooltip: cohort size, active customers, retention rate, revenue retention

## Row-Level Security Example

Example role: `Regional Manager`

```DAX
[region_id] = USERPRINCIPALNAME()
```

For deployment extension, use a security mapping table such as `security_user_region` with one row per user and region assignment. This repository documents the BI security pattern so it can be connected to identity management when the report is published.

## Dashboard Pages

Use the completed local `.pbix` as the primary dashboard asset. The page-level specifications in `dashboards/specs/` remain useful for QA, rebuilds, and future Tableau or Power BI extensions.

- Executive Overview
- Customer Segments
- Churn & Retention
- CLV Analysis
- Cohort Retention
- Product Profitability
- Activation Center

## Refresh Strategy

Recommended local strategy:

- Import mode for committed sample outputs and local CSV marts.
- PostgreSQL import mode for larger local runs.
- DirectQuery only if PostgreSQL is tuned and dashboard interactivity remains acceptable.

Future implementation idea:

- Incremental refresh by `order_date` for order facts.
- Full refresh for small dimensions.
- Model scoring refresh after feature engineering and before dashboard mart publication.

## QA Checklist

- Confirm row counts between source marts and Power BI tables.
- Confirm all KPI cards use governed DAX measures.
- Confirm date slicers filter order facts and session facts correctly.
- Confirm customer and product drillthrough pages respect selected context.
- Confirm cohort retention uses cohort month/index grain.
- Confirm no visual-level measure duplicates a governed semantic measure.
- Confirm null or unknown categories are labeled clearly.
- Confirm dashboard screenshots are generated from actual local reports, not mock images.
