# Model Monitoring Report

> Evidence profile: `full_250k` (250,000 customers) — full-volume monitoring evidence; not authoritative for current 5K model KPIs.

- Signals evaluated: 13
- Passing signals: 12
- Watch signals: 1

## Current Score Snapshot
- Average churn probability: 74.7%
- P95 churn probability: 100.0%
- Average predicted CLV: $191
- P95 predicted CLV: $873

| Category | Signal | Observed | Threshold | Status | Meaning |
|---|---|---:|---|---|---|
| data_freshness | `mart_churn_risk_rows` | 250000 | >= 100000 | PASS | Customer scoring coverage |
| data_freshness | `mart_clv_rows` | 250000 | >= 100000 | PASS | CLV scoring coverage |
| model_quality | `churn_roc_auc` | 0.9952 | >= 0.75 | PASS | Churn ranking quality |
| model_quality | `churn_recall` | 0.9642 | >= 0.60 | PASS | Risk capture quality |
| model_quality | `clv_r2` | 0.3663 | >= 0.10 | PASS | Forward-value signal strength |
| model_quality | `segmentation_silhouette` | 0.2769 | >= 0.20 | PASS | Cluster separation |
| score_drift | `churn_probability_psi` | 0.0001 | <= 0.10 | PASS | Population stability index for churn scores |
| score_drift | `predicted_clv_psi` | 0.0002 | <= 0.10 | PASS | Population stability index for CLV scores |
| mix_drift | `churn_risk_mix_delta` | 0.0 | <= 0.08 | PASS | Risk tier distribution shift |
| mix_drift | `segment_mix_delta` | 0.0 | <= 0.08 | PASS | Segment distribution shift |
| baseline | `baseline_status` | loaded | baseline available | PASS | Monitoring baseline state |
| kpi_watch | `revenue_leakage` | 28247631.3945 | tracked | PASS | Executive leakage watchlist |
| kpi_watch | `retention_rate` | 0.2318 | >= 0.65 | WATCH | Executive retention watchlist |

## Watch Items
- retention_rate: observed `0.2318` against `>= 0.65`.
