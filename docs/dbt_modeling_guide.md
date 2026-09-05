# dbt-Style Modeling Guide

The `dbt/` folder provides a dbt-compatible local modeling layer for staging, intermediate, mart, semantic, and quality patterns.

## Model Layers

- `staging`: cleans and standardizes raw source tables without business aggregation.
- `intermediate`: creates reusable customer, product, and cohort building blocks.
- `marts`: exposes BI-ready dimensional/reporting tables.
- `semantic`: documents metrics and dashboard exposures.

## Recommended Commands

```bash
cp dbt/profiles.example.yml dbt/profiles.yml
# Edit dbt/profiles.yml if your local Postgres connection differs from the demo defaults.
dbt debug --project-dir dbt --profiles-dir dbt
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
dbt docs generate --project-dir dbt --profiles-dir dbt
```

## Why This Matters

This layer demonstrates BI developer and analytics engineering thinking:

- governed staging logic
- reusable intermediate models
- mart ownership and grain control
- metric definitions
- dashboard exposures
- model tests and lineage
