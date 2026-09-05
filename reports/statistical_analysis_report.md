# Statistical Analysis Report

## 1. Objective
Evaluate customer and product questions with formal tests, uncertainty, effect sizes, and business interpretation.

## 2. Dataset / Population
Deterministic synthetic customer, transaction, segment, churn, CLV, cohort, product, and experiment outputs. No real customers or live experiment are represented.

### Descriptive snapshot by churn status
| Churn Label | Metric | N | Mean | Median | Standard Deviation | 25th Percentile | 75th Percentile |
|---|---|---:|---:|---:|---:|---:|---:|
| 0 | orders | 1,290 | 15.1295 | 9.0000 | 17.3820 | 5.0000 | 19.0000 |
| 0 | historical_clv | 1,290 | 472.1677 | 232.9222 | 702.0043 | 97.2905 | 566.5973 |
| 0 | predicted_12m_clv | 1,290 | 656.1008 | 331.1234 | 920.2872 | 149.1092 | 751.5632 |
| 0 | engagement_score | 1,290 | 82.5086 | 89.1900 | 19.4416 | 68.1575 | 100.0000 |
| 0 | repeat_purchase_flag | 1,290 | 0.9907 | 1.0000 | 0.0960 | 1.0000 | 1.0000 |
| 0 | return_rate | 1,290 | 0.1626 | 0.1384 | 0.1605 | 0.0000 | 0.2500 |
| 1 | orders | 3,710 | 1.4779 | 1.0000 | 2.4537 | 0.0000 | 2.0000 |
| 1 | historical_clv | 3,710 | 45.3418 | 0.0000 | 103.4909 | 0.0000 | 47.7400 |
| 1 | predicted_12m_clv | 3,710 | 62.8286 | 11.2767 | 122.4359 | 2.4506 | 74.6650 |
| 1 | engagement_score | 3,710 | 53.7902 | 50.5750 | 21.6744 | 36.6825 | 68.4200 |
| 1 | repeat_purchase_flag | 3,710 | 0.3000 | 0.0000 | 0.4583 | 0.0000 | 1.0000 |
| 1 | return_rate | 3,710 | 0.0745 | 0.0000 | 0.2082 | 0.0000 | 0.0000 |

## 3. Methodology
Two-sided tests use alpha=0.05. Analyses report 95% confidence intervals and effect sizes. The seven planned questions use Holm family-wise error adjustment; raw p-values are interpreted with adjusted results, effect magnitude, and business context.

## 4. Analytical Questions

### Q01: Does higher discount exposure correspond to different repeat-purchase behavior?
- Hypothesis: Repeat-purchase rates are equal above and below median discount dependency.
- Population / sample: Synthetic customers split at median discount dependency
- Metric and method: repeat-purchase rate; Two-sample proportion z-test
- Result: statistic 44.4203; raw p-value 0.0000; Holm-adjusted p-value 0.0000; 95% CI [0.6061, 0.6491]
- Effect size: 0.6276 (risk difference, large)
- Statistical interpretation: The null hypothesis is rejected at alpha=0.05; effect magnitude is large. Holm-adjusted significance: True.
- Business interpretation: Higher-discount and lower-discount customers show an observed repeat-rate difference; the effect size determines whether it is decision-relevant.
- Recommended action: Test discount policy with randomized holdouts before changing targeting.
- KPI to monitor: repeat-purchase rate
- Assumptions: Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.
- Limitations: Median split loses information and the observational comparison is not causal.

