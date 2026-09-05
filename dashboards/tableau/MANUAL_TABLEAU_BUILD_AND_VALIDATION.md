# Final Tableau Desktop Validation Record

The authoritative local workbook is `workbook/Customer_Intelligence_Product_Analytics.twb`. Do not regenerate, structurally rebuild, or overwrite it. Tableau Desktop 2026.1 normalized the XML and the user completed manual presentation wording changes after generation.

All project data is deterministic/generated. No real customer, production revenue, realized campaign impact, production deployment, or external Tableau publication is claimed.

## Completed validation

| Check | Result | Evidence |
|---|---:|---|
| TWB opens in Tableau Desktop 2026.1 | PASS | User manual validation |
| Portable standalone TWB reopens after `../data` path edit | PASS | User manual validation |
| Executive Overview renders | PASS | `screenshots/01_executive_overview.png` |
| Customer Segmentation renders | PASS | `screenshots/02_customer_segmentation.png` |
| Churn & Retention renders | PASS | `screenshots/03_churn_retention.png` |
| CLV Analysis renders | PASS | `screenshots/04_clv_analysis.png` |
| Cohort Retention renders | PASS | `screenshots/05_cohort_retention.png` |
| Product Profitability renders | PASS | `screenshots/06_product_profitability.png` |
| Experiment & Decision Evidence renders | PASS | `screenshots/07_experiment_decision_evidence.png` |
| Customer Retention Decision Story | 7/7 PASS | All points manually opened; `screenshots/08_customer_retention_story.png` |
| TWBX saved | PASS | User manual validation; artifact present |
| Tableau closed and TWBX reopened | PASS | User manual validation; TWBX unchanged by portability pass |
| Canonical genuine screenshots | 8/8 PASS | PNG and visual audit |
| Governed metric reconciliation | 27/27 PASS | `validation/tableau_reconciliation_report.csv` |
| External publication | NONE | Local-only validation boundary |

The TWBX is present, archive-valid, packages all nine governed CSVs, and contains no personal filesystem paths. It was not modified during the portability pass.

## Completed portability revalidation

The standalone TWB’s nine connection directories were changed only from the Tableau Desktop-local absolute directory to `../data`. The user then reopened `workbook/Customer_Intelligence_Product_Analytics.twb` in Tableau Desktop and verified:

1. Executive Overview.
2. Customer Segmentation.
3. Churn & Retention.
4. CLV Analysis.
5. Cohort Retention.
6. Product Profitability.
7. Experiment & Decision Evidence.
8. Customer Retention Decision Story.

Portable standalone-TWB reopen validation: **PASS**.

## Approved visible wording

The user manually reduced repetitive provenance language in the dashboard UI while keeping truthful disclosure in project documentation.

| View | Approved subtitle |
|---|---|
| Executive Overview | Customer health, value, product, and experiment evidence. |
| Customer Segmentation | Customer segment value, RFM behavior, channel composition, and migration. |
| Churn & Retention | Customer risk, retention opportunities, and modeled churn associations. |
| CLV Analysis | Historical customer value and modeled 12-month customer lifetime value. |
| Cohort Retention | Customer retention by acquisition cohort and month since acquisition. |
| Product Profitability | Return-adjusted profitability, margins, returns, and product performance. |
| Experiment & Decision Evidence | Experiment results, statistical evidence, practical significance, and decision economics. |

Story point 4 intentionally remains: **What does generated cohort retention look like?** Do not normalize or rewrite it.

## Interaction claim boundary

The following were not evidenced as separately exercised and must not be described as fully tested:

- Four parameters: Metric Selector, Top N, Risk Threshold, and Experiment View.
- Five generated filter/highlight actions.
- Two optional manual Go-to-Sheet actions.

These are optional interaction QA/enhancement items, not remaining workbook construction work. Their definitions must not be changed merely to produce a stronger claim.

## Artifact protection

- Do not run `build_tableau_workbook.py` over the final TWB.
- Do not edit datasource, worksheet, dashboard, Story, calculation, filter, LOD, table-calculation, parameter, or action XML without an actual validated failure.
- Do not fabricate a TWBX or screenshot.
- Keep exactly the eight canonical screenshots documented in `screenshots/README.md`.
- Keep all work local; do not publish to Tableau Public, Server, or Cloud.
