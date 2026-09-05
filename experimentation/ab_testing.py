from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


@dataclass(frozen=True)
class ExperimentResult:
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float
    z_statistic: float
    p_value: float


def _stable_uniform(values: pd.Series, salt: str) -> pd.Series:
    hashed = pd.util.hash_pandas_object(values.astype(str) + salt, index=False).astype("uint64")
    return (hashed % 1_000_000) / 1_000_000


def _normal_cdf(value: float) -> float:
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def _z_test_proportions(control_success: int, control_n: int, treatment_success: int, treatment_n: int) -> ExperimentResult:
    control_rate = control_success / control_n if control_n else 0
    treatment_rate = treatment_success / treatment_n if treatment_n else 0
    pooled = (control_success + treatment_success) / (control_n + treatment_n) if control_n + treatment_n else 0
    standard_error = math.sqrt(max(pooled * (1 - pooled) * ((1 / max(control_n, 1)) + (1 / max(treatment_n, 1))), 1e-12))
    z_statistic = (treatment_rate - control_rate) / standard_error
    p_value = 2 * (1 - _normal_cdf(abs(z_statistic)))
    absolute_lift = treatment_rate - control_rate
    relative_lift = absolute_lift / control_rate if control_rate else 0
    return ExperimentResult(control_rate, treatment_rate, absolute_lift, relative_lift, z_statistic, p_value)


