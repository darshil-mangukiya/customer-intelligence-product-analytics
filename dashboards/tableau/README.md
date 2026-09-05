# Tableau Customer Intelligence Implementation

**Status: TABLEAU IMPLEMENTATION COMPLETE — LOCAL DESKTOP + TWBX + PORTABILITY VALIDATION PASSED.**

The Tableau Desktop 2026.1 implementation contains nine governed presentation sources, 36 worksheets, seven dashboards, and one seven-point decision Story. All dashboards and Story points manually rendered, 8/8 genuine Tableau exports are present, and 27/27 governed metrics reconcile. The user also confirmed that a packaged TWBX was saved, Tableau was closed, and the TWBX reopened successfully.

The validated TWBX is present and uses portable packaged paths. The standalone TWB’s nine connection directories use `../data`, and the path-only portability edit passed a subsequent manual Tableau Desktop reopen.

All data is deterministic/generated portfolio data. It does not represent real customers, production revenue, a production experiment, realized commercial impact, or a deployed Tableau environment. Nothing was published externally.

## Five-minute review

1. Open the final [Tableau workbook](workbook/Customer_Intelligence_Product_Analytics.twb).
2. Review the [eight genuine Tableau screenshots](screenshots/README.md).
3. Read the [authoritative validation report](validation/tableau_validation_report.md).
4. Inspect the [structural validation](validation/tableau_workbook_structural_validation.md).
5. Review the [worksheet binding audit](validation/tableau_worksheet_binding_audit.csv), [datasource audit](validation/tableau_datasource_audit.csv), and [27-metric reconciliation](validation/tableau_reconciliation_report.csv).
6. Review the [workbook contract](workbook/WORKBOOK_SPEC.md) and [calculated-field catalog](calculations/CALCULATED_FIELDS.md).
7. Use the [final Desktop validation record](MANUAL_TABLEAU_BUILD_AND_VALIDATION.md) for the precise claim boundary.

## Screenshot evidence

1. [Executive Overview](screenshots/01_executive_overview.png)
2. [Customer Segmentation](screenshots/02_customer_segmentation.png)
3. [Churn & Retention](screenshots/03_churn_retention.png)
4. [CLV Analysis](screenshots/04_clv_analysis.png)
5. [Cohort Retention](screenshots/05_cohort_retention.png)
6. [Product Profitability](screenshots/06_product_profitability.png)
7. [Experiment & Decision Evidence](screenshots/07_experiment_decision_evidence.png)
8. [Customer Retention Decision Story](screenshots/08_customer_retention_story.png)

## Source model

| Tableau source | Governed origin | Grain | Primary use |
|---|---|---|---|
| `tableau_executive_kpis.csv` | KPI summary | KPI | Executive cards |
| `tableau_customer_analytics.csv` | Customer, segment, RFM, churn, and CLV marts | Customer | Segmentation, churn, CLV |
| `tableau_cohort_retention.csv` | Cohort retention mart | Cohort month × month index | Retention heatmap and curves |
| `tableau_product_profitability.csv` | Product profitability mart | Product | Profitability and leakage |
| `tableau_experiment_results.csv` | Experiment evaluation and variant summary | Variant | Statistical decision evidence |
| `tableau_segment_migration.csv` | Segment migration summary | Transition | Migration flow |
| `tableau_churn_drivers.csv` | Churn model summary | Model feature | Associative model signals |
| `tableau_retention_actions.csv` | Retention action center | Segment × risk tier | Review queue; no automatic action |
| `tableau_retention_economics.csv` | Retention scenarios | Scenario | Decision context; not observed impact |

## Reproducibility boundary

The build scripts remain as technical implementation references. Do not run the workbook generator over the authoritative Desktop-saved TWB: Tableau Desktop normalization and the user’s manual presentation edits intentionally supersede the older generated XML shape.

## Interaction claim boundary

Manually proven: portable standalone-TWB reopen, 7/7 dashboard rendering, 7/7 Story-point rendering/navigation, TWBX close/reopen, and 8/8 genuine screenshot exports. The TWBX was not modified during the portability pass.

Not separately certified: behavior of all four parameters and all five generated actions. The two Go-to-Sheet actions remain optional manual enhancements. These are available for optional interaction QA and are not release blockers. No Tableau Public, Server, Cloud, or production deployment is claimed.
