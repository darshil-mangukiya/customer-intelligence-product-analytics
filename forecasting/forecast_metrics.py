from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def _period_start(values: pd.Series) -> pd.Series:
    return pd.PeriodIndex(values.astype(str), freq="M").to_timestamp()


def _forecast_frame(history: pd.DataFrame, date_col: str, value_col: str, periods: int = 6) -> pd.DataFrame:
    frame = history[[date_col, value_col]].dropna().sort_values(date_col).copy()
    frame[date_col] = pd.to_datetime(frame[date_col])
    frame[value_col] = pd.to_numeric(frame[value_col], errors="coerce").fillna(0)
    if len(frame) < 3:
        last_date = frame[date_col].max() if len(frame) else pd.Timestamp("2026-01-01")
        future_dates = pd.date_range(last_date + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
        value = frame[value_col].mean() if len(frame) else 0
        return pd.DataFrame({date_col: future_dates, "forecast_value": value, "history_points": len(frame)})

    frame = frame.groupby(date_col, as_index=False)[value_col].sum()
    frame["t"] = np.arange(len(frame))
    frame["month"] = frame[date_col].dt.month
    x = np.column_stack(
        [
            frame["t"],
            np.sin(2 * np.pi * frame["month"] / 12),
            np.cos(2 * np.pi * frame["month"] / 12),
        ]
    )
    model = LinearRegression().fit(x, frame[value_col])
    future_dates = pd.date_range(frame[date_col].max() + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    future_t = np.arange(len(frame), len(frame) + periods)
    future_month = future_dates.month
    future_x = np.column_stack(
        [
            future_t,
            np.sin(2 * np.pi * future_month / 12),
            np.cos(2 * np.pi * future_month / 12),
        ]
    )
    forecasts = model.predict(future_x)
    lower_floor = max(frame[value_col].quantile(0.05) * 0.25, 0)
    result = pd.DataFrame(
        {
            date_col: future_dates,
            "forecast_value": np.maximum(forecasts, lower_floor),
            "history_points": len(frame),
        }
    )
    result["forecast_low"] = result["forecast_value"] * 0.90
    result["forecast_high"] = result["forecast_value"] * 1.10
    return result


def build_forecasts(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    orders = pd.read_csv(
        project_config.mart_dir / "fact_orders.csv",
        usecols=["order_month", "customer_id", "category", "net_revenue", "return_adjusted_profit", "is_completed_order"],
    )
    orders = orders.loc[orders["is_completed_order"].astype(bool)].copy()
    orders["month_start"] = _period_start(orders["order_month"])

    monthly = (
        orders.groupby("month_start", as_index=False)
        .agg(
            net_revenue=("net_revenue", "sum"),
            return_adjusted_profit=("return_adjusted_profit", "sum"),
            orders=("customer_id", "size"),
            customers=("customer_id", "nunique"),
        )
        .sort_values("month_start")
    )
    revenue_forecast = _forecast_frame(monthly, "month_start", "net_revenue")
    profit_forecast = _forecast_frame(monthly, "month_start", "return_adjusted_profit").rename(
        columns={"forecast_value": "profit_forecast", "forecast_low": "profit_low", "forecast_high": "profit_high"}
    )
    revenue_forecast = revenue_forecast.merge(profit_forecast[["month_start", "profit_forecast", "profit_low", "profit_high"]], on="month_start")
    revenue_forecast = revenue_forecast.rename(columns={"forecast_value": "revenue_forecast", "forecast_low": "revenue_low", "forecast_high": "revenue_high"})

    customers = pd.read_csv(project_config.processed_dir / "customer_features.csv", usecols=["signup_date", "churn_label", "acquisition_channel"])
    customers["signup_month"] = pd.to_datetime(customers["signup_date"]).dt.to_period("M").dt.to_timestamp()
    churn_history = customers.groupby("signup_month", as_index=False).agg(churn_rate=("churn_label", "mean"), customers=("churn_label", "size"))
    churn_forecast = _forecast_frame(churn_history, "signup_month", "churn_rate").rename(
        columns={"signup_month": "forecast_month", "forecast_value": "churn_rate_forecast"}
    )
    churn_forecast["churn_rate_forecast"] = churn_forecast["churn_rate_forecast"].clip(0, 1)
    churn_forecast["forecast_low"] = churn_forecast["forecast_low"].clip(0, 1)
    churn_forecast["forecast_high"] = churn_forecast["forecast_high"].clip(0, 1)

    top_categories = orders.groupby("category")["net_revenue"].sum().nlargest(8).index
    category_rows: list[pd.DataFrame] = []
    for category, frame in orders.loc[orders["category"].isin(top_categories)].groupby("category"):
        category_monthly = frame.groupby("month_start", as_index=False).agg(net_revenue=("net_revenue", "sum"), orders=("customer_id", "size"))
        forecast = _forecast_frame(category_monthly, "month_start", "net_revenue")
        forecast["category"] = category
        category_rows.append(forecast)
    category_forecast = pd.concat(category_rows, ignore_index=True).rename(columns={"forecast_value": "category_revenue_forecast"})

    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv", usecols=["customer_id", "acquisition_cohort", "predicted_12m_clv"])
    segments = pd.read_csv(project_config.mart_dir / "mart_customer_segments.csv", usecols=["customer_id", "segment_name"])
    clv = clv.merge(segments, on="customer_id", how="left")
    clv["cohort_month"] = _period_start(clv["acquisition_cohort"])
    segment_rows: list[pd.DataFrame] = []
    for segment, frame in clv.groupby("segment_name"):
        history = frame.groupby("cohort_month", as_index=False).agg(avg_predicted_clv=("predicted_12m_clv", "mean"))
        forecast = _forecast_frame(history, "cohort_month", "avg_predicted_clv")
        forecast["segment_name"] = segment
        segment_rows.append(forecast)
    segment_clv_forecast = pd.concat(segment_rows, ignore_index=True).rename(
        columns={"cohort_month": "forecast_month", "forecast_value": "avg_predicted_clv_forecast"}
    )

    write_csv(revenue_forecast, project_config.export_dir / "revenue_profit_forecast.csv")
    write_csv(churn_forecast, project_config.export_dir / "churn_forecast.csv")
    write_csv(category_forecast, project_config.export_dir / "category_demand_forecast.csv")
    write_csv(segment_clv_forecast, project_config.export_dir / "segment_clv_forecast.csv")
    _write_report(revenue_forecast, churn_forecast, category_forecast, segment_clv_forecast, project_config)
    return {
        "revenue": revenue_forecast,
        "churn": churn_forecast,
        "category": category_forecast,
        "segment_clv": segment_clv_forecast,
    }


def _write_report(
    revenue: pd.DataFrame,
    churn: pd.DataFrame,
    category: pd.DataFrame,
    segment_clv: pd.DataFrame,
    project_config: ProjectConfig,
) -> None:
    top_category = category.sort_values("category_revenue_forecast", ascending=False).iloc[0]
    best_segment = segment_clv.sort_values("avg_predicted_clv_forecast", ascending=False).iloc[0]
    lines = [
        "# Forecasting Report",
        "",
        f"- Next-month revenue forecast: ${revenue.iloc[0]['revenue_forecast']:,.0f}",
        f"- Next-month profit forecast: ${revenue.iloc[0]['profit_forecast']:,.0f}",
        f"- Next-cohort churn forecast: {churn.iloc[0]['churn_rate_forecast']:.1%}",
        f"- Highest forecast category: {top_category['category']} (${top_category['category_revenue_forecast']:,.0f})",
        f"- Highest forecast CLV segment: {best_segment['segment_name']} (${best_segment['avg_predicted_clv_forecast']:,.0f})",
        "",
        "## Planning Use",
        "- Use revenue/profit forecast for executive target setting and monthly KPI variance review.",
        "- Use category forecast to align merchandising, retention offers, and inventory priorities.",
        "- Use segment CLV forecast to decide which acquisition and retention motions deserve budget protection.",
    ]
    write_markdown(lines, project_config.report_dir / "forecasting_report.md")


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Build revenue, churn, category, and CLV forecasts.").parse_args()


def main() -> None:
    parse_args()
    build_forecasts()


if __name__ == "__main__":
    main()
