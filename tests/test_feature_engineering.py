from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import ProjectConfig
from etl.cleaning import run_cleaning
from etl.synthetic_data import GenerationConfig, generate_all
from feature_engineering.build_features import build_feature_sets


def _tmp_config(root: Path) -> ProjectConfig:
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


def test_cleaning_and_feature_outputs_are_created(tmp_path):
    project_config = _tmp_config(tmp_path)
    generation_config = GenerationConfig(customers=300, products=50, orders=1200, sessions=800, seed=21)
    generate_all(generation_config, project_config)
    run_cleaning(project_config)
    outputs = build_feature_sets(project_config)

    customer_features = outputs["customer_features"]
    product_features = outputs["product_features"]

    assert len(customer_features) == generation_config.customers
    assert customer_features["customer_id"].is_unique
    assert {"recency_days", "orders", "discount_dependency", "return_rate", "churn_label"}.issubset(customer_features.columns)
    assert product_features["product_id"].is_unique
    assert (project_config.mart_dir / "fact_orders.csv").exists()

    fact_orders = pd.read_csv(project_config.mart_dir / "fact_orders.csv")
    assert "return_adjusted_profit" in fact_orders.columns
    assert fact_orders["order_id"].is_unique

