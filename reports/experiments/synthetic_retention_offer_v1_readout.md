# synthetic_retention_offer_v1 Experiment Readout

## Business Question
Does a modeled retention offer improve conversion among High/Critical churn-risk customers?

## Hypothesis
Treatment conversion equals control conversion.

## Population
Synthetic High/Critical churn-risk customers

## Experiment Design
Control: Control; treatment: Retention Offer; primary metric: conversion_rate.

## Sample Size
Control: 1,809; treatment: 1,702.

## SRM
Status: **PASS**; chi-square=3.2609; p=0.0710. Allocation is consistent with the planned split.

## Primary Metric
Conversion rate.

## Results
- Control: 5.91%
- Treatment: 8.70%
- Absolute lift: 2.78%
- Relative lift: 47.01%
- 95% CI: 1.06% to 4.51%
- p-value: 0.001509
- Effect size: 0.0278 (risk difference)
- Statistical significance: True
- Practical significance: True

## Guardrail Metrics
Average profit proxy and sample-ratio mismatch are retained as rollout guardrails.

## Business Interpretation
The treatment difference is statistically detectable and exceeds the predefined practical threshold for the generated experiment population.

## Recommendation
Targeted rollout candidate with a continuing holdout

## Limitations
Results apply to the generated experiment population.
