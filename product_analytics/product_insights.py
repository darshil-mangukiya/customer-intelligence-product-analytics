from __future__ import annotations

from itertools import combinations

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def run_product_analytics(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    transactions = pd.read_csv(project_config.processed_dir / "transactions_enriched.csv", parse_dates=["order_date"])
    product_features = pd.read_csv(project_config.processed_dir / "product_features.csv")

    top_revenue = product_features.sort_values("net_revenue", ascending=False).head(100)
    low_margin_high_volume = product_features.loc[
        (product_features["orders"] >= product_features["orders"].quantile(0.75))
        & (product_features["return_adjusted_margin"] <= product_features["return_adjusted_margin"].quantile(0.35))
    ].sort_values(["orders", "return_adjusted_margin"], ascending=[False, True])
    return_heavy = product_features.loc[product_features["return_rate"] >= product_features["return_rate"].quantile(0.90)].sort_values("return_rate", ascending=False)

    category_profitability = (
        transactions.groupby("category")
        .agg(
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            units=("quantity", "sum"),
            net_revenue=("net_revenue", "sum"),
            return_adjusted_profit=("return_adjusted_profit", "sum"),
            returns=("return_flag", "sum"),
            discount_amount=("discount_amount", "sum"),
        )
        .reset_index()
    )
    category_profitability["return_rate"] = category_profitability["returns"] / category_profitability["orders"]
    category_profitability["return_adjusted_margin"] = category_profitability["return_adjusted_profit"] / category_profitability["net_revenue"].replace(0, pd.NA)
    category_profitability["discount_dependency"] = category_profitability["discount_amount"] / (
        category_profitability["discount_amount"] + category_profitability["net_revenue"]
    ).replace(0, pd.NA)
    category_profitability = category_profitability.fillna(0).sort_values("return_adjusted_profit", ascending=False)

    lifecycle = (
        product_features.groupby(["category", "lifecycle_stage"])
        .agg(products=("product_id", "nunique"), revenue=("net_revenue", "sum"), profit=("return_adjusted_profit", "sum"), return_rate=("return_rate", "mean"))
        .reset_index()
    )
    retention_drivers = product_features.sort_values(["repeat_customer_rate", "return_adjusted_profit"], ascending=False).head(100)
    churn_linked_products = product_features.sort_values(["return_rate", "discount_dependency"], ascending=False).head(100)
    affinity = _build_category_affinity(transactions)
    product_affinity = _build_product_affinity(transactions)

    write_csv(top_revenue, project_config.export_dir / "top_revenue_products.csv")
    write_csv(low_margin_high_volume, project_config.export_dir / "low_margin_high_volume_products.csv")
    write_csv(return_heavy, project_config.export_dir / "return_heavy_products.csv")
    write_csv(category_profitability, project_config.mart_dir / "mart_category_profitability.csv")
    write_csv(lifecycle, project_config.export_dir / "product_lifecycle_analysis.csv")
    write_csv(retention_drivers, project_config.mart_dir / "mart_retention_drivers.csv")
    write_csv(churn_linked_products, project_config.export_dir / "products_associated_with_churn_risk.csv")
    write_csv(affinity, project_config.mart_dir / "mart_product_affinity.csv")
    write_csv(product_affinity, project_config.export_dir / "product_pair_affinity.csv")
    _write_product_report(category_profitability, low_margin_high_volume, return_heavy, affinity, project_config)

    return {
        "top_revenue": top_revenue,
        "low_margin_high_volume": low_margin_high_volume,
        "return_heavy": return_heavy,
        "category_profitability": category_profitability,
        "lifecycle": lifecycle,
        "retention_drivers": retention_drivers,
        "affinity": affinity,
        "product_affinity": product_affinity,
    }


def _build_category_affinity(transactions: pd.DataFrame) -> pd.DataFrame:
    customer_categories = transactions.groupby("customer_id")["category"].agg(lambda s: sorted(set(s.dropna()))).reset_index()
    total_customers = len(customer_categories)
    category_customer_counts = transactions.groupby("category")["customer_id"].nunique().to_dict()

    pair_counts: dict[tuple[str, str], int] = {}
    for categories in customer_categories["category"]:
        for source, target in combinations(categories, 2):
            pair_counts[(source, target)] = pair_counts.get((source, target), 0) + 1
            pair_counts[(target, source)] = pair_counts.get((target, source), 0) + 1

    rows = []
    for (source, target), both_customers in pair_counts.items():
        source_customers = category_customer_counts.get(source, 0)
        target_customers = category_customer_counts.get(target, 0)
        confidence = both_customers / source_customers if source_customers else 0
        target_base_rate = target_customers / total_customers if total_customers else 0
        lift = confidence / target_base_rate if target_base_rate else 0
        rows.append(
            {
                "source_category": source,
                "target_category": target,
                "both_customers": both_customers,
                "source_customers": source_customers,
                "target_customers": target_customers,
                "confidence": confidence,
                "lift": lift,
                "affinity_score": confidence * lift,
            }
        )
    return pd.DataFrame(rows).sort_values("affinity_score", ascending=False)


def _build_product_affinity(transactions: pd.DataFrame) -> pd.DataFrame:
    top_products = set(transactions["product_id"].value_counts().head(120).index)
    top_tx = transactions.loc[transactions["product_id"].isin(top_products)]
    customer_products = top_tx.groupby("customer_id")["product_id"].agg(lambda s: sorted(set(s))).reset_index()
    product_counts = top_tx.groupby("product_id")["customer_id"].nunique().to_dict()
    total_customers = top_tx["customer_id"].nunique()

    pair_counts: dict[tuple[str, str], int] = {}
    for products in customer_products["product_id"]:
        for source, target in combinations(products[:12], 2):
            pair_counts[(source, target)] = pair_counts.get((source, target), 0) + 1
            pair_counts[(target, source)] = pair_counts.get((target, source), 0) + 1

    rows = []
    for (source, target), both_customers in pair_counts.items():
        source_customers = product_counts.get(source, 0)
        target_customers = product_counts.get(target, 0)
        confidence = both_customers / source_customers if source_customers else 0
        target_base_rate = target_customers / total_customers if total_customers else 0
        lift = confidence / target_base_rate if target_base_rate else 0
        rows.append(
            {
                "source_product_id": source,
                "target_product_id": target,
                "both_customers": both_customers,
                "confidence": confidence,
                "lift": lift,
                "affinity_score": confidence * lift,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["source_product_id", "target_product_id", "both_customers", "confidence", "lift", "affinity_score"])
    return pd.DataFrame(rows).sort_values("affinity_score", ascending=False).head(500)


def _write_product_report(
    category_profitability: pd.DataFrame,
    low_margin_high_volume: pd.DataFrame,
    return_heavy: pd.DataFrame,
    affinity: pd.DataFrame,
    project_config: ProjectConfig,
) -> None:
    top_category = category_profitability.head(1)
    leakage_category = category_profitability.sort_values("return_rate", ascending=False).head(1)
    lines = [
        "# Product Analytics Summary",
        "",
    ]
    if len(top_category):
        row = top_category.iloc[0]
        lines.append(f"- Most profitable category: {row['category']} with ${row['return_adjusted_profit']:,.0f} return-adjusted profit.")
    if len(leakage_category):
        row = leakage_category.iloc[0]
        lines.append(f"- Highest return-rate category: {row['category']} at {row['return_rate']:.1%}.")
    lines.extend(
        [
            f"- Low-margin high-volume products identified: {len(low_margin_high_volume):,}.",
            f"- Return-heavy products identified: {len(return_heavy):,}.",
        ]
    )
    if len(affinity):
        top_pair = affinity.iloc[0]
        lines.append(
            f"- Strongest category cross-sell path: {top_pair['source_category']} to {top_pair['target_category']} with {top_pair['lift']:.2f}x lift."
        )
    lines.extend(
        [
            "",
            "## Business Use",
            "- Use return-adjusted profit instead of gross sales for merchandising decisions.",
            "- Prioritize product fixes where high unit volume combines with weak margin or heavy returns.",
            "- Use affinity scores to build cross-sell modules and bundle tests.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "product_analytics_summary.md")


def main() -> None:
    run_product_analytics()


if __name__ == "__main__":
    main()

