# Data Quality Framework

The data quality framework checks source, staged, mart, model, KPI, and dashboard readiness.

## Validation Checks

- Duplicate customers and orders.
- Missing customer_id and product_id.
- Invalid revenue or negative profit anomalies.
- Impossible order dates.
- Invalid churn labels and retention month values.
- Broken customer/product foreign keys.
- Unusual return and discount rates.
- Row count anomalies.
- Null threshold violations.
- Stale dashboard marts and model scoring outputs.
- Invalid KPI calculations.

## Outputs

- data_quality_summary.csv, validation_results.csv, rejected_rows.csv, anomaly_log.csv, pipeline_audit_log.csv, mart_freshness_report.csv.
- Markdown reports summarize pass/fail status and business impact.

## Ownership

- P1 dashboard gates: BI Engineering.
- Customer scoring gates: Customer Analytics.
- Product profitability gates: Product Analytics.
- Revenue leakage gates: Finance Analytics.
