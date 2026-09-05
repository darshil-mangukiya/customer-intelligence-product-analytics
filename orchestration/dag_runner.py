from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass, field

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


@dataclass
class Task:
    task_id: str
    command: list[str]
    depends_on: list[str] = field(default_factory=list)
    retries: int = 1
    sla_seconds: int = 600
    enabled: bool = True


def build_dag(full_refresh: bool = False, downstream_only: bool = False) -> list[Task]:
    pipeline_args = [
        sys.executable,
        "-m",
        "etl.run_pipeline",
        "--customers",
        "5000" if not full_refresh else "250000",
        "--products",
        "250" if not full_refresh else "1500",
        "--orders",
        "25000" if not full_refresh else "1050000",
        "--sessions",
        "18000" if not full_refresh else "850000",
        "--seed",
        "42",
    ]
    validation_dependencies = [] if downstream_only else ["analytics_pipeline"]
    tasks = [
        Task("analytics_pipeline", pipeline_args, retries=0, sla_seconds=3600 if full_refresh else 900, enabled=not downstream_only),
        Task("data_validation", [sys.executable, "-m", "validation.validate_data"], validation_dependencies, retries=1, sla_seconds=180),
        Task("model_monitoring", [sys.executable, "-m", "monitoring.model_monitoring"], ["data_validation"], retries=1, sla_seconds=180),
        Task("model_registry", [sys.executable, "-m", "model_registry.registry"], ["model_monitoring"], retries=1, sla_seconds=180),
        Task("experimentation", [sys.executable, "-m", "experimentation.ab_testing"], ["model_registry"], retries=1, sla_seconds=240),
        Task("statistical_analysis", [sys.executable, "-m", "analytics.run_analysis"], ["experimentation"], retries=1, sla_seconds=300),
        Task("next_best_action", [sys.executable, "-m", "next_best_action.recommend_actions"], ["statistical_analysis"], retries=1, sla_seconds=240),
        Task("forecasting", [sys.executable, "-m", "forecasting.forecast_metrics"], ["next_best_action"], retries=1, sla_seconds=240),
        Task("retention_lifecycle", [sys.executable, "-m", "retention_analytics.lifecycle_analysis"], ["forecasting"], retries=1, sla_seconds=240),
        Task("schema_contracts", [sys.executable, "-m", "observability.schema_contracts"], ["retention_lifecycle"], retries=1, sla_seconds=180),
        Task("executive_pdf", [sys.executable, "-m", "reports.executive_one_pager"], ["schema_contracts"], retries=1, sla_seconds=180),
    ]
    return tasks


def run_task(task: Task, project_config: ProjectConfig = CONFIG) -> dict[str, object]:
    start = time.perf_counter()
    attempt = 0
    last_error = ""
    status = "FAILED"

    while attempt <= task.retries:
        attempt += 1
        proc = subprocess.run(task.command, cwd=project_config.root, text=True, capture_output=True)
        elapsed = time.perf_counter() - start
        if proc.returncode == 0:
            status = "SUCCESS"
            last_error = ""
            break
        last_error = (proc.stderr or proc.stdout or "unknown error")[-2000:]
        if attempt <= task.retries:
            time.sleep(min(2 * attempt, 10))

    elapsed = time.perf_counter() - start
    return {
        "task_id": task.task_id,
        "status": status,
        "attempts": attempt,
        "seconds": round(elapsed, 2),
        "sla_seconds": task.sla_seconds,
        "sla_missed": elapsed > task.sla_seconds,
        "command": " ".join(task.command),
        "error": last_error,
    }


def run_dag(full_refresh: bool = False, downstream_only: bool = False, project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    project_config.ensure_directories()
    tasks = build_dag(full_refresh=full_refresh, downstream_only=downstream_only)
    completed: dict[str, dict[str, object]] = {}
    rows: list[dict[str, object]] = []

    for task in tasks:
        if not task.enabled:
            continue
        unmet = [dep for dep in task.depends_on if completed.get(dep, {}).get("status") != "SUCCESS"]
        if unmet:
            row = {
                "task_id": task.task_id,
                "status": "SKIPPED",
                "attempts": 0,
                "seconds": 0,
                "sla_seconds": task.sla_seconds,
                "sla_missed": False,
                "command": " ".join(task.command),
                "error": f"Unmet dependencies: {', '.join(unmet)}",
            }
        else:
            row = run_task(task, project_config)
        completed[task.task_id] = row
        rows.append(row)
        if row["status"] != "SUCCESS":
            break

    manifest = pd.DataFrame(rows)
    write_csv(manifest, project_config.audit_dir / "orchestration_run_manifest.csv")
    _write_report(manifest, full_refresh, downstream_only, project_config)
    return manifest


def _write_report(manifest: pd.DataFrame, full_refresh: bool, downstream_only: bool, project_config: ProjectConfig) -> None:
    lines = [
        "# Orchestration Run Report",
        "",
        f"- Mode: {'downstream only' if downstream_only else 'full refresh' if full_refresh else 'sample refresh'}",
        f"- Tasks completed: {manifest['status'].eq('SUCCESS').sum():,}/{len(manifest):,}",
        f"- SLA misses: {manifest['sla_missed'].sum():,}",
        "",
        "| Task | Status | Attempts | Seconds | SLA Seconds | SLA Missed |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in manifest.to_dict("records"):
        lines.append(
            f"| {row['task_id']} | {row['status']} | {row['attempts']} | {row['seconds']} | {row['sla_seconds']} | {row['sla_missed']} |"
        )
    failed = manifest.loc[manifest["status"].isin(["FAILED", "SKIPPED"])]
    if len(failed):
        lines.extend(["", "## Failure Details"])
        for row in failed.to_dict("records"):
            lines.append(f"- `{row['task_id']}`: {row['error']}")
    write_markdown(lines, project_config.report_dir / "orchestration_run_report.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local DAG orchestration for the analytics platform.")
    parser.add_argument("--full-refresh", action="store_true", help="Run the full million-order pipeline before downstream tasks.")
    parser.add_argument("--downstream-only", action="store_true", help="Use existing marts and run validation, monitoring, registry, and PDF tasks only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dag(full_refresh=args.full_refresh, downstream_only=args.downstream_only)


if __name__ == "__main__":
    main()
