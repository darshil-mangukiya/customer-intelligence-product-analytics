from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = REPO_ROOT / "data" / "marts"
EXPORTS_DIR = REPO_ROOT / "data" / "exports"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SAMPLE_DIR = REPO_ROOT / "data" / "sample" / "customer_intelligence"
REPORTS_DIR = REPO_ROOT / "reports"


@dataclass(frozen=True)
class LoadedDataset:
    name: str
    frame: pd.DataFrame
    source_path: Path | None
    source_label: str
    is_fallback: bool = False
    note: str = ""


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    cleaned = frame.copy()
    cleaned.columns = [str(col).strip().lower().replace(" ", "_").replace("-", "_") for col in cleaned.columns]
    return cleaned


def _existing(candidates: Iterable[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


@st.cache_data(show_spinner=False)
def _read_csv_cached(path_text: str, nrows: int | None = None) -> pd.DataFrame:
    return pd.read_csv(path_text, nrows=nrows)


@st.cache_data(show_spinner=False)
def _read_excel_cached(path_text: str, sheet_name: str | int | None = None) -> pd.DataFrame:
    return pd.read_excel(path_text, sheet_name=sheet_name)


def load_dataset(
    name: str,
    candidates: list[Path],
    *,
    fallback: Path | None = None,
    nrows: int | None = 100_000,
    normalize: bool = True,
) -> LoadedDataset:
    path = _existing(candidates)
    is_fallback = False
    note = ""
    if path is None and fallback is not None and fallback.exists():
        path = fallback
        is_fallback = True
        note = "Loaded committed sample fallback because generated output was not found."

    if path is None:
        return LoadedDataset(
            name=name,
            frame=pd.DataFrame(),
            source_path=None,
            source_label="Missing",
            is_fallback=False,
            note="No generated output or sample fallback found.",
        )

    try:
        if path.suffix.lower() in {".xlsx", ".xls"}:
            frame = _read_excel_cached(str(path), sheet_name=0)
        else:
            frame = _read_csv_cached(str(path), nrows=nrows)
    except Exception as exc:
        return LoadedDataset(
            name=name,
            frame=pd.DataFrame(),
            source_path=path,
            source_label=path.relative_to(REPO_ROOT).as_posix(),
            is_fallback=is_fallback,
            note=f"Could not load file: {exc}",
        )

    if normalize:
        frame = _normalize_columns(frame)

    return LoadedDataset(
        name=name,
        frame=frame,
        source_path=path,
        source_label=path.relative_to(REPO_ROOT).as_posix(),
        is_fallback=is_fallback,
        note=note,
    )


def _mart(name: str) -> Path:
    return MARTS_DIR / name


def _export(name: str) -> Path:
    return EXPORTS_DIR / name


def _output(name: str) -> Path:
    return OUTPUTS_DIR / name


def _sample(name: str) -> Path:
    return SAMPLE_DIR / name


@st.cache_data(show_spinner=False)
def sample_customer_features() -> pd.DataFrame:
    customers = _normalize_columns(pd.read_csv(_sample("customers_sample.csv")))
    transactions = _normalize_columns(pd.read_csv(_sample("transactions_sample.csv")))
    if customers.empty:
        return customers
    if transactions.empty:
        customers["orders"] = 0
        customers["net_revenue"] = 0.0
        customers["return_adjusted_profit"] = 0.0
        customers["churn_label"] = customers.get("churn_status", "").astype(str).str.lower().isin(["churned", "at risk"]).astype(int)
        return customers

    transactions["return_flag"] = pd.to_numeric(transactions.get("return_flag", 0), errors="coerce").fillna(0)
    transactions["net_revenue"] = pd.to_numeric(transactions.get("revenue", 0), errors="coerce").fillna(0) * (
        1 - pd.to_numeric(transactions.get("discount", 0), errors="coerce").fillna(0)
    )
    transactions["return_adjusted_profit"] = pd.to_numeric(transactions.get("profit", 0), errors="coerce").fillna(0)
    aggregate = (
        transactions.groupby("customer_id", dropna=False)
        .agg(
            orders=("order_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
            return_adjusted_profit=("return_adjusted_profit", "sum"),
            returns=("return_flag", "sum"),
        )
        .reset_index()
    )
    merged = customers.merge(aggregate, on="customer_id", how="left")
    for col in ["orders", "net_revenue", "return_adjusted_profit", "returns"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    merged["return_rate"] = merged["returns"] / merged["orders"].replace(0, pd.NA)
    merged["return_rate"] = merged["return_rate"].fillna(0)
    merged["churn_label"] = merged.get("churn_status", "").astype(str).str.lower().isin(["churned", "at risk"]).astype(int)
    merged["repeat_purchase_flag"] = merged.get("repeat_purchase_behavior", "").astype(str).str.lower().eq("repeat").astype(int)
    merged["historical_clv"] = merged["return_adjusted_profit"]
    return merged


def load_dashboard_data() -> dict[str, LoadedDataset]:
    datasets = {
        "kpis": load_dataset(
            "KPIs",
            [_export("kpi_summary.csv")],
            fallback=_sample("kpi_summary_sample.csv"),
            nrows=None,
        ),
        "kpi_catalog": load_dataset("KPI catalog", [_output("kpi_catalog.csv"), _export("kpi_catalog.csv")], nrows=None),
        "customer_overview": load_dataset(
            "Customer overview",
            [_mart("mart_customer_overview.csv"), _mart("fact_customer_value.csv")],
            fallback=_sample("customers_sample.csv"),
            nrows=75_000,
        ),
        "segments": load_dataset(
            "Customer segments",
            [_export("segment_kpi_comparison.csv"), _mart("mart_customer_segments.csv")],
            nrows=75_000,
        ),
        "segment_profiles": load_dataset("Segment profiles", [_export("segment_profiles.csv")], nrows=None),
        "churn": load_dataset(
            "Churn risk",
            [_mart("mart_churn_risk.csv"), _export("at_risk_customers.csv"), _output("activation_churn_campaign.csv")],
            nrows=75_000,
        ),
        "churn_drivers": load_dataset(
            "Churn drivers",
            [_export("churn_driver_summary.csv"), _output("feature_importance_churn.csv")],
            nrows=None,
        ),
        "clv": load_dataset(
            "CLV",
            [_mart("mart_clv.csv"), _export("high_clv_customers.csv"), _output("activation_high_clv_customers.csv")],
            nrows=75_000,
        ),
        "clv_segment": load_dataset("CLV by segment", [_export("clv_by_segment.csv")], nrows=None),
        "clv_channel": load_dataset("CLV by channel", [_export("clv_by_acquisition_channel.csv")], nrows=None),
        "cohort": load_dataset("Cohort retention", [_mart("mart_cohort_retention.csv"), _mart("fact_cohort_retention.csv")], nrows=None),
        "cohort_heatmap": load_dataset("Cohort retention heatmap", [_export("cohort_retention_heatmap.csv")], nrows=None),
        "retention_channel": load_dataset("Retention by acquisition channel", [_export("retention_by_acquisition_channel.csv")], nrows=None),
        "retention_category": load_dataset("Retention by first category", [_export("retention_by_first_product_category.csv")], nrows=None),
        "product": load_dataset(
            "Product profitability",
            [_mart("mart_product_profitability.csv"), _export("top_revenue_products.csv")],
            fallback=_sample("products_sample.csv"),
            nrows=75_000,
        ),
        "orders": load_dataset(
            "Orders",
            [_mart("fact_orders.csv")],
            fallback=_sample("transactions_sample.csv"),
            nrows=100_000,
        ),
        "category_profit": load_dataset("Category profitability", [_mart("mart_category_profitability.csv")], nrows=None),
        "return_heavy": load_dataset("Return-heavy products", [_export("return_heavy_products.csv")], nrows=20_000),
        "low_margin": load_dataset("Low-margin high-volume products", [_export("low_margin_high_volume_products.csv")], nrows=20_000),
        "affinity": load_dataset(
            "Product affinity",
            [_mart("mart_product_affinity.csv"), _export("product_pair_affinity.csv"), _export("cross_sell_recommendations.csv")],
            nrows=20_000,
        ),
        "quality": load_dataset(
            "Data quality summary",
            [_output("data_quality_summary.csv"), _export("data_quality_summary.csv")],
            nrows=None,
        ),
        "validation": load_dataset("Validation results", [_export("validation_results.csv")], nrows=None),
        "anomalies": load_dataset("Anomaly log", [_output("anomaly_log.csv")], nrows=None),
        "rejected": load_dataset("Rejected rows", [_output("rejected_rows.csv")], nrows=None),
        "freshness": load_dataset(
            "Mart freshness",
            [_output("mart_freshness_report.csv"), _export("mart_freshness_report.csv")],
            nrows=None,
        ),
        "audit": load_dataset("Pipeline audit", [_output("pipeline_audit_log.csv")], nrows=None),
        "model_scoring": load_dataset("Model scoring log", [_output("model_scoring_log.csv")], nrows=None),
        "activation_manifest": load_dataset("Activation manifest", [_output("activation_export_manifest.csv"), _export("activation_export_manifest.csv")], nrows=None),
        "activation_churn": load_dataset("Churn campaign", [_output("activation_churn_campaign.csv"), _export("activation_churn_campaign.csv")], nrows=5_000),
        "activation_winback": load_dataset("Win-back campaign", [_output("activation_winback_campaign.csv"), _export("activation_winback_campaign.csv")], nrows=5_000),
        "activation_high_clv": load_dataset("High-CLV customers", [_output("activation_high_clv_customers.csv"), _export("activation_high_clv_customers.csv")], nrows=5_000),
        "activation_cross_sell": load_dataset("Cross-sell targets", [_output("activation_cross_sell_targets.csv"), _export("activation_cross_sell_targets.csv")], nrows=5_000),
        "activation_loyalty": load_dataset("Loyalty upgrade targets", [_output("activation_loyalty_upgrade_targets.csv"), _export("activation_loyalty_upgrade_targets.csv")], nrows=5_000),
        "activation_discount": load_dataset("Discount-sensitive customers", [_output("activation_discount_sensitive_customers.csv"), _export("activation_discount_sensitive_customers.csv")], nrows=5_000),
        "revenue_profit_forecast": load_dataset("Revenue/profit forecast", [_export("revenue_profit_forecast.csv")], nrows=None),
        "statistical_tests": load_dataset("Statistical test results", [_export("statistical_test_results.csv")], nrows=None),
        "experiment_evaluation": load_dataset("Experiment evaluation", [_export("experiment_evaluation.csv")], nrows=None),
        "statistical_churn_drivers": load_dataset("Statistical churn drivers", [_export("churn_driver_analysis.csv")], nrows=None),
        "clv_drivers": load_dataset("CLV drivers", [_export("clv_driver_analysis.csv")], nrows=None),
        "regression": load_dataset("Regression analysis", [_export("regression_analysis.csv")], nrows=None),
    }

    if datasets["customer_overview"].is_fallback:
        datasets["customer_overview"] = LoadedDataset(
            name="Customer overview",
            frame=sample_customer_features(),
            source_path=_sample("customers_sample.csv"),
            source_label="data/sample/customer_intelligence/*.csv",
            is_fallback=True,
            note="Loaded committed sample fallback because generated customer mart was not found.",
        )

    return datasets


def missing_dataset_names(datasets: dict[str, LoadedDataset]) -> list[str]:
    return [name for name, dataset in datasets.items() if dataset.frame.empty]


def fallback_dataset_names(datasets: dict[str, LoadedDataset]) -> list[str]:
    return [dataset.name for dataset in datasets.values() if dataset.is_fallback]
