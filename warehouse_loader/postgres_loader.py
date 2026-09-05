from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


DEFAULT_DATABASE_URL = "postgresql+psycopg2://analytics:analytics@localhost:5432/analytics"
SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class LoadTarget:
    csv_path: Path
    schema: str
    table: str
    preserve_schema: bool = False
    chunksize: int = 50_000


def default_targets(project_config: ProjectConfig = CONFIG) -> list[LoadTarget]:
    return [
        LoadTarget(project_config.raw_dir / "customers.csv", "raw", "customers", preserve_schema=True),
        LoadTarget(project_config.raw_dir / "products.csv", "raw", "products", preserve_schema=True),
        LoadTarget(project_config.raw_dir / "transactions.csv", "raw", "transactions", preserve_schema=True),
        LoadTarget(project_config.raw_dir / "web_behavior.csv", "raw", "web_behavior", preserve_schema=True),
        LoadTarget(project_config.raw_dir / "engagement.csv", "raw", "engagement", preserve_schema=True),
        LoadTarget(project_config.mart_dir / "dim_customer.csv", "marts", "dim_customer", preserve_schema=True),
        LoadTarget(project_config.mart_dir / "dim_product.csv", "marts", "dim_product", preserve_schema=True),
        LoadTarget(project_config.mart_dir / "dim_date.csv", "marts", "dim_date", preserve_schema=True),
        LoadTarget(project_config.mart_dir / "fact_orders.csv", "marts", "fact_orders", preserve_schema=True),
        LoadTarget(project_config.mart_dir / "fact_sessions.csv", "marts", "fact_sessions", preserve_schema=True),
        LoadTarget(project_config.mart_dir / "fact_customer_value.csv", "marts", "fact_customer_value", preserve_schema=True),
        LoadTarget(project_config.mart_dir / "mart_churn_risk.csv", "marts", "mart_churn_risk"),
        LoadTarget(project_config.mart_dir / "mart_customer_segments.csv", "marts", "mart_customer_segments"),
        LoadTarget(project_config.mart_dir / "mart_product_profitability.csv", "marts", "mart_product_profitability"),
        LoadTarget(project_config.mart_dir / "mart_cohort_retention.csv", "marts", "mart_cohort_retention"),
        LoadTarget(project_config.mart_dir / "mart_clv.csv", "marts", "mart_clv"),
        LoadTarget(project_config.export_dir / "kpi_summary.csv", "marts", "kpi_summary"),
        LoadTarget(project_config.export_dir / "stakeholder_insights.csv", "marts", "stakeholder_insights"),
        LoadTarget(
            project_config.export_dir / "ab_test_customer_assignments.csv",
            "marts",
            "experiment_assignments",
        ),
    ]


def create_engine_from_env(database_url: str | None = None) -> Engine:
    return create_engine(database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))


def _validated_identifier(value: str) -> str:
    if not SQL_IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid SQL identifier: {value!r}")
    return value


def ensure_schema(engine: Engine, schema: str) -> None:
    schema = _validated_identifier(schema)
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


def initialize_database(engine: Engine, project_config: ProjectConfig = CONFIG) -> None:
    schema_path = project_config.root / "sql" / "postgres" / "init" / "schema_postgres.sql"
    statements = [statement.strip() for statement in schema_path.read_text(encoding="utf-8").split(";") if statement.strip()]
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


def _safe_error(exc: Exception) -> str:
    message = str(exc)
    message = re.sub(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:]+:)[^@]+(@)", r"\1[REDACTED]\2", message)
    return message[:2000]


def load_target(engine: Engine, target: LoadTarget) -> dict[str, object]:
    schema = _validated_identifier(target.schema)
    table = _validated_identifier(target.table)
    if not target.csv_path.exists():
        return {
            "schema": target.schema,
            "table": target.table,
            "csv_path": str(target.csv_path.relative_to(CONFIG.root)),
            "status": "MISSING",
            "rows_loaded": 0,
            "error": "CSV not found",
        }
    rows_loaded = 0
    try:
        ensure_schema(engine, schema)
        table_exists = inspect(engine).has_table(table, schema=schema)
        if table_exists:
            with engine.begin() as connection:
                connection.execute(text(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE'))
        database_columns = (
            {column["name"] for column in inspect(engine).get_columns(table, schema=schema)}
            if table_exists and target.preserve_schema
            else None
        )
        for chunk in pd.read_csv(target.csv_path, chunksize=target.chunksize):
            if database_columns is not None:
                chunk = chunk[[column for column in chunk.columns if column in database_columns]]
            chunk.to_sql(
                table,
                engine,
                schema=schema,
                if_exists="append",
                index=False,
                method="multi",
            )
            rows_loaded += len(chunk)
        with engine.begin() as connection:
            observed = connection.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')).scalar_one()
        return {
            "schema": target.schema,
            "table": target.table,
            "csv_path": str(target.csv_path.relative_to(CONFIG.root)),
            "status": "SUCCESS" if observed == rows_loaded else "ROW_COUNT_MISMATCH",
            "rows_loaded": rows_loaded,
            "database_rows": observed,
            "error": "",
        }
    except Exception as exc:
        return {
            "schema": target.schema,
            "table": target.table,
            "csv_path": str(target.csv_path),
            "status": "FAILED",
            "rows_loaded": rows_loaded,
            "database_rows": 0,
            "error": _safe_error(exc),
        }


def load_all(
    database_url: str | None = None,
    project_config: ProjectConfig = CONFIG,
    limit_small: bool = False,
) -> pd.DataFrame:
    project_config.ensure_directories()
    engine = create_engine_from_env(database_url)
    initialize_database(engine, project_config)
    targets = default_targets(project_config)
    if limit_small:
        targets = [target for target in targets if target.table in {"dim_customer", "dim_product", "kpi_summary", "stakeholder_insights"}]
    rows = [load_target(engine, target) for target in targets]
    manifest = pd.DataFrame(rows)
    write_csv(manifest, project_config.audit_dir / "postgres_load_manifest.csv")
    _write_report(manifest, project_config)
    return manifest


def _write_report(manifest: pd.DataFrame, project_config: ProjectConfig) -> None:
    lines = [
        "# PostgreSQL Load Report",
        "",
        f"- Tables attempted: {len(manifest):,}",
        f"- Successful loads: {manifest['status'].eq('SUCCESS').sum():,}",
        "",
        "| Schema | Table | Status | Rows Loaded | Database Rows |",
        "|---|---|---|---:|---:|",
    ]
    for row in manifest.to_dict("records"):
        lines.append(
            f"| {row['schema']} | {row['table']} | {row['status']} | {row.get('rows_loaded', 0):,} | {row.get('database_rows', 0):,} |"
        )
    failed = manifest.loc[~manifest["status"].eq("SUCCESS")]
    if len(failed):
        lines.extend(["", "## Failed or Skipped Loads"])
        for row in failed.to_dict("records"):
            lines.append(f"- `{row['schema']}.{row['table']}`: {row['status']} - {row.get('error', '')}")
    write_markdown(lines, project_config.report_dir / "postgres_load_report.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load generated CSV marts into PostgreSQL.")
    parser.add_argument("--database-url", default=None, help="SQLAlchemy database URL. Defaults to DATABASE_URL env var.")
    parser.add_argument("--small", action="store_true", help="Load only a small representative subset of tables.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_all(args.database_url, limit_small=args.small)


if __name__ == "__main__":
    main()
