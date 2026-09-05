# Synthetic Subgroup Model-Risk Check

This evaluates subgroup-analysis methodology on synthetic data and does not establish real-world fairness.

- Groups evaluated: 20
- Insufficient-sample groups: 2
- Minimum required positives and negatives per group: 20
- Metrics: ROC-AUC, PR-AUC, precision, recall, false-positive rate, false-negative rate, top-10% lift, Brier score, and calibration gap.

| Dimension | Evaluated | Insufficient | ROC-AUC range | PR-AUC range |
|---|---:|---:|---:|---:|
| region | 10 | 0 | 0.992-0.998 | 0.998-0.999 |
| tenure_band | 3 | 0 | 0.993-0.996 | 0.998-0.999 |
| value_tier | 4 | 1 | 0.984-0.999 | 0.959-1.000 |
| activity_level | 3 | 1 | 0.975-0.989 | 0.976-0.998 |

Observed subgroup differences are diagnostic review signals on deterministic synthetic data. They must not be interpreted as protected-class fairness results, causal effects, or evidence of real-world model performance.
