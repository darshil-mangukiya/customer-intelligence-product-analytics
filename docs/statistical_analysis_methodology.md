# Statistical Analysis and Experimentation Methodology

## Scope

The methodology layer uses deterministic generated customer, order, product, segment, churn, CLV, and experiment outputs. The methods and recorded results apply to this dataset.

## Decision chain

```text
Business question -> governed dataset -> assumption checks -> test/model
-> 95% confidence interval -> p-value -> effect size -> interpretation
-> recommended action -> KPI to monitor
```

Seven pre-scoped questions limit opportunistic testing, and Holm adjustment controls family-wise error across them. Two-sided tests use `alpha = 0.05`. A detectable p-value is never treated as proof of material value. Welch tests compare numeric groups without assuming equal variance; proportion z-tests compare binary rates; Pearson chi-square with Cramer's V evaluates categorical associations; Spearman correlation evaluates monotonic relationships; and robust-covariance OLS supports explanatory CLV interpretation.

The synthetic retention-offer evaluation reports group sizes, rates, absolute difference, relative lift, 95% interval, p-value, risk-difference effect size, an approximate 80%-power minimum detectable effect, and a separate two-percentage-point practical threshold.

The experiment registry fixes the baseline, desired minimum detectable effect, alpha, power, population, primary/secondary metrics, guardrails, method, status, and review owner before readout. `analytics/experiment_design.py` uses the standard equal-sized two-proportion normal approximation to calculate required sample size from the declared baseline and treatment-rate alternative. This design output supports planning; it does not retroactively change the observed result.

Before outcome interpretation, sample-ratio mismatch is evaluated with a one-degree-of-freedom Pearson chi-square test against the planned 50/50 allocation. SRM uses alpha 0.01 to reduce false alarms from ordinary random allocation variation. A failed SRM marks the experiment unreliable until assignment or instrumentation is investigated; tolerances and significance rules are not weakened to obtain a pass.

Driver rankings use standardized logistic-regression coefficients plus group differences for churn and Spearman associations for CLV. “Driver” means an associated signal, not a verified cause.

## Reproduction

Run `make analytics` after marts are available, or use `make customer-intelligence` for the governed end-to-end lifecycle. Outputs are written to `data/exports`, experiment readouts to `reports/experiments`, and validations are included in `make validate`.

## Independent R experiment validation

Base R provides a focused cross-language validation layer. `analytics/r/experiment_validation.R` reads the same deterministic `data/exports/ab_test_customer_assignments.csv` used by Python.

The script uses base R and requires no external packages. R 4.1 or newer is recommended. It invokes `prop.test(..., correct = FALSE)` to match Python's pooled, two-sided difference-in-proportions test without Yates continuity correction. The signed z statistic is calculated from the same pooled standard error. Because base R's `prop.test` confidence interval is not the same contract as the existing Python helper, R independently calculates the treatment-minus-control unpooled Wald interval used by Python. It also calculates absolute lift, relative lift, risk ratio, statistical significance at alpha 0.05, and practical significance at the existing two-percentage-point threshold.

`analytics/r_validation.py` runs the R script and reconciles exact counts and boolean conclusions plus numeric results at an absolute tolerance of `1e-10`. It writes `data/exports/python_r_statistical_reconciliation.csv` and reports PASS only when every required metric meets its contract. The workflow executed successfully with base R 4.6.1: all 12 required comparisons passed, including counts, rates, lift, confidence bounds, test statistic, p-value, and statistical/practical significance. Execute with:

```text
make analytics
make r-validate
```

R remains optional for the primary Python pipeline. The recorded reconciliation validates the current generated experiment inputs across two implementations.

## Safeguards and limitations

- Empty inputs, malformed groups, zero denominators, missing columns, low counts, non-finite values, and constant series are rejected or flagged.
- Confidence intervals and effect sizes accompany inferential results.
- The generated experiment is deterministic and represents no external customer population.
- Observational association and regression coefficients do not establish causality.
- Real decisions require data-quality review, representative production data, prospective testing, and domain review.
