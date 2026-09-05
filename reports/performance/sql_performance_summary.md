# SQL Performance Summary

This document records performance evidence and design guidance for the local PostgreSQL-ready analytics layer. No live benchmark was run as part of this final repository update because a populated local PostgreSQL database is not guaranteed to be available from the committed sample files. The checks below are therefore labeled as local design notes, not benchmark results.

## Local Design Notes

| Query or workload | Table/mart used | Approximate row count context | Runtime | Index used or recommended | Optimization note |
|---|---|---|---|---|---|
| Customer order rollups | `marts.fact_orders` | Full synthetic run target is 1M+ orders generated locally | Not benchmarked in this update | `idx_fact_orders_customer` | Customer-level aggregations should group from indexed customer keys and materialize recurring customer features. |
| Product profitability | `marts.fact_orders`, `marts.dim_product`, `marts.mart_product_profitability` | Product dimension target is 1,500 products in full run | Not benchmarked in this update | `idx_fact_orders_product` | Product dashboards should use `mart_product_profitability` rather than scan raw orders for every visual. |
| Date trend reporting | `marts.fact_orders`, `marts.dim_date` | Daily/monthly trend against order fact | Not benchmarked in this update | `idx_fact_orders_date` | Use `date_key` relationship and pre-aggregate monthly KPI marts for dashboard cards. |
| Cohort retention | `marts.fact_cohort_retention` | Month 0 through Month 12 cohort grain | Not benchmarked in this update | Composite index recommended on `(cohort_month, cohort_index)` | Cohort heatmaps should read from the cohort fact/mart rather than recomputing first purchase in the BI layer. |
| Churn dashboard | `marts.fact_customer_value`, churn scoring output | Customer-level scoring grain | Not benchmarked in this update | Index recommended on churn tier/risk score when stored in DB | Keep churn scoring output as a customer-level table to avoid repeated feature joins at dashboard time. |
| Product affinity | Pairwise affinity output or mart | Category/product pair grain | Not benchmarked in this update | Composite index recommended on `(source_category, recommended_category)` | Use a dedicated affinity mart because pairwise analysis can create many-to-many ambiguity in BI tools. |

## Existing Indexes In PostgreSQL DDL

The committed PostgreSQL schema includes these core indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer ON marts.fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_product ON marts.fact_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON marts.fact_orders(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sessions_customer ON marts.fact_sessions(customer_id);
```

Operational index notes are also documented in `sql/postgres/ops/indexes_and_grants.sql` for churn, CLV, and segment reporting tables when those marts are materialized.

## Recommended Additional Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_fact_orders_order_date
    ON marts.fact_orders(order_date);

CREATE INDEX IF NOT EXISTS idx_fact_cohort_retention_month_index
    ON marts.fact_cohort_retention(cohort_month, cohort_index);

CREATE INDEX IF NOT EXISTS idx_fact_customer_value_churn
    ON marts.fact_customer_value(churn_label);

CREATE INDEX IF NOT EXISTS idx_product_profitability_category
    ON marts.mart_product_profitability(category);
```

If `mart_product_profitability` is implemented as a view, apply category/product indexes to its underlying materialized table or source fact/dimension tables instead.

## Mart Materialization Strategy

| Mart type | Recommended materialization | Reason |
|---|---|---|
| Customer 360 / customer overview | Table or incremental table | Customer dashboards and activation exports repeatedly use the same customer features. |
| Product profitability | Materialized table | Product return and margin calculations are reused across product and revenue leakage dashboards. |
| Cohort retention | Table refreshed after order load | Cohort calculations are expensive and should not be recalculated in the BI visual layer. |
| Executive KPIs | View or small table | KPI aggregation is compact, but table materialization helps snapshot reporting. |
| Product affinity | Table | Pairwise affinity can be expensive and should be precomputed. |

## Dashboard Performance Considerations

- Prefer Power BI Import mode for local CSVs and moderate PostgreSQL extracts.
- Use DirectQuery only after validating query latency, indexes, and visual complexity.
- Keep cohort heatmaps, affinity matrices, and activation lists on precomputed marts.
- Avoid bidirectional relationships that introduce ambiguous filter paths.
- Hide raw technical fields that are not needed for reporting.
- Use aggregation tables for executive KPI cards when full order facts become large.

## Import vs DirectQuery Recommendation

| Mode | Recommendation |
|---|---|
| Import | Recommended for this local simulation because it provides fast dashboard interactions and predictable metric behavior. |
| DirectQuery | Use only if the PostgreSQL database is persistently hosted and query plans are tested. |
| Composite model | Optional for future cloud-style implementations where high-level KPI tables are imported and detailed order facts remain queried. |

## Incremental Refresh Design Notes

Future implementation if deployed beyond local simulation:

- Partition `fact_orders` by `order_date`.
- Incrementally refresh recent order partitions while keeping historical partitions static.
- Refresh customer value, churn, CLV, and activation outputs after order and engagement features are rebuilt.
- Refresh product affinity less frequently than daily order facts unless assortment changes rapidly.
- Store model scoring timestamps and mart freshness timestamps for dashboard health checks.

## Evidence Boundaries

- Documents the indexing and query-design decisions behind the marts.
- Runtimes are not benchmarked here; add them after running against a populated PostgreSQL database.
