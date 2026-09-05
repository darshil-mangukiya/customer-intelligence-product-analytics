# BigQuery and Snowflake Notes

## BigQuery

- Store raw CSV outputs in Cloud Storage and load them into `raw` datasets.
- Use partitioned fact tables on `order_date` and `session_date`.
- Cluster `fact_orders` by `customer_id`, `product_id`, and `sales_channel`.
- Convert PostgreSQL `NUMERIC` types to BigQuery `NUMERIC` or `BIGNUMERIC` for currency fields.
- Use scheduled queries or dbt Cloud to materialize marts.

## Snowflake

- Stage generated CSV files with `PUT` or external stages.
- Load raw tables with `COPY INTO`.
- Use transient tables for staging and permanent tables for marts.
- Cluster large fact tables by `order_date`, `customer_id`, and `product_id` if query patterns require it.
- Use tasks and streams for incremental pipeline orchestration in production.

## Production Enhancements

- Add dbt models and tests for transformations.
- Add Great Expectations suites for raw and mart-level validation.
- Add orchestration through Airflow, Dagster, or Prefect.
- Add row-level security by region or business unit for BI consumers.

