# PostgreSQL Loader Guide

The loader in `warehouse_loader/postgres_loader.py` initializes the existing PostgreSQL DDL, loads the five raw dbt sources plus governed dimensions, facts, analytical marts, KPI/insight outputs, and synthetic experiment assignments using SQLAlchemy and psycopg2. Declared constrained tables are truncated and appended so primary/foreign keys are preserved; pandas table replacement is not used.

Run with the default Docker Compose connection:

```bash
python3 -m warehouse_loader.postgres_loader
```

Run against a custom database:

```bash
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/db python3 -m warehouse_loader.postgres_loader
```

Small smoke load:

```bash
python3 -m warehouse_loader.postgres_loader --small
```

Outputs:

- `data/audit/postgres_load_manifest.csv`
- `reports/postgres_load_report.md`

Run live inventory, constraint, row-count, and authoritative metric reconciliation with:

```bash
python3 -m scripts.postgres_validate --database-url "$DATABASE_URL"
```

Additional outputs include `postgres_table_inventory.csv`, `postgres_row_counts.csv`, `postgres_reconciliation.csv`, and `reports/postgresql_execution_report.md`. The bounded 2026-08-22 local run used PostgreSQL 16.15, loaded 19/19 targets, observed six primary and six foreign keys, and passed all eight metric reconciliations on synthetic data.
