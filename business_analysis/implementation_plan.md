# Customer Intelligence Implementation Plan

## Baseline and scope

Reuse the existing synthetic-data pipeline, Customer 360 features, RFM/segmentation, cohorts, churn, CLV, statistical analysis, A/B testing, Python/base-R reconciliation, driver analysis, Power BI-ready exports, Streamlit, FastAPI, validation, and Makefile orchestration. The PBIX, original P3, Snowflake, Salesforce, and external write-back are outside scope.

## Delivery sequence

1. Govern the existing experiment with a registry, design/power output, SRM, readout, and decision log.
2. Calculate historical-cutoff versus current RFM migration and aggregate its transition matrix.
3. Add retention scenario economics with explicit assumptions and synthetic-estimate labels.
4. Combine risk, value, migration, driver, and experiment evidence in an advisory action center.
5. Reconcile important customer, churn, CLV, experiment, migration, and action totals.
6. Generate explainable alerts and a deterministic aggregate insight packet.
7. Add one provider-abstracted strategy copilot with fake, disabled, and optional OpenAI modes.
8. Validate numeric/statistical fidelity, SRM awareness, causality, privacy, malformed output, and data-quality disclosure.
9. Generate requirements traceability, UAT evidence, operating documentation, and the one-command workflow.

## Testing, UAT, and release concept

Unit tests cover calculations and edge cases; integration tests validate generated schemas and reconciliation; fake-provider evaluations validate guardrails. UAT cases remain `NOT RUN` until their cited automated evidence is executed, then the workbook generator imports genuine statuses. Release means local regeneration with `make customer-intelligence`, R reconciliation, tests, lint, documentation checks, and manual artifact review.

## Recovery concept

Generated exports can be rebuilt from the governed source data and orchestration commands. The PBIX remains a separately managed presentation asset, while the five full-volume validation gates remain unchanged.

## Limitations

All customer and experiment data is synthetic. Scenario economics are assumptions, observational drivers are non-causal, engagement lacks a historical snapshot, AI recommendations are advisory, and real OpenAI execution is verified only when credentials are present.
