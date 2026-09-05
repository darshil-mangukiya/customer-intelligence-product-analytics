# Troubleshooting Guide

Common failure modes and recommended fixes for the local production simulation.

## Missing Marts

- Run make sample or make full, then make orchestrate.
- Confirm data/marts contains fact_orders, mart_churn_risk, mart_clv, and mart_product_profitability.

## Validation Failures

- Open reports/validation_report.md.
- Check failing suite, table, column, and severity.
- Repair upstream cleaning or feature engineering logic before rerunning dashboards.

## API Missing Dataset Errors

- Run pipeline outputs before calling mart endpoints.
- Check CUSTOMER_INTELLIGENCE_API_KEY only when auth is configured.

## Activation Export Issues

- Run make activation after model scoring outputs exist.
- Confirm mart_churn_risk and mart_clv are present.
