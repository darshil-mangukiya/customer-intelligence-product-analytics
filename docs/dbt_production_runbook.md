# dbt Production Runbook

## Purpose

The dbt layer is locally executed against PostgreSQL while the Python pipeline remains the source for synthetic generation, ML scoring, and exports. The 2026-08-22 bounded run used dbt Core 1.11.14 with the PostgreSQL adapter 1.10.2, executed 15 models, and passed 41/41 standalone tests.

## Run Order

```bash
export DBT_POSTGRES_PASSWORD="<local password>"
# Optional: set DBT_POSTGRES_HOST, DBT_POSTGRES_PORT, DBT_POSTGRES_USER, and DBT_POSTGRES_DATABASE.
dbt deps --project-dir dbt --profiles-dir dbt
dbt debug --project-dir dbt --profiles-dir dbt
dbt parse --project-dir dbt --profiles-dir dbt
dbt compile --project-dir dbt --profiles-dir dbt
dbt seed --project-dir dbt --profiles-dir dbt
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
dbt build --project-dir dbt --profiles-dir dbt
dbt docs generate --project-dir dbt --profiles-dir dbt
```

The committed `dbt/profiles.yml` contains environment-variable references only. Keep any credential-bearing local variant ignored.

## Model Contracts

Contracts are documented in YAML with `contract.enforced: false` for portability. In a real warehouse deployment, set contracts to true once column types are stable across environments.

## Quality Gates

- Source key uniqueness and non-null checks
- Fact-to-dimension relationship tests
- Numeric range tests for rates, revenue, and cohort metrics
- Coverage tests for customer mart completeness
- Reconciliation models in `dbt/models/quality`

## Refresh Cadence

- Staging and intermediate models: daily
- Marts: daily after staging
- Snapshots: daily after mart refresh
- Dashboard exposures: refresh after marts and semantic metrics are updated

## Ownership

- Analytics Engineering: dbt models, tests, docs, exposures
- Customer Analytics: segmentation, churn, CLV definitions
- BI: semantic measures and dashboard certification
