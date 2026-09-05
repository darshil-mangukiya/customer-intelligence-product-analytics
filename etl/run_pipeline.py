from __future__ import annotations

import argparse
import time

import pandas as pd

from churn_model.train_churn_model import train_churn_model
from clv.model_clv import run_clv_model
from cohort_analysis.build_cohorts import run_cohort_analysis
from config.settings import CONFIG, ProjectConfig
from etl.cleaning import run_cleaning
from etl.io_utils import write_csv, write_markdown
from etl.synthetic_data import GenerationConfig, generate_all
from feature_engineering.build_features import build_feature_sets
from insights.generate_insights import generate_business_insights
from kpi.kpi_engine import calculate_kpis
from product_analytics.product_insights import run_product_analytics
from segmentation.rfm_analysis import run_rfm_analysis
from segmentation.segment_customers import run_segmentation


def run_pipeline(
    generation_config: GenerationConfig,
    project_config: ProjectConfig = CONFIG,
    skip_generation: bool = False,
) -> pd.DataFrame:
    project_config.ensure_directories()
    steps: list[dict[str, object]] = []

    def timed(step_name: str, fn):
        start = time.perf_counter()
        result = fn()
        elapsed = time.perf_counter() - start
        steps.append({"step": step_name, "seconds": round(elapsed, 2), "status": "success"})
        print(f"[pipeline] {step_name} completed in {elapsed:.2f}s")
        return result

    if not skip_generation:
        timed("synthetic_data_generation", lambda: generate_all(generation_config, project_config))
    timed("data_cleaning", lambda: run_cleaning(project_config))
    timed("feature_engineering_and_reporting_layer", lambda: build_feature_sets(project_config))
    timed("customer_segmentation", lambda: run_segmentation(project_config))
    timed("rfm_analysis", lambda: run_rfm_analysis(project_config))
    timed("churn_model", lambda: train_churn_model(project_config))
    timed("cohort_analysis", lambda: run_cohort_analysis(project_config))
    timed("product_analytics", lambda: run_product_analytics(project_config))
    timed("clv_model", lambda: run_clv_model(project_config))
    timed("kpi_engine", lambda: calculate_kpis(project_config))
    timed("insights_engine", lambda: generate_business_insights(project_config))

    manifest = pd.DataFrame(steps)
    write_csv(manifest, project_config.audit_dir / "pipeline_run_manifest.csv")
    _write_pipeline_summary(manifest, generation_config, project_config, skip_generation)
    return manifest


def _write_pipeline_summary(
    manifest: pd.DataFrame,
    generation_config: GenerationConfig,
    project_config: ProjectConfig,
    skip_generation: bool,
) -> None:
    lines = [
        "# Pipeline Run Summary",
        "",
        f"- Customers requested: {generation_config.customers:,}",
        f"- Products requested: {generation_config.products:,}",
        f"- Orders requested: {generation_config.orders:,}",
        f"- Sessions requested: {generation_config.sessions:,}",
        f"- Generation skipped: {skip_generation}",
        f"- Total runtime: {manifest['seconds'].sum():,.2f} seconds",
        "",
        "| Step | Seconds | Status |",
        "|---|---:|---|",
    ]
    for row in manifest.to_dict("records"):
        lines.append(f"| {row['step']} | {row['seconds']:.2f} | {row['status']} |")
    write_markdown(lines, project_config.report_dir / "pipeline_run_summary.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full customer intelligence analytics platform.")
    parser.add_argument("--customers", type=int, default=GenerationConfig.customers)
    parser.add_argument("--products", type=int, default=GenerationConfig.products)
    parser.add_argument("--orders", type=int, default=GenerationConfig.orders)
    parser.add_argument("--sessions", type=int, default=GenerationConfig.sessions)
    parser.add_argument("--seed", type=int, default=GenerationConfig.seed)
    parser.add_argument("--skip-generation", action="store_true", help="Use existing raw files and run downstream processing only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(
        GenerationConfig(
            customers=args.customers,
            products=args.products,
            orders=args.orders,
            sessions=args.sessions,
            seed=args.seed,
        ),
        skip_generation=args.skip_generation,
    )


if __name__ == "__main__":
    main()

