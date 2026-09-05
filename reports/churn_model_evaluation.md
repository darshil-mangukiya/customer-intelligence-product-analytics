# Churn Model Evaluation

The existing logistic-regression algorithm was preserved and evaluated on its deterministic 25% held-out set.

## Predictive Metrics

- ROC-AUC: 0.9958
- PR-AUC: 0.9986
- Precision: 0.9966
- Recall: 0.9525
- F1: 0.9741
- Accuracy: 0.9624
- Log loss: 0.0895
- Brier score: 0.0270

## Ranking Use

The top 10% of risk scores captured 13.5% of held-out churners with lift 1.35 over the held-out base rate.

## Modeled Operating Point

No fixed probability threshold in the tested range produces a non-empty selection within five percentage points of the modeled 20% capacity. Use explicit top-K ranking for capacity planning; no universal threshold is recommended.
This is an analytical operating point, not a production-approved threshold. False-positive cost uses a synthetic $6 contact assumption; false-negative exposure uses held-out historical CLV.

## Limitations

All records and outcomes are synthetic. Strong discrimination reflects the controlled generator and does not establish future production performance.
