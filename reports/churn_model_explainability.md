# Churn Model Explainability

## Method

SHAP is not installed in the current local dependency set. For the existing standardized logistic regression, P3 uses an exact additive log-odds decomposition: each standardized feature deviation multiplied by its fitted coefficient. This is lightweight, model-specific, and reconciles exactly to the model probability.

Leading mean absolute predictive contributions: recency_days, channel_diversity, orders, category_diversity, return_rate, product_diversity.
Local example maximum probability reconciliation error: 1.919e-22.

## Statistical Drivers Versus Predictive Contributions

Statistical driver analysis describes population-level associations and uncertainty. Predictive contribution analysis explains why this fitted model produced a score for a record. They may disagree and neither establishes causality.

Use ‘factors contributing to the model prediction’ and ‘features associated with higher predicted churn risk’; never interpret these outputs as causes of churn.
