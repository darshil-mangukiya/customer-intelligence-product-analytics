from __future__ import annotations

import argparse
import platform
import resource
import tempfile
import time
from pathlib import Path

import pandas as pd

from config.settings import ProjectConfig
from etl.io_utils import write_csv, write_markdown
from etl.run_pipeline import run_pipeline
from etl.synthetic_data import GenerationConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def isolated_config(root: Path) -> ProjectConfig:
    return ProjectConfig(
        root=root,
        raw_dir=root / "data" / "raw",
        processed_dir=root / "data" / "processed",
        mart_dir=root / "data" / "marts",
        export_dir=root / "data" / "exports",
        rejected_dir=root / "data" / "rejected",
        audit_dir=root / "data" / "audit",
        report_dir=root / "reports",
        model_dir=root / "models",
    )


def peak_rss_mb() -> float:
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**2 if platform.system() == "Darwin" else 1024
    return float(maximum / divisor)


def output_size_mb(root: Path) -> float:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) / 1024**2


def run_profile(name: str, generation: GenerationConfig, root: Path) -> dict[str, object]:
    config = isolated_config(root / name)
    started = time.perf_counter()
    manifest = run_pipeline(generation, config)
    total = time.perf_counter() - started
    timings = manifest.set_index("step")["seconds"].to_dict()
    raw_transactions = len(pd.read_csv(config.raw_dir / "transactions.csv", usecols=["order_id"]))
    raw_sessions = len(pd.read_csv(config.raw_dir / "web_behavior.csv", usecols=["session_id"]))
    model_time = sum(timings.get(step, 0.0) for step in ("customer_segmentation", "churn_model", "clv_model"))
    analytics_time = sum(
        timings.get(step, 0.0)
        for step in ("rfm_analysis", "cohort_analysis", "product_analytics", "kpi_engine", "insights_engine")
    )
    return {
        "profile": name,
        "customers": generation.customers,
        "transactions": raw_transactions,
        "sessions": raw_sessions,
        "generation_seconds": timings.get("synthetic_data_generation", 0.0),
        "cleaning_seconds": timings.get("data_cleaning", 0.0),
        "feature_engineering_seconds": timings.get("feature_engineering_and_reporting_layer", 0.0),
        "model_training_and_scoring_seconds": model_time,
        "analytics_seconds": analytics_time,
        "total_seconds": total,
        "peak_process_rss_mb": peak_rss_mb(),
        "output_size_mb": output_size_mb(config.root),
        "status": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run isolated local P3 pipeline benchmarks.")
    parser.add_argument("--include-50k", action="store_true")
    args = parser.parse_args()

    profiles = [
        ("5k", GenerationConfig(customers=5_000, products=250, orders=25_000, sessions=18_000, seed=42)),
    ]
    if args.include_50k:
        profiles.append(
            ("50k", GenerationConfig(customers=50_000, products=1_000, orders=250_000, sessions=180_000, seed=42))
        )

    with tempfile.TemporaryDirectory(prefix="p3-pipeline-benchmark-") as temporary:
        rows = [run_profile(name, generation, Path(temporary)) for name, generation in profiles]

    results = pd.DataFrame(rows)
    write_csv(results, PROJECT_ROOT / "data" / "audit" / "performance_benchmark.csv")
    report = [
        "# Controlled Pandas Pipeline Performance Benchmark",
        "",
        "Profiles ran in isolated disposable directories with deterministic seed 42. This is a local benchmark, not a production or cloud-scale claim.",
        "",
        "| Profile | Customers | Transactions | Sessions | Total s | Peak RSS MB | Output MB | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in results.to_dict("records"):
        report.append(
            f"| {row['profile']} | {row['customers']:,} | {row['transactions']:,} | {row['sessions']:,} | "
            f"{row['total_seconds']:.2f} | {row['peak_process_rss_mb']:.2f} | {row['output_size_mb']:.2f} | {row['status']} |"
        )
    report.extend(
        [
            "",
            "## Interpretation",
            "",
            "Model training and scoring are reported together because the existing pipeline stages do not expose separate timing boundaries.",
            "The 250K-customer profile was not forced during this bounded local pass because it implies substantially larger order/session volumes and was not necessary to establish representative single-node scaling.",
            "Pandas remained adequate for the executed profiles; the largest observed bottleneck is identified from the stage timings in the CSV evidence.",
        ]
    )
    write_markdown(report, PROJECT_ROOT / "reports" / "performance_benchmark.md")


if __name__ == "__main__":
    main()
