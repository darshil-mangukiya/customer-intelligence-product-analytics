# Modeled User Stories

These stories translate the modeled requirements in [business_requirements.md](business_requirements.md). Each story assumes synthetic data and governed aggregate outputs.

1. **US-001 / CR-001:** As a Retention Manager, I want high-CLV groups ranked by governed churn risk so that I can prioritize human review. Acceptance: period, risk definition, count, CLV, exposure, source, recommendation, and limitation are present.
2. **US-002 / CR-002:** As a Data Analyst, I want ranked churn-associated drivers so that I can propose testable investigations. Acceptance: strength, method, traceable source, and association-not-causation language are present.
3. **US-003 / CR-003:** As a Finance Business Partner, I want revenue and CLV exposure reconciled to customer marts so that scenario inputs are auditable. Acceptance: historical values reconcile within tolerance.
4. **US-004 / CR-004:** As a Product Manager, I want statistical and practical significance shown separately so that a small detectable effect is not automatically scaled. Acceptance: p-value, CI, effect size, practical threshold, and both statuses appear.
5. **US-005 / CR-005:** As a Customer Strategy Manager, I want prior-to-current segment movement so that deteriorating valuable groups can be reviewed. Acceptance: transition, count, value change, risk change, source, and unavailable historical engagement disclosure appear.
6. **US-006 / CR-006:** As a Data Analyst, I want SRM checked before outcome interpretation so that allocation defects are surfaced. Acceptance: actual/expected counts and chi-square p-value produce a deterministic status.
7. **US-007 / CR-007:** As a Product Manager, I want one registered synthetic experiment linked to its readout and decision log so that the lifecycle is traceable. Acceptance: matching ID and methodology are present.
8. **US-008 / CR-008:** As a Finance Business Partner, I want five retention scenarios so that cost, lift, preserved value, and ROI tradeoffs can be reviewed. Acceptance: assumptions are explicit and outputs say scenario estimate.
9. **US-009 / CR-009:** As a Retention Manager, I want an action center combining risk, CLV, migration, drivers, and experiment evidence so that review effort is prioritized. Acceptance: recommendation is advisory and status is `NEEDS_REVIEW`.
10. **US-010 / CR-013:** As a BI Developer, I want output reconciliation so that reporting exports preserve source totals. Acceptance: source, output, difference, tolerance, and PASS/FAIL are machine-readable.
11. **US-011 / CR-015:** As a Data Analyst, I want a finite aggregate JSON evidence packet so that narrative tools cannot invent authoritative metrics. Acceptance: required schema, source evidence, warnings, and limitations validate with no NaN/Infinity.
12. **US-012 / CR-016:** As a Customer Strategy Manager, I want a structured advisory copilot so that I can interpret governed results. Acceptance: exact supporting metrics, statistical evidence, warnings, uncertainty, recommendations, and evidence references are returned.
13. **US-013 / CR-018:** As a BI Developer, I want one local command to refresh the lifecycle so that customer intelligence is reproducible. Acceptance: every stage records status/runtime and no external service is required.

Across all stories, acceptance requires a reporting period, traceable source, decision limitation, and no protected or sensitive characteristic as an eligibility rule.
