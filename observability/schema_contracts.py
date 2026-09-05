from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


@dataclass(frozen=True)
class TableContract:
    name: str
    path: Path
    owner: str
    grain: str
    required_columns: tuple[str, ...]
    unique_key: str | None = None
    min_rows: int = 1
    severity: str = "P1"


def build_contracts(project_config: ProjectConfig = CONFIG) -> list[TableContract]:
    return [
        TableContract(
            "fact_orders",
            project_config.mart_dir / "fact_orders.csv",
            "BI Engineering",
            "one row per order",
            ("order_id", "customer_id", "product_id", "order_date", "net_revenue", "return_adjusted_profit", "is_completed_order"),
            "order_id",
            100_000,
        ),
        TableContract(
            "mart_churn_risk",
            project_config.mart_dir / "mart_churn_risk.csv",
            "Customer Analytics",
            "one row per customer",
            ("customer_id", "churn_probability", "churn_risk_tier", "expected_profit_at_risk"),
            "customer_id",
            100_000,
        ),
        TableContract(
            "mart_clv",
            project_config.mart_dir / "mart_clv.csv",
            "Customer Analytics",
            "one row per customer",
            ("customer_id", "predicted_12m_clv", "clv_band", "expected_clv_at_risk"),
            "customer_id",
            100_000,
        ),
        TableContract(
            "mart_product_profitability",
            project_config.mart_dir / "mart_product_profitability.csv",
            "Product Analytics",
            "one row per product",
            ("product_id", "category", "net_revenue", "return_adjusted_profit", "return_rate", "return_adjusted_margin"),
            "product_id",
            1_000,
            "P2",
        ),
        TableContract(
            "kpi_summary",
            project_config.export_dir / "kpi_summary.csv",
            "BI Engineering",
            "one row per governed KPI",
            ("kpi_name", "value", "display_format", "grain", "owner", "threshold"),
            "kpi_name",
            10,
            "P1",
        ),
        TableContract(
            "next_best_actions",
            project_config.export_dir / "next_best_actions.csv",
            "Lifecycle Marketing",
            "one row per customer action recommendation",
            ("customer_id", "recommended_action", "action_priority_score", "owner_team", "success_metric"),
            "customer_id",
            100_000,
            "P2",
        ),
    ]


def evaluate_contract(contract: TableContract) -> dict[str, object]:
    if not contract.path.exists():
        return {
            "table_name": contract.name,
            "status": "FAIL",
            "severity": contract.severity,
            "owner": contract.owner,
            "grain": contract.grain,
            "row_count": 0,
            "missing_columns": ",".join(contract.required_columns),
            "duplicate_key_count": None,
            "message": "File is missing",
        }
    frame = pd.read_csv(contract.path)
    missing = sorted(set(contract.required_columns) - set(frame.columns))
    duplicate_key_count = None
    if contract.unique_key and contract.unique_key in frame.columns:
        duplicate_key_count = int(frame[contract.unique_key].duplicated().sum())
    passed = not missing and len(frame) >= contract.min_rows and (duplicate_key_count in {0, None})
    return {
        "table_name": contract.name,
        "status": "PASS" if passed else "FAIL",
        "severity": contract.severity,
        "owner": contract.owner,
        "grain": contract.grain,
        "row_count": len(frame),
        "min_rows": contract.min_rows,
        "missing_columns": ",".join(missing),
        "unique_key": contract.unique_key,
        "duplicate_key_count": duplicate_key_count,
        "message": "Contract passed" if passed else "Contract violation detected",
    }


def run_schema_contracts(project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    project_config.ensure_directories()
    results = pd.DataFrame([evaluate_contract(contract) for contract in build_contracts(project_config)])
    write_csv(results, project_config.export_dir / "schema_contract_results.csv")
    _write_report(results, project_config)
    _write_contract_catalog(project_config)
    return results


def _write_report(results: pd.DataFrame, project_config: ProjectConfig) -> None:
    customer_rows = results.loc[results["table_name"].eq("mart_churn_risk"), "row_count"]
    customer_volume = int(customer_rows.iloc[0]) if not customer_rows.empty else 0
    profile = "sample_5k" if customer_volume == 5_000 else "full_250k" if customer_volume == 250_000 else "volume_unspecified"
    if profile == "sample_5k":
        role = "authoritative current sample evidence"
    elif profile == "full_250k":
        role = "full-volume schema and lifecycle evidence; not authoritative for current 5K model KPIs"
    else:
        role = "unclassified-volume schema evidence; not authoritative for current 5K model KPIs"
    lines = [
        "# Schema Contract Report",
        "",
        f"> Evidence profile: `{profile}` ({customer_volume:,} customers) — {role}.",
        "",
        f"- Contracts evaluated: {len(results):,}",
        f"- Passing contracts: {results['status'].eq('PASS').sum():,}",
        f"- Failing contracts: {results['status'].eq('FAIL').sum():,}",
        "",
        "| Table | Status | Severity | Owner | Rows | Missing Columns | Duplicate Keys |",
        "|---|---|---|---|---:|---|---:|",
    ]
    for row in results.to_dict("records"):
        lines.append(
            f"| {row['table_name']} | {row['status']} | {row['severity']} | {row['owner']} | "
            f"{row['row_count']:,.0f} | {row.get('missing_columns', '')} | {row.get('duplicate_key_count', '')} |"
        )
    lines.extend(
        [
            "",
            "## Incident Rules",
            "- P1 failures block executive dashboard refreshes.",
            "- P2 failures require data-steward review before downstream publication.",
            "- P3 failures can publish with a release note when business impact is low.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "schema_contract_report.md")


def _write_contract_catalog(project_config: ProjectConfig) -> None:
    lines = [
        "# Source and Mart Data Contracts",
        "",
        "| Table | Owner | Grain | Unique Key | Minimum Rows | Required Columns |",
        "|---|---|---|---|---:|---|",
    ]
    for contract in build_contracts(project_config):
        lines.append(
            f"| {contract.name} | {contract.owner} | {contract.grain} | {contract.unique_key or ''} | "
            f"{contract.min_rows:,} | {', '.join(contract.required_columns)} |"
        )
    write_markdown(lines, project_config.root / "docs" / "observability" / "source_data_contracts.md")


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Evaluate schema contracts and write observability outputs.").parse_args()


def main() -> None:
    parse_args()
    run_schema_contracts()


if __name__ == "__main__":
    main()
