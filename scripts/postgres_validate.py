from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from config.settings import CONFIG
from etl.io_utils import write_csv, write_markdown


@dataclass(frozen=True)
class ReconciliationMetric:
    name: str
    local_csv: Path
    local_column: str | None
    database_sql: str
    tolerance: float = 0.0


def _scalar(engine: Engine, sql: str) -> float:
    with engine.connect() as connection:
        value = connection.execute(text(sql)).scalar_one()
    return float(value or 0)


def _local_value(metric: ReconciliationMetric) -> float:
    frame = pd.read_csv(metric.local_csv)
    if metric.local_column is None:
        return float(len(frame))
    return float(pd.to_numeric(frame[metric.local_column], errors="raise").sum())


def validate(database_url: str) -> None:
    engine = create_engine(database_url)
    inventory_sql = """
        select
            table_schema as schema,
            table_name as table,
            table_type,
            count(*) over (partition by table_schema) as tables_in_schema
        from information_schema.tables
        where table_schema in (
            'raw', 'staging', 'marts', 'audit', 'analytics',
            'analytics_staging', 'analytics_intermediate',
            'analytics_marts', 'analytics_semantic', 'snapshots'
        )
        order by table_schema, table_name
    """
    inventory = pd.read_sql_query(text(inventory_sql), engine)
    constraints_sql = """
        select
            n.nspname as schema,
            c.relname as table,
            count(*) filter (where con.contype = 'p') as primary_keys,
            count(*) filter (where con.contype = 'f') as foreign_keys,
            count(*) filter (where con.contype = 'u') as unique_constraints
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        left join pg_constraint con on con.conrelid = c.oid
        where n.nspname in ('raw', 'marts') and c.relkind = 'r'
        group by n.nspname, c.relname
    """
    constraints = pd.read_sql_query(text(constraints_sql), engine)
    inventory = inventory.merge(constraints, on=["schema", "table"], how="left").fillna(0)

    row_counts: list[dict[str, object]] = []
    for record in inventory.to_dict("records"):
        schema = str(record["schema"])
        table_name = str(record["table"])
        observed = _scalar(engine, f'SELECT COUNT(*) FROM "{schema}"."{table_name}"')
        row_counts.append({"schema": schema, "table": table_name, "row_count": int(observed)})
    row_count_frame = pd.DataFrame(row_counts)

    metrics = [
        ReconciliationMetric(
            "customer_count",
            CONFIG.raw_dir / "customers.csv",
            None,
            "select count(*) from raw.customers",
        ),
        ReconciliationMetric(
            "transaction_count",
            CONFIG.raw_dir / "transactions.csv",
            None,
            "select count(*) from raw.transactions",
        ),
        ReconciliationMetric(
            "gross_revenue",
            CONFIG.raw_dir / "transactions.csv",
            "revenue",
            "select sum(revenue) from raw.transactions",
            0.01,
        ),
        ReconciliationMetric(
            "product_count",
            CONFIG.raw_dir / "products.csv",
            None,
            "select count(*) from raw.products",
        ),
        ReconciliationMetric(
            "segment_population",
            CONFIG.mart_dir / "mart_customer_segments.csv",
            None,
            "select count(*) from marts.mart_customer_segments",
        ),
        ReconciliationMetric(
            "churn_population",
            CONFIG.mart_dir / "mart_churn_risk.csv",
            None,
            "select count(*) from marts.mart_churn_risk",
        ),
        ReconciliationMetric(
            "predicted_12m_clv",
            CONFIG.mart_dir / "mart_clv.csv",
            "predicted_12m_clv",
            "select sum(predicted_12m_clv) from marts.mart_clv",
            0.01,
        ),
        ReconciliationMetric(
            "experiment_population",
            CONFIG.export_dir / "ab_test_customer_assignments.csv",
            None,
            "select count(*) from marts.experiment_assignments",
        ),
    ]
    reconciliation_rows: list[dict[str, object]] = []
    for metric in metrics:
        local_value = _local_value(metric)
        database_value = _scalar(engine, metric.database_sql)
        difference = abs(local_value - database_value)
        reconciliation_rows.append(
            {
                "metric": metric.name,
                "local_value": local_value,
                "postgres_value": database_value,
                "absolute_difference": difference,
                "tolerance": metric.tolerance,
                "status": "PASS" if difference <= metric.tolerance else "FAIL",
            }
        )
    reconciliation = pd.DataFrame(reconciliation_rows)

    write_csv(inventory, CONFIG.audit_dir / "postgres_table_inventory.csv")
    write_csv(row_count_frame, CONFIG.audit_dir / "postgres_row_counts.csv")
    write_csv(reconciliation, CONFIG.audit_dir / "postgres_reconciliation.csv")
    report = [
        "# PostgreSQL Execution Report",
        "",
        "This report records local execution against PostgreSQL using deterministic synthetic P3 data.",
        "",
        f"- Schemas observed: {inventory['schema'].nunique()}",
        f"- Tables/views observed: {len(inventory)}",
        f"- Rows across observed relations: {int(row_count_frame['row_count'].sum()):,}",
        f"- Primary keys observed: {int(inventory['primary_keys'].sum())}",
        f"- Foreign keys observed: {int(inventory['foreign_keys'].sum())}",
        f"- Reconciliation: {'PASS' if reconciliation['status'].eq('PASS').all() else 'FAIL'}",
        "",
        "## Reconciliation",
        "",
        "| Metric | Local | PostgreSQL | Difference | Tolerance | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in reconciliation.to_dict("records"):
        report.append(
            f"| {row['metric']} | {row['local_value']:.6f} | {row['postgres_value']:.6f} | "
            f"{row['absolute_difference']:.6f} | {row['tolerance']:.6f} | {row['status']} |"
        )
    report.extend(
        [
            "",
            "All experiment records and outcomes are synthetic; no real customer experiment is represented.",
        ]
    )
    write_markdown(report, CONFIG.report_dir / "postgresql_execution_report.md")

    if not reconciliation["status"].eq("PASS").all():
        raise SystemExit("PostgreSQL reconciliation failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and reconcile the local PostgreSQL warehouse.")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    validate(args.database_url)


if __name__ == "__main__":
    main()
