from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv


ACTIVATION_COLUMNS = [
    "customer_id",
    "segment",
    "churn_probability",
    "clv_band",
    "recommended_action",
    "recommended_product_category",
    "priority_score",
    "campaign_reason",
]


def _read_optional(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    return pd.read_csv(path, usecols=columns)


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _score_base(project_config: ProjectConfig) -> pd.DataFrame:
    churn = _read_optional(project_config.mart_dir / "mart_churn_risk.csv")
    clv = _read_optional(project_config.mart_dir / "mart_clv.csv")
    segments = _read_optional(project_config.mart_dir / "mart_customer_segments.csv")
    actions = _read_optional(project_config.export_dir / "next_best_actions.csv")

    if churn.empty:
        return pd.DataFrame(columns=ACTIVATION_COLUMNS)

    base = churn.copy()
    clv_cols = [
        col
        for col in ["customer_id", "predicted_12m_clv", "clv_band", "expected_clv_at_risk", "acquisition_channel", "loyalty_tier"]
        if col in clv.columns
    ]
    if clv_cols:
        base = base.merge(clv[clv_cols], on="customer_id", how="left", suffixes=("", "_clv"))

    segment_cols = [col for col in ["customer_id", "segment_name", "business_recommendation"] if col in segments.columns]
    if segment_cols:
        base = base.merge(segments[segment_cols], on="customer_id", how="left")

    action_cols = [
        col
        for col in ["customer_id", "recommended_category", "product_name", "recommended_action", "action_priority_score"]
        if col in actions.columns
    ]
    if action_cols:
        base = base.merge(actions[action_cols].drop_duplicates("customer_id"), on="customer_id", how="left", suffixes=("", "_nba"))

    base["segment"] = base.get("segment_name", pd.Series(index=base.index, dtype=object)).fillna("Unassigned")
    base["clv_band"] = base.get("clv_band", pd.Series(index=base.index, dtype=object)).fillna("Unscored")
    base["recommended_product_category"] = (
        base.get("recommended_category", pd.Series(index=base.index, dtype=object))
        .fillna(base.get("top_purchase_category", pd.Series(index=base.index, dtype=object)))
        .fillna("Lifecycle")
    )
    base["predicted_12m_clv"] = pd.to_numeric(base.get("predicted_12m_clv", 0), errors="coerce").fillna(0)
    base["expected_profit_at_risk"] = pd.to_numeric(base.get("expected_profit_at_risk", 0), errors="coerce").fillna(0)
    base["churn_probability"] = pd.to_numeric(base.get("churn_probability", 0), errors="coerce").fillna(0)
    base["discount_dependency"] = pd.to_numeric(base.get("discount_dependency", 0), errors="coerce").fillna(0)
    base["return_rate"] = pd.to_numeric(base.get("return_rate", 0), errors="coerce").fillna(0)
    base["orders"] = pd.to_numeric(base.get("orders", 0), errors="coerce").fillna(0)
    base["recency_days"] = pd.to_numeric(base.get("recency_days", 999), errors="coerce").fillna(999)
    base["priority_base"] = (
        base["expected_profit_at_risk"].rank(pct=True)
        + base["predicted_12m_clv"].rank(pct=True)
        + base["churn_probability"].rank(pct=True)
    ) / 3
    return base


def _activation_frame(frame: pd.DataFrame, action: str, reason: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=ACTIVATION_COLUMNS)
    output = frame.copy()
    output["recommended_action"] = action
    output["campaign_reason"] = reason
    output["priority_score"] = np.round(output["priority_base"].fillna(0) * 100, 2)
    return output[ACTIVATION_COLUMNS].sort_values("priority_score", ascending=False)


def build_activation_exports(project_config: ProjectConfig = CONFIG, sample_rows: int = 250) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    output_dir = project_config.root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    base = _score_base(project_config)
    if base.empty:
        loyalty_tier = base.get("loyalty_tier", pd.Series(index=base.index, dtype=object)).fillna("Unassigned")
        exports = {
            "activation_churn_campaign.csv": pd.DataFrame(columns=ACTIVATION_COLUMNS),
            "activation_winback_campaign.csv": pd.DataFrame(columns=ACTIVATION_COLUMNS),
            "activation_high_clv_customers.csv": pd.DataFrame(columns=ACTIVATION_COLUMNS),
            "activation_cross_sell_targets.csv": pd.DataFrame(columns=ACTIVATION_COLUMNS),
            "activation_loyalty_upgrade_targets.csv": pd.DataFrame(columns=ACTIVATION_COLUMNS),
            "activation_discount_sensitive_customers.csv": pd.DataFrame(columns=ACTIVATION_COLUMNS),
        }
    else:
        high_clv_threshold = base["predicted_12m_clv"].quantile(0.80)
        discount_threshold = max(0.30, float(base["discount_dependency"].quantile(0.80)))
        loyalty_tier = base.get("loyalty_tier", pd.Series(index=base.index, dtype=object)).fillna("Unassigned")
        exports = {
            "activation_churn_campaign.csv": _activation_frame(
                base.loc[base["churn_risk_tier"].isin(["High", "Critical"]) | base["churn_probability"].ge(0.70)],
                "Retention save journey",
                "High churn probability with measurable profit or CLV at risk.",
            ),
            "activation_winback_campaign.csv": _activation_frame(
                base.loc[base["recency_days"].ge(120) | base["orders"].le(1)],
                "Win-back journey",
                "Customer has lapsed or has not converted beyond the first order.",
            ),
            "activation_high_clv_customers.csv": _activation_frame(
                base.loc[base["predicted_12m_clv"].ge(high_clv_threshold)],
                "VIP retention treatment",
                "Customer is in the top predicted CLV population and should be protected from preventable churn.",
            ),
            "activation_cross_sell_targets.csv": _activation_frame(
                base.loc[base["recommended_product_category"].ne("Lifecycle")],
                "Cross-sell recommendation",
                "Customer has an actionable product or category recommendation from affinity or next-best-action logic.",
            ),
            "activation_loyalty_upgrade_targets.csv": _activation_frame(
                base.loc[base["predicted_12m_clv"].ge(high_clv_threshold) & ~loyalty_tier.isin(["Platinum", "VIP"])],
                "Loyalty upgrade offer",
                "High-value customer is not yet in the highest loyalty tier.",
            ),
            "activation_discount_sensitive_customers.csv": _activation_frame(
                base.loc[base["discount_dependency"].ge(discount_threshold)],
                "Margin-controlled promotion",
                "Customer shows high discount dependency and should receive controlled offers rather than blanket discounts.",
            ),
        }

    manifest_rows = []
    for filename, df in exports.items():
        full_path = project_config.export_dir / filename
        sample_path = output_dir / filename
        write_csv(df, full_path)
        write_csv(df.head(sample_rows), sample_path)
        manifest_rows.append(
            {
                "export_name": filename,
                "full_local_path": _repo_relative(full_path, project_config.root),
                "sample_output_path": _repo_relative(sample_path, project_config.root),
                "rows": len(df),
                "sample_rows": min(len(df), sample_rows),
                "grain": "customer",
                "activation_owner": "Lifecycle Marketing",
            }
        )

    manifest = pd.DataFrame(manifest_rows)
    write_csv(manifest, project_config.export_dir / "activation_export_manifest.csv")
    write_csv(manifest, output_dir / "activation_export_manifest.csv")
    return exports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build activation and reverse-ETL customer exports.")
    parser.add_argument("--sample-rows", type=int, default=250)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_activation_exports(sample_rows=args.sample_rows)


if __name__ == "__main__":
    main()
