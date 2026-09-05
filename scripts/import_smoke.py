from __future__ import annotations

import importlib


MODULES = [
    "api.main",
    "etl.synthetic_data",
    "etl.cleaning",
    "feature_engineering.build_features",
    "segmentation.segment_customers",
    "segmentation.rfm_analysis",
    "churn_model.train_churn_model",
    "cohort_analysis.build_cohorts",
    "product_analytics.product_insights",
    "clv.model_clv",
    "kpi.kpi_engine",
    "insights.generate_insights",
    "experimentation.ab_testing",
    "next_best_action.recommend_actions",
    "forecasting.forecast_metrics",
    "retention_analytics.lifecycle_analysis",
    "observability.schema_contracts",
    "observability.enterprise_quality",
    "activation.build_activation_exports",
    "enterprise_assets.generate_enterprise_assets",
    "orchestration.dag_runner",
    "warehouse_loader.postgres_loader",
]


def main() -> None:
    for module in MODULES:
        importlib.import_module(module)
    print(f"Imported {len(MODULES)} platform modules successfully.")


if __name__ == "__main__":
    main()
