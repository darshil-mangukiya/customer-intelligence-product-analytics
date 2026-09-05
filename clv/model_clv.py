from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown
from feature_engineering.build_features import build_customer_features


CLV_FEATURES = [
    "orders",
    "net_revenue",
    "return_adjusted_profit",
    "recency_days",
    "avg_order_value",
    "purchase_frequency_30d",
    "discount_dependency",
    "return_rate",
    "sessions",
    "avg_page_views",
    "bounce_rate",
    "engagement_score",
    "category_diversity",
    "product_diversity",
    "channel_diversity",
    "customer_age_days",
]


def run_clv_model(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame | dict[str, object]]:
    project_config.ensure_directories()
    customers = pd.read_csv(project_config.processed_dir / "customers_clean.csv", parse_dates=["signup_date"])
    transactions = pd.read_csv(project_config.processed_dir / "transactions_enriched.csv", parse_dates=["order_date"])
    web_behavior = pd.read_csv(project_config.processed_dir / "web_behavior_clean.csv", parse_dates=["session_date"])
    engagement = pd.read_csv(project_config.processed_dir / "engagement_clean.csv", parse_dates=["last_engagement_date"])

    cutoff = transactions["order_date"].max() - pd.Timedelta(days=90)
    pre_tx = transactions.loc[transactions["order_date"].le(cutoff)].copy()
    future_profit = (
        transactions.loc[transactions["order_date"].gt(cutoff)]
        .groupby("customer_id")["return_adjusted_profit"]
        .sum()
        .rename("next_90d_profit")
        .reset_index()
    )
    pre_sessions = web_behavior.loc[web_behavior["session_date"].le(cutoff)].copy()
    pre_features = build_customer_features(customers, pre_tx, pre_sessions, engagement, analysis_date=cutoff.strftime("%Y-%m-%d"))
    model_table = pre_features.merge(future_profit, on="customer_id", how="left")
    model_table["next_90d_profit"] = model_table["next_90d_profit"].fillna(0).clip(lower=-500)

    X = model_table[CLV_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = model_table["next_90d_profit"]

    if y.nunique() <= 2 or len(model_table) < 100:
        model = None
        model_table["predicted_next_90d_profit"] = y.mean()
        metrics = {"mae": None, "r2": None, "note": "Insufficient target variation; mean target fallback used."}
    else:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
        model = HistGradientBoostingRegressor(max_iter=160, learning_rate=0.06, l2_regularization=0.05, random_state=42)
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        metrics = {
            "mae": round(float(mean_absolute_error(y_test, predictions)), 2),
            "r2": round(float(r2_score(y_test, predictions)), 4),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "target_mean_next_90d_profit": round(float(y.mean()), 2),
        }
        model_table["predicted_next_90d_profit"] = model.predict(X)
        joblib.dump(model, project_config.model_dir / "clv_model.joblib")

    current_features = pd.read_csv(project_config.processed_dir / "customer_features.csv")
    clv = current_features[
        [
            "customer_id",
            "signup_date",
            "acquisition_channel",
            "segment_seed",
            "loyalty_tier",
            "orders",
            "net_revenue",
            "return_adjusted_profit",
            "historical_clv",
            "churn_label",
            "recency_days",
        ]
    ].merge(model_table[["customer_id", "predicted_next_90d_profit"]], on="customer_id", how="left")
    clv["predicted_next_90d_profit"] = clv["predicted_next_90d_profit"].fillna(model_table["next_90d_profit"].mean())
    clv["predicted_12m_clv"] = clv["historical_clv"] + clv["predicted_next_90d_profit"].clip(lower=0) * 4
    clv["clv_band"] = pd.cut(
        clv["predicted_12m_clv"],
        bins=[-np.inf, 0, 100, 350, 1000, np.inf],
        labels=["Negative", "Low", "Mid", "High", "Elite"],
    ).astype(str)
    clv["acquisition_cohort"] = pd.to_datetime(clv["signup_date"], errors="coerce").dt.to_period("M").astype(str)
    clv["expected_clv_at_risk"] = clv["predicted_12m_clv"].clip(lower=0) * clv["churn_label"]

    by_segment = _aggregate_clv(clv, "segment_seed")
    by_channel = _aggregate_clv(clv, "acquisition_channel")
    by_cohort = _aggregate_clv(clv, "acquisition_cohort")
    clv_churn = (
        clv.groupby(["clv_band", "churn_label"])
        .agg(customers=("customer_id", "nunique"), avg_predicted_12m_clv=("predicted_12m_clv", "mean"))
        .reset_index()
    )

    high_clv = clv.sort_values("predicted_12m_clv", ascending=False).head(500)

    write_csv(clv, project_config.mart_dir / "mart_clv.csv")
    write_csv(by_segment, project_config.export_dir / "clv_by_segment.csv")
    write_csv(by_channel, project_config.export_dir / "clv_by_acquisition_channel.csv")
    write_csv(by_cohort, project_config.export_dir / "clv_by_acquisition_cohort.csv")
    write_csv(clv_churn, project_config.export_dir / "clv_vs_churn_relationship.csv")
    write_csv(high_clv, project_config.export_dir / "high_clv_customers.csv")
    (project_config.model_dir / "clv_model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _write_clv_report(metrics, by_segment, by_channel, project_config)
    return {
        "clv": clv,
        "by_segment": by_segment,
        "by_channel": by_channel,
        "by_cohort": by_cohort,
        "metrics": metrics,
    }


def _aggregate_clv(clv: pd.DataFrame, dimension: str) -> pd.DataFrame:
    grouped = (
        clv.groupby(dimension)
        .agg(
            customers=("customer_id", "nunique"),
            historical_clv=("historical_clv", "sum"),
            predicted_12m_clv=("predicted_12m_clv", "sum"),
            avg_predicted_12m_clv=("predicted_12m_clv", "mean"),
            churn_rate=("churn_label", "mean"),
            expected_clv_at_risk=("expected_clv_at_risk", "sum"),
        )
        .reset_index()
        .sort_values("predicted_12m_clv", ascending=False)
    )
    grouped["clv_share"] = grouped["predicted_12m_clv"] / grouped["predicted_12m_clv"].sum()
    return grouped


def _write_clv_report(metrics: dict[str, object], by_segment: pd.DataFrame, by_channel: pd.DataFrame, project_config: ProjectConfig) -> None:
    top_segment = by_segment.head(1)
    risky_channel = by_channel.sort_values("expected_clv_at_risk", ascending=False).head(1)
    lines = [
        "# Customer Lifetime Value Summary",
        "",
        "The CLV model estimates forward customer value using recent purchase, engagement, session, return, and discount behavior.",
        "",
        "## Model Metrics",
    ]
    for key, value in metrics.items():
        lines.append(f"- {key}: `{value}`")
    if len(top_segment):
        row = top_segment.iloc[0]
        lines.append(f"- Highest predicted CLV segment: {row['segment_seed']} with ${row['predicted_12m_clv']:,.0f}.")
    if len(risky_channel):
        row = risky_channel.iloc[0]
        lines.append(f"- Highest CLV at risk by channel: {row['acquisition_channel']} with ${row['expected_clv_at_risk']:,.0f}.")
    lines.extend(
        [
            "",
            "## Business Use",
            "- Prioritize retention spend where predicted CLV and churn exposure overlap.",
            "- Compare channels by expected value, not only acquisition volume.",
            "- Use CLV bands to govern executive reporting, loyalty strategy, and audience activation.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "clv_summary.md")


def main() -> None:
    run_clv_model()


if __name__ == "__main__":
    main()

