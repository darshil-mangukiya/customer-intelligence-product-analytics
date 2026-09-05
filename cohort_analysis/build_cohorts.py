from __future__ import annotations

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def run_cohort_analysis(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    cohort_base = pd.read_csv(project_config.processed_dir / "cohort_base.csv")
    cohort_base = cohort_base.loc[cohort_base["cohort_index"].between(0, 12)].copy()

    retention = (
        cohort_base.groupby(["cohort_month", "cohort_index"])
        .agg(
            active_customers=("customer_id", "nunique"),
            orders=("order_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
            profit=("return_adjusted_profit", "sum"),
        )
        .reset_index()
    )
    base = retention.loc[retention["cohort_index"].eq(0), ["cohort_month", "active_customers", "net_revenue"]].rename(
        columns={"active_customers": "cohort_size", "net_revenue": "month_0_revenue"}
    )
    retention = retention.merge(base, on="cohort_month", how="left")
    retention["retention_rate"] = retention["active_customers"] / retention["cohort_size"]
    retention["revenue_retention_rate"] = retention["net_revenue"] / retention["month_0_revenue"].replace(0, pd.NA)
    retention["revenue_retention_rate"] = retention["revenue_retention_rate"].fillna(0)

    heatmap = (
        retention.pivot_table(index="cohort_month", columns="cohort_index", values="retention_rate", fill_value=0)
        .reindex(columns=list(range(13)), fill_value=0)
        .reset_index()
    )
    heatmap.columns = ["cohort_month"] + [f"month_{i}" for i in range(13)]

    revenue_decay = (
        retention.pivot_table(index="cohort_month", columns="cohort_index", values="revenue_retention_rate", fill_value=0)
        .reindex(columns=list(range(13)), fill_value=0)
        .reset_index()
    )
    revenue_decay.columns = ["cohort_month"] + [f"month_{i}" for i in range(13)]

    channel_retention = _retention_by_dimension(cohort_base, "acquisition_channel")
    category_retention = _retention_by_dimension(cohort_base, "first_product_category")

    write_csv(retention, project_config.mart_dir / "mart_cohort_retention.csv")
    write_csv(heatmap, project_config.export_dir / "cohort_retention_heatmap.csv")
    write_csv(revenue_decay, project_config.export_dir / "cohort_revenue_decay.csv")
    write_csv(channel_retention, project_config.export_dir / "retention_by_acquisition_channel.csv")
    write_csv(category_retention, project_config.export_dir / "retention_by_first_product_category.csv")
    _write_cohort_report(retention, channel_retention, category_retention, project_config)
    _write_heatmap_png(heatmap, project_config)
    return {
        "retention": retention,
        "heatmap": heatmap,
        "revenue_decay": revenue_decay,
        "channel_retention": channel_retention,
        "category_retention": category_retention,
    }


def _retention_by_dimension(cohort_base: pd.DataFrame, dimension: str) -> pd.DataFrame:
    grouped = (
        cohort_base.groupby([dimension, "cohort_index"])
        .agg(active_customers=("customer_id", "nunique"), net_revenue=("net_revenue", "sum"))
        .reset_index()
    )
    base = grouped.loc[grouped["cohort_index"].eq(0), [dimension, "active_customers", "net_revenue"]].rename(
        columns={"active_customers": "base_customers", "net_revenue": "base_revenue"}
    )
    grouped = grouped.merge(base, on=dimension, how="left")
    grouped["retention_rate"] = grouped["active_customers"] / grouped["base_customers"].replace(0, pd.NA)
    grouped["revenue_retention_rate"] = grouped["net_revenue"] / grouped["base_revenue"].replace(0, pd.NA)
    return grouped.fillna(0)


def _write_heatmap_png(heatmap: pd.DataFrame, project_config: ProjectConfig) -> None:
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except Exception:
        return

    if heatmap.empty:
        return
    plot_data = heatmap.set_index("cohort_month")
    plt.figure(figsize=(13, max(5, len(plot_data) * 0.28)))
    sns.heatmap(plot_data, annot=False, cmap="YlGnBu", vmin=0, vmax=1, cbar_kws={"label": "Retention Rate"})
    plt.title("Monthly Customer Retention by Acquisition Cohort")
    plt.xlabel("Months Since First Purchase")
    plt.ylabel("Cohort Month")
    plt.tight_layout()
    plt.savefig(project_config.report_dir / "cohort_retention_heatmap.png", dpi=180)
    plt.close()


def _write_cohort_report(
    retention: pd.DataFrame,
    channel_retention: pd.DataFrame,
    category_retention: pd.DataFrame,
    project_config: ProjectConfig,
) -> None:
    month_1 = retention.loc[retention["cohort_index"].eq(1), "retention_rate"].mean()
    month_3 = retention.loc[retention["cohort_index"].eq(3), "retention_rate"].mean()
    month_6 = retention.loc[retention["cohort_index"].eq(6), "retention_rate"].mean()
    best_channel = (
        channel_retention.loc[channel_retention["cohort_index"].eq(3)]
        .sort_values("retention_rate", ascending=False)
        .head(1)
    )
    best_category = (
        category_retention.loc[category_retention["cohort_index"].eq(3)]
        .sort_values("retention_rate", ascending=False)
        .head(1)
    )
    lines = [
        "# Cohort Analysis Summary",
        "",
        f"- Average Month 1 retention: {month_1:.1%}",
        f"- Average Month 3 retention: {month_3:.1%}",
        f"- Average Month 6 retention: {month_6:.1%}",
    ]
    if len(best_channel):
        row = best_channel.iloc[0]
        lines.append(f"- Best Month 3 acquisition channel: {row['acquisition_channel']} at {row['retention_rate']:.1%}")
    if len(best_category):
        row = best_category.iloc[0]
        lines.append(f"- Best Month 3 first product category: {row['first_product_category']} at {row['retention_rate']:.1%}")
    lines.extend(
        [
            "",
            "## Business Use",
            "- Compare first-purchase cohorts to diagnose onboarding quality and product-market fit.",
            "- Slice retention by acquisition channel to identify low-LTV acquisition sources.",
            "- Slice retention by first category to identify products that create durable repeat behavior.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "cohort_analysis_summary.md")


def main() -> None:
    run_cohort_analysis()


if __name__ == "__main__":
    main()

