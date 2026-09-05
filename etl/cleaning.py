from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


CHANNEL_MAP = {
    "paid search": "Paid Search",
    "paid_search": "Paid Search",
    "PAID_SEARCH": "Paid Search",
    "paid social": "Paid Social",
    "paid_social": "Paid Social",
    "PAID_SOCIAL": "Paid Social",
    "organic": "Organic Search",
    "organic search": "Organic Search",
    "email": "Email",
    "Email ": "Email",
    "referral": "Referral",
    "affiliate": "Affiliate",
    "marketplace": "Marketplace",
    "market place": "Marketplace",
    "direct": "Direct",
    "web": "Web",
    "Web": "Web",
    "mobile app": "Mobile App",
    "MOBILE_APP": "Mobile App",
    "Retail Partner": "Retail Partner",
    "Social Shop": "Social Shop",
}


def _standardize_label(value: object, default: str = "Unknown") -> str:
    if pd.isna(value):
        return default
    text = str(value).strip()
    if text == "":
        return default
    return CHANNEL_MAP.get(text, CHANNEL_MAP.get(text.lower(), text.title()))


def _audit_row(table_name: str, raw: pd.DataFrame, clean: pd.DataFrame, duplicate_rows: int, rejected_rows: int) -> dict[str, object]:
    return {
        "table_name": table_name,
        "raw_rows": len(raw),
        "clean_rows": len(clean),
        "duplicate_rows_removed": duplicate_rows,
        "rejected_or_flagged_rows": rejected_rows,
        "raw_null_cells": int(raw.isna().sum().sum()),
        "clean_null_cells": int(clean.isna().sum().sum()),
    }


