# Segmentation Model Card

**Model / versions:** `segmentation_model`; `artifacts/model_registry.json` records content-derived dataset and feature versions, the SHA-256 artifact hash, algorithm parameters, and validation timestamp.

Assign behavioral customer segments and business recommendations.

## Inputs

- Customer features, transactional aggregates, engagement, return, discount, session, and product behavior signals.

## Outputs

- Scored customer marts, dashboard fields, model monitoring outputs, and activation-ready fields.

## Model Scope

- Trained on generated customer behavior data covering value, recency, frequency, engagement, returns, discounts, and product affinity.

## Method, validation, and governance

Standardized K-Means with five clusters supports descriptive customer-strategy review. There is no supervised target or probability threshold, and calibration is not applicable. Validation challenges k=3–7 using silhouette, Davies–Bouldin, inertia, cluster balance, seed adjusted Rand index, and time-slice distribution stability. K=5 is retained for interpretable operational coverage, not claimed as a mathematical optimum.

Intended users are customer analytics and strategy reviewers. Segment labels must remain grounded in observed profiles. Prohibited uses include protected-class decisions, causal claims, or automated customer treatment. Synthetic training data may not represent real populations; stability and fairness require revalidation before any real use. Artifact: `models/segmentation_model.joblib`.
