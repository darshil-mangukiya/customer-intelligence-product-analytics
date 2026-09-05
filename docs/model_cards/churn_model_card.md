# Churn Model Card

**Model / versions:** `churn_model`; `artifacts/model_registry.json` records the content-derived model, dataset, and feature versions, SHA-256 artifact hash, and validation timestamp.

Predict churn probability and prioritize expected profit at risk.

## Inputs

- Customer features, transactional aggregates, engagement, return, discount, session, and product behavior signals.

## Outputs

- Scored customer marts, dashboard fields, model monitoring outputs, and activation-ready fields.

## Model Scope

- Trained on generated customer behavior data covering churn, engagement, purchase, discount, return, and value patterns.

## Method and validation

- Target: synthetic `churn_label`; population: deterministic synthetic customer feature base.
- Algorithm: standardized logistic regression using the governed feature list in code.
- Evaluation: deterministic stratified held-out test set; ROC-AUC, PR-AUC, precision, recall, F1, accuracy, log loss, Brier score, confusion matrix, top-K ranking, and threshold economics.
- Threshold: 0.50 remains the scoring convention. Capacity planning uses the generated top-K and threshold tables because the tested fixed thresholds did not meet the 20% capacity assumption.
- Calibration: raw, sigmoid, and isotonic probabilities are compared. The retained method and decision rule are recorded in the calibration report and registry.
- Explainability: exact standardized-logistic log-odds contributions, used because SHAP is not installed and linear contributions reconcile directly to the model prediction. This explains prediction contributions, not causality.

## Governance and limitations

Intended users are data analysts, data scientists, and customer-strategy reviewers. Prohibited uses include automated adverse decisions, real customer contact, causal claims, or use as a production risk score. Inputs may encode synthetic demographic and behavioral patterns that would require fairness, privacy, representativeness, and legal review on real data. Artifacts: `models/churn_model.joblib`, generated evaluation CSVs, and reports under `reports/`.