def _read_raw(project_config: ProjectConfig, name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = project_config.raw_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing raw table: {path}")
    return pd.read_csv(path, parse_dates=parse_dates)


def clean_customers(raw: pd.DataFrame, project_config: ProjectConfig = CONFIG) -> tuple[pd.DataFrame, dict[str, object]]:
    duplicate_mask = raw.duplicated("customer_id", keep="first")
    duplicates = raw.loc[duplicate_mask].copy()
    if len(duplicates):
        write_csv(duplicates, project_config.rejected_dir / "customers_duplicate_customer_id.csv")

    clean = raw.loc[~duplicate_mask].copy()
    clean["signup_date"] = pd.to_datetime(clean["signup_date"], errors="coerce")
    clean["acquisition_channel"] = clean["acquisition_channel"].map(lambda x: _standardize_label(x, "Unknown"))
    clean["preferred_category"] = clean["preferred_category"].fillna("Unknown").replace({"": "Unknown"})
    clean["loyalty_tier"] = clean["loyalty_tier"].fillna("Base")
    clean["churn_status"] = clean["churn_status"].fillna("Unknown")
    clean["tenure_days"] = clean["tenure_days"].fillna((pd.Timestamp(CONFIG.analysis_date) - clean["signup_date"]).dt.days)
    clean["discount_sensitivity"] = clean["discount_sensitivity"].fillna(clean["discount_sensitivity"].median()).clip(0, 1)
    clean["return_propensity"] = clean["return_propensity"].fillna(clean["return_propensity"].median()).clip(0, 1)
    clean["age"] = clean["age"].fillna(clean["age"].median()).clip(18, 90).astype(int)

    return clean, _audit_row("customers", raw, clean, int(duplicate_mask.sum()), len(duplicates))


def clean_products(raw: pd.DataFrame, project_config: ProjectConfig = CONFIG) -> tuple[pd.DataFrame, dict[str, object]]:
    duplicate_mask = raw.duplicated("product_id", keep="first")
    duplicates = raw.loc[duplicate_mask].copy()
    if len(duplicates):
        write_csv(duplicates, project_config.rejected_dir / "products_duplicate_product_id.csv")

    clean = raw.loc[~duplicate_mask].copy()
    clean["launch_date"] = pd.to_datetime(clean["launch_date"], errors="coerce")
    clean["category"] = clean["category"].fillna("Unknown").astype(str).str.strip().str.title()
    clean["sub_category"] = clean["sub_category"].fillna("Unknown").astype(str).str.strip().str.title()
    for col in ["base_price", "unit_cost", "margin_rate"]:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")
        clean[col] = clean[col].fillna(clean[col].median())
    clean["margin_rate"] = clean["margin_rate"].clip(0.01, 0.90)
    return clean, _audit_row("products", raw, clean, int(duplicate_mask.sum()), len(duplicates))


def clean_transactions(raw: pd.DataFrame, project_config: ProjectConfig = CONFIG) -> tuple[pd.DataFrame, dict[str, object]]:
    duplicate_mask = raw.duplicated("order_id", keep="first")
    duplicates = raw.loc[duplicate_mask].copy()
    if len(duplicates):
        write_csv(duplicates, project_config.rejected_dir / "transactions_duplicate_order_id.csv")

    clean = raw.loc[~duplicate_mask].copy()
    clean["order_date"] = pd.to_datetime(clean["order_date"], errors="coerce")
    clean["sales_channel"] = clean["sales_channel"].map(lambda x: _standardize_label(x, "Unknown"))
    clean["order_status"] = clean["order_status"].fillna("Unknown").astype(str).str.strip().str.title()
    clean["return_flag"] = clean["return_flag"].fillna(False).astype(bool)
    for col in ["quantity", "revenue", "discount", "cost", "profit"]:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")

    clean["quantity"] = clean["quantity"].fillna(1).clip(1, 100)
    clean["discount"] = clean["discount"].fillna(clean["discount"].median()).clip(0, 0.85)
    clean["cost"] = clean["cost"].fillna(clean["cost"].median()).clip(lower=0)
    clean["revenue"] = clean["revenue"].fillna(clean["revenue"].median()).clip(lower=0)
    clean["profit"] = clean["profit"].fillna(clean["revenue"] - clean["cost"])

    high_revenue_threshold = clean["revenue"].quantile(0.999)
    low_margin_threshold = clean["profit"].quantile(0.001)
    clean["revenue_outlier_flag"] = clean["revenue"] > high_revenue_threshold
    clean["profit_outlier_flag"] = clean["profit"] < low_margin_threshold
    flagged = clean.loc[clean["revenue_outlier_flag"] | clean["profit_outlier_flag"]].copy()
    if len(flagged):
        write_csv(flagged, project_config.rejected_dir / "transactions_flagged_outliers.csv")

    returned_or_cancelled = clean["return_flag"] | clean["order_status"].isin(["Returned", "Cancelled"])
    clean["gross_revenue"] = clean["revenue"]
    clean["net_revenue"] = np.where(returned_or_cancelled, 0.0, clean["revenue"])
    discount_denominator = (1 - clean["discount"]).replace(0, np.nan)
    discount_amount = np.where(
        clean["discount"].gt(0),
        clean["revenue"] * clean["discount"] / discount_denominator,
        0,
    )
    clean["discount_amount"] = pd.Series(discount_amount, index=clean.index).fillna(0)
    clean["return_loss"] = np.where(returned_or_cancelled, clean["revenue"] + clean["cost"] * 0.15, 0.0)
    clean["return_adjusted_profit"] = np.where(returned_or_cancelled, -clean["cost"] * 0.15, clean["profit"])
    clean["order_month"] = clean["order_date"].dt.to_period("M").astype(str)
    clean["order_year"] = clean["order_date"].dt.year
    clean["is_completed_order"] = clean["order_status"].eq("Completed")

    return clean, _audit_row("transactions", raw, clean, int(duplicate_mask.sum()), len(flagged) + len(duplicates))


def clean_web_behavior(raw: pd.DataFrame, project_config: ProjectConfig = CONFIG) -> tuple[pd.DataFrame, dict[str, object]]:
    duplicate_mask = raw.duplicated("session_id", keep="first")
    duplicates = raw.loc[duplicate_mask].copy()
    if len(duplicates):
        write_csv(duplicates, project_config.rejected_dir / "web_behavior_duplicate_session_id.csv")

    clean = raw.loc[~duplicate_mask].copy()
    clean["session_date"] = pd.to_datetime(clean["session_date"], errors="coerce")
    clean["traffic_source"] = clean["traffic_source"].map(lambda x: _standardize_label(x, "Unknown"))
    clean["device_type"] = clean["device_type"].fillna("Unknown").astype(str).str.strip().str.title()
    clean["page_views"] = pd.to_numeric(clean["page_views"], errors="coerce").fillna(1)
    clean["time_spent"] = pd.to_numeric(clean["time_spent"], errors="coerce").fillna(0)
    clean["bounce_flag"] = clean["bounce_flag"].fillna(False).astype(bool)
    clean["odd_session_flag"] = clean["page_views"].lt(1) | clean["page_views"].gt(120) | clean["time_spent"].lt(0)
    flagged = clean.loc[clean["odd_session_flag"]].copy()
    if len(flagged):
        write_csv(flagged, project_config.rejected_dir / "web_behavior_flagged_odd_sessions.csv")

    clean["page_views"] = clean["page_views"].clip(1, 120)
    clean["time_spent"] = clean["time_spent"].clip(0, 7200)
    clean["session_month"] = clean["session_date"].dt.to_period("M").astype(str)
    return clean, _audit_row("web_behavior", raw, clean, int(duplicate_mask.sum()), len(flagged) + len(duplicates))


def clean_engagement(raw: pd.DataFrame, project_config: ProjectConfig = CONFIG) -> tuple[pd.DataFrame, dict[str, object]]:
    duplicate_mask = raw.duplicated("customer_id", keep="first")
    duplicates = raw.loc[duplicate_mask].copy()
    if len(duplicates):
        write_csv(duplicates, project_config.rejected_dir / "engagement_duplicate_customer_id.csv")

    clean = raw.loc[~duplicate_mask].copy()
    clean["last_engagement_date"] = pd.to_datetime(clean["last_engagement_date"], errors="coerce")
    for col in ["email_opens", "clicks", "campaign_interactions", "engagement_score"]:
        clean[col] = pd.to_numeric(clean[col], errors="coerce").fillna(0)
    clean["engagement_score"] = clean["engagement_score"].clip(0, 100)
    clean["engagement_rate"] = np.where(clean["email_opens"].gt(0), clean["clicks"] / clean["email_opens"], 0).clip(0, 1)
    clean["days_since_engagement"] = (pd.Timestamp(CONFIG.analysis_date) - clean["last_engagement_date"]).dt.days.clip(lower=0)
    return clean, _audit_row("engagement", raw, clean, int(duplicate_mask.sum()), len(duplicates))


def clean_optional_table(raw: pd.DataFrame, table_name: str, project_config: ProjectConfig = CONFIG) -> tuple[pd.DataFrame, dict[str, object]]:
    clean = raw.copy()
    for col in clean.columns:
        if col.endswith("_date") or col == "review_date" or col == "event_date" or col == "case_date":
            clean[col] = pd.to_datetime(clean[col], errors="coerce")
    return clean, _audit_row(table_name, raw, clean, 0, 0)


def run_cleaning(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    audit_rows: list[dict[str, object]] = []

    table_specs = {
        "customers": clean_customers,
        "products": clean_products,
        "transactions": clean_transactions,
        "web_behavior": clean_web_behavior,
        "engagement": clean_engagement,
    }

    cleaned: dict[str, pd.DataFrame] = {}
    for name, cleaner in table_specs.items():
        raw = _read_raw(project_config, name)
        clean, audit = cleaner(raw, project_config)
        cleaned[name] = clean
        audit_rows.append(audit)
        write_csv(clean, project_config.processed_dir / f"{name}_clean.csv")

    for optional_name in [
        "customer_support_interactions",
        "product_reviews",
        "loyalty_events",
        "product_affinity_seed",
    ]:
        path = project_config.raw_dir / f"{optional_name}.csv"
        if path.exists():
            raw = pd.read_csv(path)
            clean, audit = clean_optional_table(raw, optional_name, project_config)
            cleaned[optional_name] = clean
            audit_rows.append(audit)
            write_csv(clean, project_config.processed_dir / f"{optional_name}_clean.csv")

    audit = pd.DataFrame(audit_rows)
    write_csv(audit, project_config.audit_dir / "data_quality_summary.csv")
    _write_quality_report(audit, project_config)
    return cleaned


def _write_quality_report(audit: pd.DataFrame, project_config: ProjectConfig) -> None:
    lines = [
        "# Data Quality Summary",
        "",
        "This report is generated by the cleaning pipeline and tracks row-level quality controls used by the analytics marts.",
        "",
        "| Table | Raw Rows | Clean Rows | Duplicates Removed | Rejected / Flagged Rows | Raw Null Cells | Clean Null Cells |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in audit.to_dict("records"):
        lines.append(
            f"| {row['table_name']} | {row['raw_rows']:,} | {row['clean_rows']:,} | "
            f"{row['duplicate_rows_removed']:,} | {row['rejected_or_flagged_rows']:,} | "
            f"{row['raw_null_cells']:,} | {row['clean_null_cells']:,} |"
        )
    lines.extend(
        [
            "",
            "## Controls Applied",
            "- Duplicate order, session, customer, and product keys are removed and exported to `data/rejected/`.",
            "- Missing and inconsistent channels are standardized into governed channel labels.",
            "- Transaction revenue, discount, margin, return, and cancellation fields are normalized for reporting.",
            "- Extreme revenue and profit observations are retained with flags and copied into rejected-row review outputs.",
            "- Session behavior anomalies are capped for analytical stability and flagged for inspection.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "data_quality_summary.md")


def main() -> None:
    run_cleaning()


if __name__ == "__main__":
    main()
