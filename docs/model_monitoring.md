# Model Monitoring

Monitoring strategy for model outputs.

## Signals

- Score distribution drift, CLV band mix, churn risk tier mix, feature quality, scoring freshness, and champion metric thresholds.

## Actions

- Review drift before using scores in activation.
- Re-score customers after major data generation or feature logic changes.
# Model Monitoring

The reproducible monitoring simulation splits the synthetic population at the median signup date into a reference and current slice. It evaluates actual churn features with PSI, KS, and missingness deltas; churn/CLV score distributions and risk-tier mix; and segment share, count, and CLV changes. PSI below 0.10 is stable, 0.10–0.25 is watch, and 0.25 or above is material drift; missingness deltas of 5/10 percentage points trigger watch/material review. These are explainable review triggers, not proof of degraded model performance or production monitoring.