### Q02: Is churn status associated with customer segment?
- Hypothesis: Customer segment and churn status are independent.
- Population / sample: Synthetic customers assigned to behavioral segments
- Metric and method: churn status; Pearson chi-square test
- Result: statistic 2123.4697; raw p-value 0.0000; Holm-adjusted p-value 0.0000; 95% CI [not applicable, not applicable]
- Effect size: 0.6517 (Cramer's V, large)
- Statistical interpretation: The null hypothesis is rejected at alpha=0.05; effect magnitude is large. Holm-adjusted significance: True.
- Business interpretation: Segment membership contains a churn-risk association signal, but does not itself cause churn.
- Recommended action: Prioritize segment-specific diagnostics and controlled retention tests.
- KPI to monitor: churn rate by segment
- Assumptions: Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.
- Limitations: Segments are model-derived and the chi-square result does not isolate individual drivers.

### Q03: Is engagement meaningfully related to predicted CLV?
- Hypothesis: Engagement score and predicted CLV have no monotonic association.
- Population / sample: Synthetic customers with engagement and CLV scores
- Metric and method: engagement score vs predicted CLV; Spearman correlation
- Result: statistic 0.6725; raw p-value 0.0000; Holm-adjusted p-value 0.0000; 95% CI [0.6571, 0.6874]
- Effect size: 0.6725 (spearman rho, large)
- Statistical interpretation: The null hypothesis is rejected at alpha=0.05; effect magnitude is large. Holm-adjusted significance: True.
- Business interpretation: The rank relationship quantifies whether more engaged customers tend to have higher modeled value.
- Recommended action: Use engagement as a prioritization signal, then validate incremental value in an experiment.
- KPI to monitor: predicted CLV and engagement rate
- Assumptions: Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.
- Limitations: Predicted CLV is modeled and correlation is not causation.

### Q04: Do return outcomes differ across product categories?
- Hypothesis: Product category and return flag are independent.
- Population / sample: Synthetic enriched order lines
- Metric and method: return flag; Pearson chi-square test
- Result: statistic 59.5030; raw p-value 0.0000; Holm-adjusted p-value 0.0000; 95% CI [not applicable, not applicable]
- Effect size: 0.0488 (Cramer's V, small)
- Statistical interpretation: The null hypothesis is rejected at alpha=0.05; effect magnitude is small. Holm-adjusted significance: True.
- Business interpretation: Category is associated with return behavior to the degree indicated by Cramer's V.
- Recommended action: Investigate high-return categories for fit, quality, and expectation gaps.
- KPI to monitor: return rate by category
- Assumptions: Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.
- Limitations: Order-line observations from the same customer may not be fully independent.

### Q05: Do acquisition channels produce different retention outcomes?
- Hypothesis: Acquisition channel and churn status are independent.
- Population / sample: Synthetic acquired customers
- Metric and method: retention/churn status; Pearson chi-square test
- Result: statistic 11.3624; raw p-value 0.1820; Holm-adjusted p-value 0.1820; 95% CI [not applicable, not applicable]
- Effect size: 0.0477 (Cramer's V, small)
- Statistical interpretation: The null hypothesis is not rejected at alpha=0.05; effect magnitude is small. Holm-adjusted significance: False.
- Business interpretation: Acquisition mix is associated with downstream retention, conditional on the synthetic design.
- Recommended action: Compare channel quality on retained CLV, not acquisition volume alone.
- KPI to monitor: retention rate by acquisition channel
- Assumptions: Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.
- Limitations: Channel selection is observational and may reflect customer mix. Some expected cells are below 5.

### Q06: Do high-value customers purchase more frequently?
- Hypothesis: Mean order count is equal for top-quartile CLV and other customers.
- Population / sample: Synthetic customers split at the 75th percentile of predicted CLV
- Metric and method: order count; Welch two-sample t-test
- Result: statistic -29.7281; raw p-value 0.0000; Holm-adjusted p-value 0.0000; 95% CI [13.6360, 15.5629]
- Effect size: 1.6520 (Cohen's d, large)
- Statistical interpretation: The null hypothesis is rejected at alpha=0.05; effect magnitude is large. Holm-adjusted significance: True.
- Business interpretation: Top-quartile modeled-value customers show a measurable difference in order frequency.
- Recommended action: Design loyalty journeys around repeat behavior while preserving margin.
- KPI to monitor: orders per customer and CLV
- Assumptions: Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.
- Limitations: CLV and orders are mechanically related, so this is descriptive rather than independent validation.

### Q07: Is return behavior associated with historical customer value?
- Hypothesis: Return rate and historical CLV have no monotonic association.
- Population / sample: Synthetic customers
- Metric and method: return rate vs historical CLV; Spearman correlation
- Result: statistic 0.3858; raw p-value 0.0000; Holm-adjusted p-value 0.0000; 95% CI [0.3620, 0.4092]
- Effect size: 0.3858 (spearman rho, moderate)
- Statistical interpretation: The null hypothesis is rejected at alpha=0.05; effect magnitude is moderate. Holm-adjusted significance: True.
- Business interpretation: The rank association indicates whether returns co-move with realized customer value.
- Recommended action: Use return-aware value metrics and review avoidable return patterns.
- KPI to monitor: return-adjusted CLV and return rate
- Assumptions: Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.
- Limitations: Bivariate association may be confounded by order volume and category mix.

## 5. Statistical Tests
Welch tests address unequal variances; two-proportion z-tests compare binary rates; Pearson chi-square tests assess categorical association.

## 6. Confidence Intervals
Intervals quantify estimation uncertainty. An interval that excludes zero supports a detectable difference, but not necessarily a useful one.

## 7. Effect Sizes
Cohen's d, risk difference, Cramer's V, and correlation coefficients communicate practical magnitude.

## 8. Correlation Findings
- Is engagement meaningfully related to predicted CLV? Effect=0.6725; The rank relationship quantifies whether more engaged customers tend to have higher modeled value.
- Is return behavior associated with historical customer value? Effect=0.3858; The rank association indicates whether returns co-move with realized customer value.

## 9. Regression Findings
The robust-uncertainty OLS model explains adjusted R-squared 0.8503. It models log predicted CLV for interpretation, not causal attribution.
- recency_days: standardized coefficient -1.0768, p=0.0000, 95% CI [-1.1850, -0.9687].
- avg_order_value: standardized coefficient 0.5927, p=0.0000, 95% CI [0.3818, 0.8037].
- orders: standardized coefficient 0.5045, p=0.0000, 95% CI [0.4321, 0.5769].
- engagement_score: standardized coefficient 0.3320, p=0.0000, 95% CI [0.2955, 0.3684].
- discount_dependency: standardized coefficient -0.2096, p=0.0000, 95% CI [-0.2621, -0.1571].
- return_rate: standardized coefficient 0.0330, p=0.2554, 95% CI [-0.0239, 0.0900].

## 10. Experiment Analysis
Control 5.91% vs treatment 8.70%; absolute lift 2.78%, relative lift 47.01%, 95% CI [1.06%, 4.51%], p=0.0015.
Decision: Targeted rollout candidate with a continuing holdout

## 11. Customer Driver Findings
Churn rankings use standardized multivariable logistic coefficients plus group effect sizes. CLV rankings use Spearman association; neither method establishes causality.
- Leading churn-associated signals: recency_days, orders, return_rate, discount_dependency, sessions.
- Leading CLV-associated signals: orders, avg_order_value, purchase_frequency_30d, recency_days, engagement_score.

## 12. Business Interpretation
Results prioritize where to investigate and experiment; statistical detection is kept separate from operational value.

## 13. Recommendations
Use segment holdouts, monitor repeat purchase and return-adjusted CLV, and revisit sample-size assumptions before rollout.

## 14. Assumptions
Independent observations are approximated; numeric tests require finite, non-constant values; chi-square expected counts are checked.

## 15. Limitations
All data and experiment outcomes are synthetic. Associations, model importance, and regression coefficients are not causal and require real-world validation.

## 16. Reproducibility Information
Run `make analytics`. Synthetic generation and assignment use deterministic seed 42 / stable hashes; generated timestamps are audit metadata.
