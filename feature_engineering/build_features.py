from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv


NUMERIC_FILL_ZERO = [
    "orders",
    "completed_orders",
    "units",
    "gross_revenue",
    "net_revenue",
    "return_adjusted_profit",
    "discount_amount",
    "returns",
    "sessions",
    "page_views",
    "time_spent",
    "bounces",
    "email_opens",
    "clicks",
    "campaign_interactions",
    "support_cases",
]


def _safe_divide(numerator: pd.Series | np.ndarray, denominator: pd.Series | np.ndarray) -> np.ndarray:
    denominator = np.asarray(denominator, dtype=float)
    numerator = np.asarray(numerator, dtype=float)
    return np.divide(numerator, denominator, out=np.zeros_like(numerator, dtype=float), where=denominator != 0)


def load_processed(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    tables = {
        "customers": pd.read_csv(project_config.processed_dir / "customers_clean.csv", parse_dates=["signup_date"]),
        "products": pd.read_csv(project_config.processed_dir / "products_clean.csv", parse_dates=["launch_date"]),
        "transactions": pd.read_csv(project_config.processed_dir / "transactions_clean.csv", parse_dates=["order_date"]),
        "web_behavior": pd.read_csv(project_config.processed_dir / "web_behavior_clean.csv", parse_dates=["session_date"]),
        "engagement": pd.read_csv(project_config.processed_dir / "engagement_clean.csv", parse_dates=["last_engagement_date"]),
    }
    optional_path = project_config.processed_dir / "customer_support_interactions_clean.csv"
    if optional_path.exists():
        tables["support"] = pd.read_csv(optional_path, parse_dates=["case_date"])
    return tables


def enrich_transactions(transactions: pd.DataFrame, products: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    product_cols = [
        "product_id",
        "category",
        "sub_category",
        "base_price",
        "margin_rate",
        "profitability_profile",
        "return_profile",
        "retention_profile",
        "lifecycle_stage",
    ]
    customer_cols = ["customer_id", "acquisition_channel", "segment_seed", "loyalty_tier", "preferred_category"]
    tx = transactions.merge(products[product_cols], on="product_id", how="left")
    tx = tx.merge(customers[customer_cols], on="customer_id", how="left")
    tx["order_month"] = tx["order_date"].dt.to_period("M").astype(str)
    return tx


def build_customer_features(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    web_behavior: pd.DataFrame,
    engagement: pd.DataFrame,
    support: pd.DataFrame | None = None,
    analysis_date: str = CONFIG.analysis_date,
) -> pd.DataFrame:
    analysis_ts = pd.Timestamp(analysis_date)

    tx_agg = (
        transactions.groupby("customer_id")
        .agg(
            orders=("order_id", "nunique"),
            completed_orders=("is_completed_order", "sum"),
            units=("quantity", "sum"),
            gross_revenue=("gross_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
            return_adjusted_profit=("return_adjusted_profit", "sum"),
            discount_amount=("discount_amount", "sum"),
            returns=("return_flag", "sum"),
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
            avg_order_value=("net_revenue", "mean"),
            avg_discount_rate=("discount", "mean"),
            category_diversity=("category", "nunique"),
            product_diversity=("product_id", "nunique"),
            channel_diversity=("sales_channel", "nunique"),
        )
        .reset_index()
    )
    top_channel = (
        transactions.groupby(["customer_id", "sales_channel"])["order_id"]
        .nunique()
        .reset_index()
        .sort_values(["customer_id", "order_id"], ascending=[True, False])
        .drop_duplicates("customer_id")[["customer_id", "sales_channel"]]
        .rename(columns={"sales_channel": "primary_sales_channel"})
    )
    top_category = (
        transactions.groupby(["customer_id", "category"])["net_revenue"]
        .sum()
        .reset_index()
        .sort_values(["customer_id", "net_revenue"], ascending=[True, False])
        .drop_duplicates("customer_id")[["customer_id", "category"]]
        .rename(columns={"category": "top_purchase_category"})
    )

    session_agg = (
        web_behavior.groupby("customer_id")
        .agg(
            sessions=("session_id", "nunique"),
            page_views=("page_views", "sum"),
            time_spent=("time_spent", "sum"),
            bounces=("bounce_flag", "sum"),
            last_session_date=("session_date", "max"),
            avg_page_views=("page_views", "mean"),
            avg_session_seconds=("time_spent", "mean"),
            device_diversity=("device_type", "nunique"),
        )
        .reset_index()
    )

    if support is not None and len(support):
        support_agg = (
            support.groupby("customer_id")
            .agg(
                support_cases=("case_id", "nunique"),
                avg_resolution_hours=("resolution_hours", "mean"),
                avg_support_satisfaction=("satisfaction_score", "mean"),
            )
            .reset_index()
        )
    else:
        support_agg = pd.DataFrame({"customer_id": customers["customer_id"], "support_cases": 0, "avg_resolution_hours": 0, "avg_support_satisfaction": 0})

    features = customers.merge(tx_agg, on="customer_id", how="left")
    features = features.merge(top_channel, on="customer_id", how="left")
    features = features.merge(top_category, on="customer_id", how="left")
    features = features.merge(session_agg, on="customer_id", how="left")
    features = features.merge(engagement, on="customer_id", how="left")
    features = features.merge(support_agg, on="customer_id", how="left")

    for col in NUMERIC_FILL_ZERO:
        if col in features:
            features[col] = features[col].fillna(0)

    date_cols = ["first_order_date", "last_order_date", "last_session_date", "last_engagement_date"]
    for col in date_cols:
        if col in features:
            features[col] = pd.to_datetime(features[col], errors="coerce")

    features["recency_days"] = (analysis_ts - features["last_order_date"]).dt.days
    features["recency_days"] = features["recency_days"].fillna(999).clip(lower=0)
    features["days_since_session"] = (analysis_ts - features["last_session_date"]).dt.days.fillna(999).clip(lower=0)
    features["days_since_engagement"] = features["days_since_engagement"].fillna(999).clip(lower=0)
    features["customer_age_days"] = (analysis_ts - features["signup_date"]).dt.days.clip(lower=1)
    features["purchase_frequency_30d"] = features["orders"] / features["customer_age_days"] * 30
    features["repeat_purchase_flag"] = features["orders"].ge(2).astype(int)
    features["return_rate"] = _safe_divide(features["returns"], features["orders"])
    features["discount_dependency"] = _safe_divide(features["discount_amount"], features["discount_amount"] + features["net_revenue"])
    features["profit_margin"] = _safe_divide(features["return_adjusted_profit"], features["net_revenue"])
    features["revenue_per_session"] = _safe_divide(features["net_revenue"], features["sessions"])
    features["bounce_rate"] = _safe_divide(features["bounces"], features["sessions"])
    engagement_rate_fallback = pd.Series(
        _safe_divide(features["clicks"], features["email_opens"]),
        index=features.index,
    )
    features["engagement_rate"] = features["engagement_rate"].fillna(engagement_rate_fallback)
    features["avg_order_value"] = features["avg_order_value"].fillna(0)
    features["avg_discount_rate"] = features["avg_discount_rate"].fillna(0)
    features["category_diversity"] = features["category_diversity"].fillna(0)
    features["product_diversity"] = features["product_diversity"].fillna(0)
    features["channel_diversity"] = features["channel_diversity"].fillna(0)
    features["primary_sales_channel"] = features["primary_sales_channel"].fillna("No Purchase")
    features["top_purchase_category"] = features["top_purchase_category"].fillna(features["preferred_category"]).fillna("Unknown")

    behavior_churn = (
        features["recency_days"].gt(120)
        | (features["orders"].le(1) & features["days_since_engagement"].gt(90))
        | features["churn_status"].isin(["Churned", "Dormant"])
    )
    features["churn_label"] = behavior_churn.astype(int)
    features["historical_clv"] = features["return_adjusted_profit"].clip(lower=-500)
    features["customer_value_band"] = pd.cut(
        features["historical_clv"],
        bins=[-np.inf, 0, 100, 350, 1000, np.inf],
        labels=["Negative", "Low", "Mid", "High", "Elite"],
    ).astype(str)

    return features


def build_product_features(products: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    customer_repeat = transactions.groupby("customer_id")["order_id"].nunique().rename("customer_orders").reset_index()
    tx = transactions.merge(customer_repeat, on="customer_id", how="left")
    tx["repeat_customer_flag"] = tx["customer_orders"].ge(2)

    agg = (
        tx.groupby("product_id")
        .agg(
            orders=("order_id", "nunique"),
            units=("quantity", "sum"),
            customers=("customer_id", "nunique"),
            repeat_customers=("repeat_customer_flag", "sum"),
            gross_revenue=("gross_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
            return_adjusted_profit=("return_adjusted_profit", "sum"),
            discount_amount=("discount_amount", "sum"),
            returns=("return_flag", "sum"),
            avg_discount_rate=("discount", "mean"),
        )
        .reset_index()
    )
    features = products.merge(agg, on="product_id", how="left")
    for col in ["orders", "units", "customers", "repeat_customers", "gross_revenue", "net_revenue", "return_adjusted_profit", "discount_amount", "returns", "avg_discount_rate"]:
        features[col] = features[col].fillna(0)
    features["return_rate"] = _safe_divide(features["returns"], features["orders"])
    features["return_adjusted_margin"] = _safe_divide(features["return_adjusted_profit"], features["net_revenue"])
    features["repeat_customer_rate"] = _safe_divide(features["repeat_customers"], features["orders"])
    features["discount_dependency"] = _safe_divide(features["discount_amount"], features["discount_amount"] + features["net_revenue"])
    features["product_performance_flag"] = np.select(
        [
            (features["orders"].ge(features["orders"].quantile(0.75))) & (features["return_adjusted_margin"].lt(features["return_adjusted_margin"].median())),
            features["return_rate"].ge(features["return_rate"].quantile(0.9)),
            (features["repeat_customer_rate"].ge(features["repeat_customer_rate"].quantile(0.75))) & (features["return_adjusted_margin"].gt(0)),
        ],
        ["Low Margin High Volume", "Return Heavy", "Retention Driver"],
        default="Stable",
    )
    return features


def build_cohort_base(transactions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    first_orders = (
        transactions.groupby("customer_id")
        .agg(first_order_date=("order_date", "min"), first_product_category=("category", lambda x: x.mode().iat[0] if len(x.mode()) else "Unknown"))
        .reset_index()
    )
    first_orders["cohort_month"] = first_orders["first_order_date"].dt.to_period("M").astype(str)

    cohort = transactions[["customer_id", "order_id", "order_date", "order_month", "net_revenue", "return_adjusted_profit", "acquisition_channel", "category"]].merge(
        first_orders[["customer_id", "cohort_month", "first_product_category"]],
        on="customer_id",
        how="left",
    )
    order_period = pd.PeriodIndex(cohort["order_month"], freq="M")
    cohort_period = pd.PeriodIndex(cohort["cohort_month"], freq="M")
    cohort["cohort_index"] = (order_period.year - cohort_period.year) * 12 + (order_period.month - cohort_period.month)
    cohort = cohort.merge(customers[["customer_id", "region_id", "segment_seed"]], on="customer_id", how="left")
    return cohort.loc[cohort["cohort_index"].between(0, 12)].copy()


def build_date_dimension(transactions: pd.DataFrame, web_behavior: pd.DataFrame) -> pd.DataFrame:
    min_date = min(transactions["order_date"].min(), web_behavior["session_date"].min())
    max_date = max(transactions["order_date"].max(), web_behavior["session_date"].max())
    dates = pd.DataFrame({"date": pd.date_range(min_date, max_date, freq="D")})
    dates["date_key"] = dates["date"].dt.strftime("%Y%m%d").astype(int)
    dates["year"] = dates["date"].dt.year
    dates["quarter"] = "Q" + dates["date"].dt.quarter.astype(str)
    dates["month"] = dates["date"].dt.month
    dates["month_name"] = dates["date"].dt.month_name()
    dates["week"] = dates["date"].dt.isocalendar().week.astype(int)
    dates["day_of_week"] = dates["date"].dt.day_name()
    dates["is_weekend"] = dates["date"].dt.dayofweek.isin([5, 6])
    dates["date"] = dates["date"].dt.date.astype(str)
    return dates


def build_reporting_layer(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    transactions: pd.DataFrame,
    web_behavior: pd.DataFrame,
    engagement: pd.DataFrame,
    customer_features: pd.DataFrame,
    product_features: pd.DataFrame,
    cohort_base: pd.DataFrame,
    project_config: ProjectConfig = CONFIG,
) -> dict[str, pd.DataFrame]:
    dim_customer = customers[
        [
            "customer_id",
            "signup_date",
            "age",
            "gender",
            "income_band",
            "acquisition_channel",
            "region_id",
            "state",
            "city",
            "loyalty_tier",
            "segment_seed",
            "preferred_category",
            "churn_status",
        ]
    ].copy()

    dim_product = products.copy()
    dim_category = products[["category", "sub_category"]].drop_duplicates().reset_index(drop=True)
    dim_category["category_key"] = np.arange(1, len(dim_category) + 1)
    dim_region = customers[["region_id", "state", "city"]].drop_duplicates().reset_index(drop=True)
    dim_channel = pd.DataFrame({"channel": sorted(set(transactions["sales_channel"]).union(set(customers["acquisition_channel"])).union(set(web_behavior["traffic_source"])))})
    dim_channel["channel_key"] = np.arange(1, len(dim_channel) + 1)
    dim_device = pd.DataFrame({"device_type": sorted(web_behavior["device_type"].dropna().unique())})
    dim_device["device_key"] = np.arange(1, len(dim_device) + 1)
    dim_date = build_date_dimension(transactions, web_behavior)

    fact_orders = transactions.copy()
    fact_orders["date_key"] = fact_orders["order_date"].dt.strftime("%Y%m%d").astype(int)
    fact_sessions = web_behavior.copy()
    fact_sessions["date_key"] = fact_sessions["session_date"].dt.strftime("%Y%m%d").astype(int)
    fact_engagement = engagement.copy()
    fact_engagement["date_key"] = pd.to_numeric(fact_engagement["last_engagement_date"].dt.strftime("%Y%m%d"), errors="coerce").astype("Int64")
    fact_returns = transactions.loc[transactions["return_flag"] | transactions["order_status"].isin(["Returned", "Cancelled"])].copy()
    fact_customer_value = customer_features[
        [
            "customer_id",
            "orders",
            "net_revenue",
            "return_adjusted_profit",
            "historical_clv",
            "customer_value_band",
            "recency_days",
            "purchase_frequency_30d",
            "repeat_purchase_flag",
            "churn_label",
        ]
    ].copy()

    fact_cohort_retention = (
        cohort_base.groupby(["cohort_month", "cohort_index"])
        .agg(customers=("customer_id", "nunique"), net_revenue=("net_revenue", "sum"), profit=("return_adjusted_profit", "sum"))
        .reset_index()
    )
    base_counts = fact_cohort_retention.loc[fact_cohort_retention["cohort_index"].eq(0), ["cohort_month", "customers"]].rename(columns={"customers": "cohort_customers"})
    fact_cohort_retention = fact_cohort_retention.merge(base_counts, on="cohort_month", how="left")
    fact_cohort_retention["retention_rate"] = _safe_divide(fact_cohort_retention["customers"], fact_cohort_retention["cohort_customers"])

    mart_customer_overview = customer_features.copy()
    mart_product_profitability = product_features.sort_values("return_adjusted_profit", ascending=False).copy()
    mart_cohort_retention = fact_cohort_retention.copy()
    mart_clv = customer_features[
        [
            "customer_id",
            "historical_clv",
            "customer_value_band",
            "net_revenue",
            "return_adjusted_profit",
            "orders",
            "acquisition_channel",
            "segment_seed",
            "loyalty_tier",
            "churn_label",
        ]
    ].copy()

    outputs = {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_category": dim_category,
        "dim_region": dim_region,
        "dim_channel": dim_channel,
        "dim_device": dim_device,
        "dim_date": dim_date,
        "fact_orders": fact_orders,
        "fact_sessions": fact_sessions,
        "fact_engagement": fact_engagement,
        "fact_returns": fact_returns,
        "fact_customer_value": fact_customer_value,
        "fact_cohort_retention": fact_cohort_retention,
        "mart_customer_overview": mart_customer_overview,
        "mart_product_profitability": mart_product_profitability,
        "mart_cohort_retention": mart_cohort_retention,
        "mart_clv": mart_clv,
    }
    for name, df in outputs.items():
        target = project_config.mart_dir if name.startswith(("dim_", "fact_", "mart_")) else project_config.processed_dir
        write_csv(df, target / f"{name}.csv")
    return outputs


def build_feature_sets(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    tables = load_processed(project_config)
    enriched_tx = enrich_transactions(tables["transactions"], tables["products"], tables["customers"])
    write_csv(enriched_tx, project_config.processed_dir / "transactions_enriched.csv")

    customer_features = build_customer_features(
        tables["customers"],
        enriched_tx,
        tables["web_behavior"],
        tables["engagement"],
        tables.get("support"),
        project_config.analysis_date,
    )
    product_features = build_product_features(tables["products"], enriched_tx)
    cohort_base = build_cohort_base(enriched_tx, tables["customers"])

    segmentation_cols = [
        "customer_id",
        "recency_days",
        "orders",
        "net_revenue",
        "return_adjusted_profit",
        "avg_order_value",
        "purchase_frequency_30d",
        "discount_dependency",
        "return_rate",
        "sessions",
        "avg_page_views",
        "bounce_rate",
        "engagement_score",
        "category_diversity",
    ]
    churn_cols = segmentation_cols + [
        "days_since_engagement",
        "days_since_session",
        "customer_age_days",
        "product_diversity",
        "channel_diversity",
        "support_cases",
        "churn_label",
    ]
    clv_cols = [
        "customer_id",
        "historical_clv",
        "customer_value_band",
        "orders",
        "net_revenue",
        "return_adjusted_profit",
        "recency_days",
        "purchase_frequency_30d",
        "avg_order_value",
        "discount_dependency",
        "return_rate",
        "engagement_score",
        "acquisition_channel",
        "segment_seed",
        "loyalty_tier",
        "churn_label",
    ]

    outputs = {
        "customer_features": customer_features,
        "product_features": product_features,
        "cohort_base": cohort_base,
        "segmentation_base": customer_features[segmentation_cols].copy(),
        "churn_model_base": customer_features[churn_cols].copy(),
        "clv_base": customer_features[clv_cols].copy(),
    }
    for name, df in outputs.items():
        write_csv(df, project_config.processed_dir / f"{name}.csv")

    outputs.update(
        build_reporting_layer(
            tables["customers"],
            tables["products"],
            enriched_tx,
            tables["web_behavior"],
            tables["engagement"],
            customer_features,
            product_features,
            cohort_base,
            project_config,
        )
    )
    return outputs


def main() -> None:
    build_feature_sets()


if __name__ == "__main__":
    main()
