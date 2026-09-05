from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def _lifecycle_stage(row: pd.Series) -> str:
    if row["customer_age_days"] <= 60 and row["orders"] <= 1:
        return "New customer"
    if row["repeat_purchase_flag"] == 1 and row["recency_days"] <= 90 and row["customer_value_band"] in {"High", "Elite", "VIP"}:
        return "High-value loyal"
    if row["repeat_purchase_flag"] == 1 and row["recency_days"] <= 90:
        return "Active repeat"
    if row["recency_days"] <= 120:
        return "Warming risk"
    if row["recency_days"] <= 240:
        return "At risk"
    return "Dormant or lost"


def build_retention_lifecycle(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    orders = pd.read_csv(
        project_config.mart_dir / "fact_orders.csv",
        usecols=["customer_id", "order_date", "order_month", "category", "net_revenue", "is_completed_order", "acquisition_channel"],
        parse_dates=["order_date"],
    )
    orders = orders.loc[orders["is_completed_order"].astype(bool)].sort_values(["customer_id", "order_date"]).copy()
    order_rank = orders.groupby("customer_id").cumcount() + 1
    ranked = orders.assign(order_rank=order_rank)
    first_second = ranked.loc[ranked["order_rank"].isin([1, 2])].pivot_table(
        index="customer_id",
        columns="order_rank",
        values="order_date",
        aggfunc="first",
    )
    first_second.columns = ["first_order_date" if col == 1 else "second_order_date" for col in first_second.columns]
    first_second = first_second.reset_index()
    first_second["time_to_second_purchase_days"] = (
        first_second["second_order_date"] - first_second["first_order_date"]
    ).dt.days
    first_meta = ranked.loc[ranked["order_rank"].eq(1), ["customer_id", "category", "acquisition_channel"]].rename(
        columns={"category": "first_product_category"}
    )
    time_to_second = first_second.merge(first_meta, on="customer_id", how="left")
    time_to_second["second_purchase_within_60d"] = time_to_second["time_to_second_purchase_days"].le(60).fillna(False)

    buckets = [0, 7, 14, 30, 60, 90, 180, 365]
    rows = []
    total = len(time_to_second)
    for day in buckets:
        repeated_by_day = time_to_second["time_to_second_purchase_days"].le(day).sum()
        rows.append(
            {
                "day": day,
                "customers": total,
                "repeat_customers_by_day": repeated_by_day,
                "repeat_rate_by_day": repeated_by_day / total if total else 0,
                "survival_rate_no_second_purchase": 1 - (repeated_by_day / total if total else 0),
            }
        )
    survival = pd.DataFrame(rows)

    first_60 = (
        time_to_second.groupby(["acquisition_channel", "first_product_category"], as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            second_purchase_60d_rate=("second_purchase_within_60d", "mean"),
            median_days_to_second_purchase=("time_to_second_purchase_days", "median"),
        )
        .sort_values(["customers", "second_purchase_60d_rate"], ascending=[False, False])
    )

    customers = pd.read_csv(
        project_config.processed_dir / "customer_features.csv",
        usecols=[
            "customer_id",
            "orders",
            "repeat_purchase_flag",
            "recency_days",
            "customer_age_days",
            "customer_value_band",
            "top_purchase_category",
            "acquisition_channel",
            "historical_clv",
            "return_rate",
        ],
    )
    customers["lifecycle_stage"] = customers.apply(_lifecycle_stage, axis=1)
    customers["recommended_transition"] = np.select(
        [
            customers["lifecycle_stage"].eq("New customer"),
            customers["lifecycle_stage"].eq("Warming risk"),
            customers["lifecycle_stage"].eq("At risk"),
            customers["lifecycle_stage"].eq("Dormant or lost"),
            customers["lifecycle_stage"].eq("High-value loyal"),
        ],
        [
            "Move to second purchase within 60 days",
            "Re-engage before 120-day inactivity",
            "Win back with margin-aware offer",
            "Suppress broad discounting; test low-cost reactivation",
            "Protect value with loyalty benefits",
        ],
        default="Nurture to next category",
    )
    stage_summary = (
        customers.groupby(["lifecycle_stage", "recommended_transition"], as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            avg_historical_clv=("historical_clv", "mean"),
            avg_recency_days=("recency_days", "mean"),
            avg_return_rate=("return_rate", "mean"),
        )
        .sort_values("customers", ascending=False)
    )

    write_csv(time_to_second, project_config.export_dir / "time_to_second_purchase.csv")
    write_csv(survival, project_config.export_dir / "retention_survival_curve.csv")
    write_csv(first_60, project_config.export_dir / "first_60_day_retention_journey.csv")
    write_csv(stage_summary, project_config.export_dir / "lifecycle_stage_transitions.csv")
    write_csv(customers, project_config.mart_dir / "mart_retention_lifecycle.csv")
    _write_report(survival, first_60, stage_summary, project_config)
    return {"time_to_second": time_to_second, "survival": survival, "first_60": first_60, "stages": stage_summary}


def _write_report(survival: pd.DataFrame, first_60: pd.DataFrame, stages: pd.DataFrame, project_config: ProjectConfig) -> None:
    sixty_day = survival.loc[survival["day"].eq(60)].iloc[0]
    top_path = first_60.iloc[0]
    lines = [
        "# Retention Lifecycle Report",
        "",
        f"- Second-purchase conversion by day 60: {sixty_day['repeat_rate_by_day']:.1%}",
        f"- Customers still waiting for second purchase at day 60: {sixty_day['survival_rate_no_second_purchase']:.1%}",
        f"- Largest first-60-day path: {top_path['acquisition_channel']} / {top_path['first_product_category']}",
        "",
        "## Lifecycle Stage Summary",
        "| Stage | Recommended Transition | Customers | Avg CLV | Avg Recency | Avg Return Rate |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in stages.to_dict("records"):
        lines.append(
            f"| {row['lifecycle_stage']} | {row['recommended_transition']} | {row['customers']:,.0f} | "
            f"${row['avg_historical_clv']:,.0f} | {row['avg_recency_days']:.0f} | {row['avg_return_rate']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Business Use",
            "- Treat the first 60 days as the activation window for repeat purchase conversion.",
            "- Separate warming-risk customers from dormant customers so retention spend is not applied too late.",
            "- Track lifecycle stage mix as an operating KPI alongside churn, retention, and CLV.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "retention_lifecycle_report.md")


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Build advanced retention lifecycle outputs.").parse_args()


def main() -> None:
    parse_args()
    build_retention_lifecycle()


if __name__ == "__main__":
    main()
