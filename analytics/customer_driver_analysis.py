from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from analytics.statistical_analysis import correlation_test, welch_mean_test


DRIVERS = ["orders", "purchase_frequency_30d", "recency_days", "engagement_score", "engagement_rate", "days_since_engagement", "sessions", "return_rate", "discount_dependency", "avg_order_value", "support_cases", "customer_age_days"]


def churn_driver_analysis(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"churn_label", *DRIVERS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"missing churn-driver columns: {missing}")
    data = frame[["churn_label", *DRIVERS]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if data["churn_label"].nunique() != 2:
        raise ValueError("churn_label must contain two groups")
    scaler = StandardScaler()
    x = scaler.fit_transform(data[DRIVERS])
    model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42).fit(x, data["churn_label"])
    coefficients = dict(zip(DRIVERS, model.coef_[0]))
    rows = []
    for driver in DRIVERS:
        retained = data.loc[data["churn_label"].eq(0), driver]
        churned = data.loc[data["churn_label"].eq(1), driver]
        test = welch_mean_test(retained, churned)
        coef = float(coefficients[driver])
        rows.append({"metric_or_driver": driver, "analysis_type": "churn_association", "population": "synthetic customers with complete features", "comparison_group": "churned vs retained", "effect_direction": "higher churn odds" if coef > 0 else "lower churn odds", "effect_size": test.effect_size, "effect_size_name": "Cohen's d", "statistic": test.statistic, "p_value": test.p_value, "confidence_interval_low": test.ci_low, "confidence_interval_high": test.ci_high, "importance_or_strength": abs(coef), "model_standardized_coefficient": coef, "business_interpretation": f"{driver} is associated with {'higher' if coef > 0 else 'lower'} modeled churn odds after controlling for the other numeric drivers.", "recommended_action": f"Monitor {driver} within risk tiers and validate interventions with controlled experiments.", "limitations": "Observational association in synthetic data; not causal."})
    return pd.DataFrame(rows).sort_values("importance_or_strength", ascending=False).reset_index(drop=True)


def clv_driver_analysis(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"historical_clv", *DRIVERS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"missing CLV-driver columns: {missing}")
    rows = []
    for driver in DRIVERS:
        test = correlation_test(frame[driver], frame["historical_clv"], method="spearman")
        rows.append({"metric_or_driver": driver, "analysis_type": "clv_association", "population": "synthetic customers", "comparison_group": "continuous rank association", "effect_direction": "positive" if test.effect_size > 0 else "negative", "effect_size": test.effect_size, "effect_size_name": "Spearman rho", "statistic": test.statistic, "p_value": test.p_value, "confidence_interval_low": test.ci_low, "confidence_interval_high": test.ci_high, "importance_or_strength": abs(test.effect_size), "model_standardized_coefficient": np.nan, "business_interpretation": f"{driver} has a {'positive' if test.effect_size > 0 else 'negative'} rank association with historical CLV.", "recommended_action": f"Use {driver} as a monitoring signal, then validate any targeting policy prospectively.", "limitations": "Bivariate association in synthetic observational data; confounding may remain."})
    return pd.DataFrame(rows).sort_values("importance_or_strength", ascending=False).reset_index(drop=True)
