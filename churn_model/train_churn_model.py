from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


CHURN_FEATURES = [
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
    "days_since_engagement",
    "days_since_session",
    "customer_age_days",
    "product_diversity",
    "channel_diversity",
    "support_cases",
]


def _risk_tier(probability: pd.Series) -> pd.Series:
    return pd.cut(
        probability,
        bins=[-0.001, 0.25, 0.50, 0.75, 1.0],
        labels=["Low", "Medium", "High", "Critical"],
    ).astype(str)


def train_churn_model(project_config: ProjectConfig = CONFIG) -> dict[str, object]:
    project_config.ensure_directories()
    base = pd.read_csv(project_config.processed_dir / "churn_model_base.csv")
    customer_features = pd.read_csv(project_config.processed_dir / "customer_features.csv")
    X = base[CHURN_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = base["churn_label"].astype(int)

    if y.nunique() < 2:
        base["churn_probability"] = np.where(base["recency_days"].gt(120), 0.85, 0.15)
        metrics = {
            "precision": None,
            "recall": None,
            "roc_auc": None,
            "confusion_matrix": None,
            "note": "Only one target class was present; rule-based fallback probabilities were used.",
        }
        model = None
        feature_importance = pd.DataFrame({"feature": CHURN_FEATURES, "importance": 0.0})
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.25,
            random_state=42,
            stratify=y,
        )
        model = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs"),
                ),
            ]
        )
        model.fit(X_train, y_train)
        probabilities = model.predict_proba(X_test)[:, 1]
        predictions = (probabilities >= 0.50).astype(int)
        metrics = {
            "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
            "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
            "test_rows": int(len(X_test)),
            "positive_rate": round(float(y.mean()), 4),
        }
        base["churn_probability"] = model.predict_proba(X)[:, 1]
        coefficients = model.named_steps["model"].coef_[0]
        feature_importance = (
            pd.DataFrame(
                {
                    "feature": CHURN_FEATURES,
                    "coefficient": coefficients,
                    "importance": np.abs(coefficients),
                    "direction": np.where(coefficients >= 0, "Increases churn risk", "Reduces churn risk"),
                }
            )
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        joblib.dump(model, project_config.model_dir / "churn_model.joblib")

    scored = base[["customer_id", "churn_probability"]].copy()
    scored["churn_risk_tier"] = _risk_tier(scored["churn_probability"])
    scored = scored.merge(
        customer_features[
            [
                "customer_id",
                "acquisition_channel",
                "loyalty_tier",
                "top_purchase_category",
                "orders",
                "net_revenue",
                "return_adjusted_profit",
                "recency_days",
                "engagement_score",
                "return_rate",
                "discount_dependency",
                "historical_clv",
                "churn_label",
            ]
        ],
        on="customer_id",
        how="left",
    )
    scored["expected_profit_at_risk"] = scored["churn_probability"] * scored["return_adjusted_profit"].clip(lower=0)

    at_risk = scored.loc[scored["churn_risk_tier"].isin(["High", "Critical"])].sort_values(
        ["expected_profit_at_risk", "churn_probability"],
        ascending=False,
    )
    driver_summary = feature_importance.head(12).copy()
    driver_summary["business_interpretation"] = driver_summary.apply(_driver_interpretation, axis=1)

    write_csv(scored, project_config.mart_dir / "mart_churn_risk.csv")
    write_csv(at_risk, project_config.export_dir / "at_risk_customers.csv")
    write_csv(driver_summary, project_config.export_dir / "churn_driver_summary.csv")
    (project_config.model_dir / "churn_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _write_model_report(metrics, driver_summary, project_config)

    return {
        "scored": scored,
        "at_risk": at_risk,
        "driver_summary": driver_summary,
        "metrics": metrics,
        "model": model,
    }


def _driver_interpretation(row: pd.Series) -> str:
    explanations = {
        "recency_days": "Longer time since last purchase is a direct churn warning.",
        "orders": "Higher purchase count usually indicates stronger relationship depth.",
        "net_revenue": "Customer value changes the priority and risk economics of retention outreach.",
        "return_adjusted_profit": "Profitability helps distinguish valuable churn risk from low-value risk.",
        "avg_order_value": "Order size indicates the value of retaining the customer.",
        "purchase_frequency_30d": "Frequent purchasing behavior indicates habit formation.",
        "discount_dependency": "High promo dependency may signal weak full-price loyalty.",
        "return_rate": "Returns can indicate product fit, experience, or quality issues.",
        "sessions": "Site activity indicates current intent even before purchase.",
        "bounce_rate": "Bounces can signal low engagement or acquisition mismatch.",
        "engagement_score": "Email and campaign engagement indicate retention reachability.",
        "days_since_engagement": "A long engagement gap weakens retention intervention effectiveness.",
    }
    return explanations.get(row["feature"], "Behavioral signal used in churn risk scoring.")


def _write_model_report(metrics: dict[str, object], driver_summary: pd.DataFrame, project_config: ProjectConfig) -> None:
    lines = [
        "# Churn Model Report",
        "",
        "The churn model estimates the probability that a customer is inactive or likely to lapse based on purchase, engagement, return, session, discount, and tenure behavior.",
        "",
        "## Evaluation",
    ]
    for key, value in metrics.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Top Churn Drivers"])
    for row in driver_summary.to_dict("records"):
        lines.append(f"- `{row['feature']}`: {row.get('direction', 'Signal')} - {row['business_interpretation']}")
    lines.extend(
        [
            "",
            "## Explainability Notes",
            "- Logistic regression is used for transparent coefficient-based interpretation.",
            "- Risk tiers are exported as governed reporting fields for BI filtering and retention operations.",
            "- Expected profit at risk prioritizes retention efforts by combining churn probability with return-adjusted profit.",
        ]
    )
    write_markdown(lines, project_config.report_dir / "churn_model_report.md")


def main() -> None:
    train_churn_model()


if __name__ == "__main__":
    main()