def build_retention_experiment(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    churn = pd.read_csv(project_config.mart_dir / "mart_churn_risk.csv")
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv", usecols=["customer_id", "predicted_12m_clv", "clv_band"])
    segments = pd.read_csv(project_config.mart_dir / "mart_customer_segments.csv", usecols=["customer_id", "segment_name"])

    population = (
        churn.merge(clv, on="customer_id", how="left")
        .merge(segments, on="customer_id", how="left")
        .loc[lambda frame: frame["churn_risk_tier"].isin(["High", "Critical"])]
        .copy()
    )
    population["variant"] = np.where(_stable_uniform(population["customer_id"], "assignment") < 0.5, "Control", "Retention Offer")
    clv_rank = population["predicted_12m_clv"].rank(pct=True).fillna(0.5)
    population["baseline_conversion_probability"] = (
        0.035
        + (1 - population["churn_probability"].clip(0, 1)) * 0.16
        + clv_rank * 0.04
        - population["return_rate"].fillna(0).clip(0, 1) * 0.02
    ).clip(0.01, 0.35)
    population["treatment_uplift_probability"] = np.where(
        population["churn_risk_tier"].eq("High"),
        0.045,
        0.027,
    ) + np.where(population["clv_band"].isin(["Elite", "Platinum"]), 0.018, 0.006)
    population["conversion_probability"] = population["baseline_conversion_probability"] + np.where(
        population["variant"].eq("Retention Offer"),
        population["treatment_uplift_probability"],
        0,
    )
    population["converted"] = _stable_uniform(population["customer_id"], "outcome") < population["conversion_probability"].clip(0.01, 0.50)
    population["retained_value_proxy"] = (
        population["expected_profit_at_risk"].fillna(0) * 0.35
        + population["predicted_12m_clv"].fillna(0) * 0.12
    )
    population["treatment_cost"] = np.where(population["variant"].eq("Retention Offer"), np.where(population["clv_band"].isin(["Elite", "Platinum"]), 8.0, 3.5), 0.0)
    population["incremental_profit_proxy"] = np.where(
        population["converted"],
        population["retained_value_proxy"],
        0,
    ) - population["treatment_cost"]

    summary = (
        population.groupby("variant", as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            conversions=("converted", "sum"),
            conversion_rate=("converted", "mean"),
            avg_churn_probability=("churn_probability", "mean"),
            avg_predicted_clv=("predicted_12m_clv", "mean"),
            total_profit_proxy=("incremental_profit_proxy", "sum"),
            avg_profit_proxy=("incremental_profit_proxy", "mean"),
        )
        .sort_values("variant")
    )
    control = summary.loc[summary["variant"].eq("Control")].iloc[0]
    treatment = summary.loc[summary["variant"].eq("Retention Offer")].iloc[0]
    stats = _z_test_proportions(int(control["conversions"]), int(control["customers"]), int(treatment["conversions"]), int(treatment["customers"]))

    group = ["segment_name", "churn_risk_tier", "clv_band", "variant"]
    segment = (
        population.groupby(group, as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            conversions=("converted", "sum"),
            conversion_rate=("converted", "mean"),
            avg_profit_proxy=("incremental_profit_proxy", "mean"),
            total_profit_proxy=("incremental_profit_proxy", "sum"),
        )
    )
    pivot = segment.pivot_table(
        index=["segment_name", "churn_risk_tier", "clv_band"],
        columns="variant",
        values=["conversion_rate", "avg_profit_proxy", "customers"],
        aggfunc="first",
    )
    pivot.columns = ["_".join(col).lower().replace(" ", "_") for col in pivot.columns]
    uplift = pivot.reset_index()
    uplift["absolute_lift"] = uplift.get("conversion_rate_retention_offer", 0) - uplift.get("conversion_rate_control", 0)
    uplift["profit_lift_per_customer"] = uplift.get("avg_profit_proxy_retention_offer", 0) - uplift.get("avg_profit_proxy_control", 0)
    uplift = uplift.sort_values(["profit_lift_per_customer", "absolute_lift"], ascending=False)

    write_csv(population, project_config.export_dir / "ab_test_customer_assignments.csv")
    write_csv(summary, project_config.export_dir / "ab_test_summary.csv")
    write_csv(uplift, project_config.export_dir / "uplift_by_segment.csv")
    _write_report(summary, uplift, stats, project_config)
    return {"assignments": population, "summary": summary, "uplift": uplift}


def _write_report(summary: pd.DataFrame, uplift: pd.DataFrame, stats: ExperimentResult, project_config: ProjectConfig) -> None:
    control_profit = summary.loc[summary["variant"].eq("Control"), "avg_profit_proxy"].iloc[0]
    treatment_profit = summary.loc[summary["variant"].eq("Retention Offer"), "avg_profit_proxy"].iloc[0]
    treatment_wins = stats.absolute_lift > 0 and stats.p_value < 0.05 and treatment_profit > control_profit
    recommendation = (
        "Scale the retention offer to high-profit uplift segments, with holdouts for ongoing measurement."
        if treatment_wins
        else "Do not blanket-roll out; target only segments with positive profit lift and keep holdouts."
    )
    lines = [
        "# Retention Campaign Experiment Report",
        "",
        "## Executive Readout",
        f"- Control conversion rate: {stats.control_rate:.2%}",
        f"- Treatment conversion rate: {stats.treatment_rate:.2%}",
        f"- Absolute lift: {stats.absolute_lift:.2%}",
        f"- Relative lift: {stats.relative_lift:.1%}",
        f"- Z-statistic: {stats.z_statistic:.2f}",
        f"- P-value: {stats.p_value:.4f}",
        f"- Recommendation: {recommendation}",
        "",
        "## Variant Summary",
        "| Variant | Customers | Conversions | Conversion Rate | Avg Predicted CLV | Avg Profit Proxy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['variant']} | {row['customers']:,.0f} | {row['conversions']:,.0f} | "
            f"{row['conversion_rate']:.2%} | ${row['avg_predicted_clv']:,.0f} | ${row['avg_profit_proxy']:,.2f} |"
        )
    lines.extend(["", "## Top Uplift Segments", "| Segment | Risk | CLV Band | Absolute Lift | Profit Lift / Customer |", "|---|---|---|---:|---:|"])
    for row in uplift.head(8).to_dict("records"):
        lines.append(
            f"| {row['segment_name']} | {row['churn_risk_tier']} | {row['clv_band']} | "
            f"{row['absolute_lift']:.2%} | ${row['profit_lift_per_customer']:,.2f} |"
        )
    write_markdown(lines, project_config.report_dir / "experimentation_report.md")


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Build retention campaign A/B test and uplift outputs.").parse_args()


def main() -> None:
    parse_args()
    build_retention_experiment()


if __name__ == "__main__":
    main()
