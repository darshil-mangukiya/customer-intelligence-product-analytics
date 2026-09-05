# Executive Customer Strategy Brief

## Executive Summary
Seven planned analyses and one retention experiment were evaluated. The largest standardized effect was **Do high-value customers purchase more frequently?** (Cohen's d=1.6520).

## Risk Signals
The highest-ranked churn-associated signals are recency_days, orders, and return_rate. Rank High/Critical risk customers by expected profit at risk and review these signals before selecting an intervention.

## Customer Value Opportunity
The strongest CLV-associated behaviors are orders, avg_order_value, purchase_frequency_30d. Loyalty and repeat-purchase tests should retain return-adjusted margin guardrails.

## Experiment Results
The experiment estimated absolute lift of 2.78% (95% CI 1.06% to 4.51%; p=0.0015). Statistical significance: True; practical significance at a 2-point threshold: True. Recommendation: Targeted rollout candidate with a continuing holdout.

## Recommended Actions
| Priority | Customer Group | Observed Signal | Evidence | Recommended Action | Expected KPI | Limitation |
|---:|---|---|---|---|---|---|
| 1 | High/Critical risk | Leading driver: recency_days | Standardized logistic association | Diagnose and test a targeted intervention with holdout | Churn rate | Association, not causation |
| 2 | High modeled CLV | Leading value signal: orders | Spearman rho 0.8978 | Design loyalty test with margin guardrail | Return-adjusted CLV | Modeled value |
| 3 | Experiment-eligible risk pool | Treatment-control difference | 95% CI and p-value reported above | Targeted rollout candidate with a continuing holdout | Conversion and profit proxy | Generated experiment population |

## KPIs to Monitor
Churn rate; retention rate; repeat-purchase rate; predicted and historical CLV; engagement rate; return rate; experiment conversion; return-adjusted profit proxy.

## Analytical Limits
Results apply to the generated project dataset. Observational associations are not causal, and scenario economics are estimates. External use requires representative data and prospective validation.

## Decision Support Summary

- Segment migration assessed 5,000 customers; 1,914 moved to a lower RFM segment at the historical-cutoff comparison.
- Experiment assignment passed the SRM check (p=0.0710 at alpha 0.01), so allocation does not invalidate interpretation.
- The Expected scenario estimates net benefit of -$11,801 and ROI of -0.75, indicating that the assumed intervention is not economically attractive.
- The highest review priority is Discount-driven Buyers / Critical risk with 1,054 customers; its action-center status remains `NEEDS_REVIEW`.
- The action center produces review priorities and has no external write path.
