# Semantic Model Plan

This document defines a Power BI/Tableau-ready semantic model for the local analytics platform. It supports the completed local Power BI `.pbix` dashboard and remains useful as Tableau or future BI design guidance.

## Model Purpose

The semantic model provides governed relationships, KPI measures, filter behavior, and dashboard-ready tables for customer intelligence, churn, CLV, cohort retention, product profitability, and activation reporting.

## Fact Tables

| Fact table | Grain | Business use |
|---|---|---|
| `fact_orders` | One row per order | Revenue, profit, discount, returns, product and customer purchasing behavior |
| `fact_sessions` | One row per session | Web behavior, traffic source, device behavior |
| `fact_customer_value` | One row per customer value snapshot | Customer value, recency, frequency, repeat purchase, churn label |
| `fact_cohort_retention` | One row per cohort month and cohort index | Retention and revenue retention |

## Dimension Tables

| Dimension table | Grain | Business use |
|---|---|---|
| `dim_customer` | One row per customer | Customer filters, channel, region, loyalty, segment seed, demographics |
| `dim_product` | One row per product | Product, category, sub-category, lifecycle, margin and return profile |
| `dim_date` | One row per date | Time intelligence and reporting date filters |

Recommended optional dimensions for a full BI model:

- `dim_channel`
- `dim_region`
- `dim_device`
- `dim_category`

These can be derived from the existing dimensions and facts if a BI model requires separate role-playing dimensions.

## Relationships

| Relationship | Cardinality | Filter direction | Active |
|---|---|---|---|
| `dim_customer[customer_id]` -> `fact_orders[customer_id]` | One-to-many | Single | Yes |
| `dim_product[product_id]` -> `fact_orders[product_id]` | One-to-many | Single | Yes |
| `dim_date[date_key]` -> `fact_orders[date_key]` | One-to-many | Single | Yes |
| `dim_customer[customer_id]` -> `fact_sessions[customer_id]` | One-to-many | Single | Yes |
| `dim_date[date_key]` -> `fact_sessions[date_key]` | One-to-many | Single | Yes |
| `dim_customer[customer_id]` -> `fact_customer_value[customer_id]` | One-to-one or one-to-many snapshot | Single | Yes |

Use dashboard-specific marts for complex many-to-many outputs such as product affinity.

## Date Table

- Use `dim_date` as the marked date table.
- Use `dim_date[date]` for standard time intelligence.
- Use `fact_cohort_retention[cohort_month]` and `fact_cohort_retention[cohort_index]` for cohort heatmaps.
- Avoid mixing order date and cohort month in one visual unless the grain is clearly labeled.

## Measure Table

Create a disconnected table called `Measures`. Move all DAX measures into this table and organize them by display folder:

- Revenue and Profit
- Customer Retention
- CLV
- Product and Leakage
- Cohort
- Activation

## Recommended Power BI Model Layout

Place dimensions on the top row, facts in the center, and curated marts below or to the right as dashboard-specific tables. Keep activation exports separate from the core star schema unless the report page is focused on lifecycle campaign lists.

Suggested layout:

```text
dim_date      dim_customer      dim_product
    |              |                |
fact_sessions   fact_orders   fact_customer_value
                   |
          fact_cohort_retention

Dashboard-specific marts:
mart_product_profitability
mart_customer_overview
mart_churn_risk / churn output
mart_clv / CLV output
activation exports
```

## Expected Filter Behavior

- Date slicers should filter order and session facts.
- Customer slicers should filter customer value, orders, sessions, and customer-level marts.
- Product and category slicers should filter order facts and product profitability marts.
- Cohort slicers should filter cohort retention facts only unless a page explicitly joins cohort customers to customer detail.
- Activation list filters should remain page-specific.

## Implementation Notes

- A completed local Power BI `.pbix` dashboard is included under `dashboards/powerbi/`.
- Tableau assets document the same BI design patterns and can be implemented from the governed marts.
- Some advanced marts, such as churn, CLV, and activation outputs, are generated locally as files and may need to be loaded as separate report tables.
- Product affinity is naturally a pairwise relationship and should be modeled as a dedicated mart rather than forced into the core star schema.
- Row-level security is documented as a design pattern that can be connected to an identity provider during deployment extension.
