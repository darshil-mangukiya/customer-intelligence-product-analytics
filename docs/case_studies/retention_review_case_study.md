# Retention Review Case Study

## Question

Which generated customer segment should be reviewed first for a retention intervention?

## Evidence path

The decision sequence combines customer value, modeled churn risk, segment migration, cohort retention, synthetic experiment evidence, and scenario economics. The `retention_action_center` is the governed review queue; it is not an activation list.

The highest-priority rows include Discount-driven Buyers and One-time Buyers at Critical modeled risk. One-time Buyers have the larger critical-risk population, while Discount-driven Buyers show materially greater generated revenue exposure. This makes Discount-driven Buyers a strong first segment for a margin-aware review, while One-time Buyers remain a scale-focused first-to-second-purchase problem.

The synthetic experiment estimates a 2.78 percentage-point absolute conversion lift (95% interval 1.06–4.51 points; p=0.00151) and clears the preset 2-point practical threshold. It demonstrates the evaluation method only: no real subjects, intervention, retention improvement, or causal commercial impact occurred.

## Recommendation

Review a targeted, margin-safe retention treatment for Discount-driven Buyers with a continuing holdout and explicit cost guardrails. Separately test low-cost first-to-second-purchase support for One-time Buyers. Require prospective validation before any activation.

## Limitations

All inputs are generated. Churn and CLV are modeled, coefficients are associative, scenario economics depend on assumptions, and the synthetic experiment does not establish external validity. A real decision would require consent/privacy controls, eligibility rules, incrementality measurement, operational capacity, and monitoring.
