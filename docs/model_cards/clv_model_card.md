# CLV Model Card

**Model / versions:** `clv_model`; `artifacts/model_registry.json` records content-derived versions, the SHA-256 artifact hash, parameters, and validation timestamp.

Estimate predicted customer value and CLV at risk.

## Inputs

- Customer features, transactional aggregates, engagement, return, discount, session, and product behavior signals.

## Outputs

- Scored customer marts, dashboard fields, model monitoring outputs, and activation-ready fields.

## Model Scope

- Trained on generated customer value data covering purchase frequency, margin, churn exposure, engagement, and future-value patterns.

## Method, validation, and governance

The existing regression pipeline estimates synthetic twelve-month CLV from governed customer features. Evaluation metrics are read from the existing model artifact evidence; classification thresholds and probability calibration are not applicable. Distribution drift is monitored as a review signal.

Intended users are customer analytics, finance analytics, and strategy reviewers. The value is modeled rather than realized and must not authorize individualized treatment. Prohibited uses include credit, eligibility, adverse decisions, or claims of real customer economics. Real deployment would require representativeness, privacy, bias, and stability review. Artifact: `models/clv_model.joblib`.
