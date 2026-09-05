# Business Requirements Document

## 1. Business Context

The project simulates a growing ecommerce/SaaS business that has transactional, customer, product, web behavior, and engagement data but lacks a trusted analytics layer for retention, product profitability, customer value, and executive reporting.

The platform converts raw synthetic source data into cleaned datasets, warehouse-ready marts, semantic KPIs, machine learning outputs, business reports, and activation-ready exports.

## 2. Problem Statement

Leadership needs reliable answers to customer and product performance questions, but raw data alone does not provide governed definitions, reusable marts, customer-level scoring, or dashboard-ready outputs. The business needs a repeatable analytics system that separates short-term acquisition activity from durable customer value and product-level profitability.

## 3. Stakeholder Personas

| Stakeholder | Primary need | Decision supported |
|---|---|---|
| Executive team | Trusted KPI view across revenue, profit, churn, retention, and leakage | Prioritize retention, profitability, and growth levers |
| Marketing / lifecycle manager | Activation lists and segment strategy | Target churn-risk, win-back, loyalty, and cross-sell campaigns |
| Product manager | Product retention, returns, margin, and affinity insight | Improve assortment, bundling, and product lifecycle decisions |
| Finance / revenue lead | Margin, leakage, discount, return, and CLV visibility | Evaluate profitability and revenue-quality tradeoffs |
| Customer success leader | Churn-risk prioritization and high-value customer exposure | Focus outreach on customers most likely to lapse |
| BI / analytics team | Governed marts, KPI definitions, semantic model, and dashboard specs | Build reliable Power BI/Tableau reporting assets |

## 4. Stakeholder Pain Points

| Pain point | Business impact |
|---|---|
| Churn is measured inconsistently across teams | Retention decisions are delayed or disputed |
| Customer segments are not action-oriented | Campaigns lack prioritization and clear ownership |
| Product profitability is measured before returns and discounts | Margin leakage is hidden inside revenue growth |
| Cohort behavior is not monitored month by month | Acquisition growth can mask weak retention |
| KPI formulas live outside a governed semantic layer | Dashboards may report inconsistent numbers |
| Activation lists are manually assembled | Lifecycle actions are slow and hard to audit |

## 5. Business Objectives

- Identify high-value customers and customers at elevated churn risk.
- Explain retention and revenue quality by cohort, channel, segment, and first product category.
- Improve product margin visibility with return-adjusted profit and discount leakage.
- Provide BI-ready marts and semantic KPI definitions for repeatable reporting.
- Generate activation-ready customer lists for lifecycle marketing and customer success use cases.
- Document business rules, acceptance criteria, and dashboard requirements for stakeholder review.

## 6. In-Scope Analytics Capabilities

- Customer 360 and customer value analytics
- Churn risk scoring and churn-risk tiering
- RFM and behavioral segmentation
- CLV and customer value banding
- Cohort retention and revenue-retention analysis
- Product profitability, returns, discounts, and affinity analysis
- KPI catalog and semantic model planning
- Completed local Power BI dashboard, Power BI/Tableau implementation guidance, and governed DAX notes
- Activation exports for churn, win-back, high CLV, cross-sell, loyalty, and discount-sensitive audiences
- Data-quality checks and freshness reporting

## 7. Implementation Boundaries

- Controlled synthetic ecommerce/SaaS data supports repeatable portfolio analysis and validation.
- The platform is packaged for local reproducibility with clear extension paths for cloud deployment, streaming ingestion, and orchestration.
- The repository includes a completed local Power BI dashboard; Tableau materials provide design guidance that can be implemented from the governed marts.
- Activation exports are CRM-style, reverse-ETL-ready files for lifecycle targeting workflows.
- Business impact is represented through modeled scenarios, KPI outputs, and stakeholder recommendations based on the synthetic project dataset.

## 8. Business Rules

| Rule | Definition |
|---|---|
| Customer grain | One row per `customer_id` in `dim_customer` and customer-level marts |
| Product grain | One row per `product_id` in `dim_product` |
| Order grain | One row per `order_id` in `fact_orders` |
| Completed order | Orders marked as completed and eligible for revenue, cohort, and purchase-frequency logic |
| Return-adjusted profit | Profit after returns and return-related leakage |
| Churn label | Binary customer-level indicator used for churn analysis and model training |
| Repeat purchase | Customer has two or more completed orders |
| Cohort month | Month of first completed purchase |
| Cohort index | Number of months since cohort month |
| Discount dependency | Discount amount divided by revenue plus discount amount |
| Activation list | Customer-level export with segment, priority, reason, and recommended action |

## 9. KPI Requirements

| KPI | Required grain | Primary owner | Required usage |
|---|---|---|---|
| Revenue | Order, product, segment, channel, month | Finance / BI | Executive and product dashboards |
| Return-adjusted profit | Order, product, category, segment | Finance | Product profitability and leakage analysis |
| Churn rate | Customer, segment, channel | Customer analytics | Churn dashboard and executive summary |
| Retention rate | Cohort month and cohort index | Customer analytics | Cohort dashboard |
| Repeat purchase rate | Customer and segment | Marketing / lifecycle | Customer overview and activation planning |
| CLV and predicted CLV | Customer, segment, channel | Customer analytics | CLV dashboard and retention prioritization |
| Discount rate | Order, product, customer | Finance / marketing | Revenue leakage dashboard |
| Return rate | Order, product, category | Product / finance | Product dashboard |
| Product affinity score | Category pair | Product / lifecycle | Cross-sell planning |

## 10. Data Requirements

- Customer profile and acquisition fields
- Product category, margin, lifecycle, and return profiles
- Transaction-level revenue, discount, return, cost, and profit fields
- Web/session engagement fields
- Email/campaign engagement fields
- Date logic for cohorts and trends
- Validation outputs for rejected rows, anomalies, audit counts, and mart freshness

## 11. Dashboard Requirements

Required dashboard pages:

- Executive Overview
- Customer Intelligence
- Churn Risk
- Cohort Retention
- CLV
- Product Profitability
- Product Affinity
- Segment Strategy
- Acquisition Channel Quality
- Revenue Leakage

Each page must use governed measures where possible, include filters for date/channel/segment/category, and support drill-through to customer, product, or cohort detail where the grain allows it.

## 12. Activation / Export Requirements

Activation exports must include:

- `customer_id`
- segment or audience label
- churn probability or churn-risk tier where available
- CLV band or value band where available
- recommended action
- recommended product/category where applicable
- priority score
- campaign reason

Activation outputs are CRM-style, reverse-ETL-ready files that can support lifecycle targeting, campaign sizing, and downstream integration planning.

## 13. User Stories

| User story | Primary artifact |
|---|---|
| As a retention manager, I want a prioritized churn-risk customer list so that I can target high-value customers before they lapse. | `outputs/activation_churn_campaign.csv` |
| As a finance lead, I want return-adjusted margin by product so that I can separate revenue growth from profit quality. | `marts.mart_product_profitability`, `sql/analysis/product_margin_leakage.sql` |
| As a product manager, I want product affinity pairs so that I can identify cross-sell and bundle candidates. | `sql/analysis/product_affinity_cross_sell.sql` |
| As an executive stakeholder, I want a governed KPI scorecard so that revenue, churn, retention, and leakage are reported consistently. | `outputs/kpi_catalog.csv`, `dashboards/specs/dax_measure_catalog.md` |
| As a BI developer, I want a star-schema and semantic model plan so that Power BI/Tableau datasets can be built from consistent relationships. | `docs/dimensional_model.md`, `dashboards/specs/semantic_model_plan.md` |
| As a lifecycle manager, I want one-time buyer and win-back audiences so that campaign teams can test first-to-second purchase journeys. | `outputs/activation_winback_campaign.csv` |

## 14. Acceptance Criteria

| Requirement | Acceptance criteria |
|---|---|
| SQL analysis examples | At least 8 standalone SQL files exist under `sql/analysis/` with headers, CTEs, joins, CASE logic, aggregations, and business-friendly outputs. |
| Cleaning summary | `docs/data_cleaning_summary.md` documents required data issues, validation rules, actions, and output artifacts. |
| Business requirements | `docs/business_requirements.md` documents stakeholders, objectives, rules, user stories, acceptance criteria, UAT scenarios, and decision workflows. |
| Recommendations report | `reports/business_recommendations.md` clearly labels findings as synthetic/local simulation outputs and maps recommendations to owners, KPIs, marts, and risks. |
| Excel-style scorecard | `reports/excel/customer_intelligence_scorecard.xlsx` exists and contains multi-sheet KPI, churn, CLV, cohort, leakage, scenario, and dictionary views. |
| Semantic model proof | DAX measures and relationship guidance are documented under `dashboards/specs/`. |
| Final repo check | `make final-repo-check` passes and validates the new practical artifacts. |

## 15. UAT Scenarios

| Scenario | Test steps | Expected result |
|---|---|---|
| Executive KPI review | Open dashboard specs and scorecard workbook; compare KPI names to KPI catalog. | KPI names and business definitions are consistent. |
| Churn activation review | Inspect churn campaign export and churn SQL analysis. | Customer-level output includes risk signal, reason, and recommended action. |
| Product leakage review | Review product margin leakage SQL and product dashboard spec. | Products can be ranked by return-adjusted profit, return leakage, and discount dependency. |
| Cohort dashboard review | Review cohort SQL and cohort dashboard spec. | Month 1 through Month 12 retention is represented with cohort-month grain. |
| BI model review | Review semantic model plan and DAX measure catalog. | Facts, dimensions, relationship direction, date table, and measure table are defined. |
| Data quality review | Inspect cleaning summary, validation report, and output quality CSVs. | Known dirty-data conditions are accounted for by validation or rejection logic. |

## 16. Decision Workflows

### Retention Prioritization

1. Review churn risk and CLV outputs.
2. Filter to high CLV or high profit-at-risk customers.
3. Segment by acquisition channel, RFM group, and discount dependency.
4. Export customer list for lifecycle testing.
5. Monitor churn rate, repeat purchase rate, and retention investment priority score.

### Product Profitability Review

1. Rank products by return-adjusted profit.
2. Identify high-volume products with weak margin.
3. Separate return leakage from discount leakage.
4. Review product affinity pairs for bundle/cross-sell opportunities.
5. Monitor return-adjusted margin and revenue leakage trend.

### Acquisition Channel Quality Review

1. Compare channels by customers, repeat purchase rate, churn rate, profit, and CLV.
2. Flag channels with high volume but low value or weak retention.
3. Adjust channel investment based on customer quality, not only order count.
4. Monitor cohorts by channel over Month 1 through Month 12.

## 17. Assumptions

- Controlled synthetic data is generated to support repeatable customer, product, retention, profitability, and activation analysis.
- Churn and CLV outputs demonstrate model training, scoring, evaluation, and business interpretation workflows.
- A completed local Power BI `.pbix` dashboard is included; Tableau guidance can be built from the same governed marts.
- Full generated datasets are reproducible through the pipeline and intentionally kept lightweight in version control.

## 18. Implementation Scope

- Local execution is the default review environment, with clear extension paths for cloud orchestration and deployment.
- The data model, feature layer, and BI assets use generated ecommerce/SaaS data for reproducible local execution.
- Activation exports are reverse-ETL-ready files that mirror lifecycle and CRM targeting workflows.
- Performance notes document practical warehouse tuning patterns and can be expanded with database benchmarks during deployment extension.

## 19. Success Criteria

- Analysts can inspect advanced SQL examples and trace them to business questions.
- Business stakeholders can review requirements, workflows, recommendations, and action plans.
- BI developers can review the completed Power BI dashboard and build or extend BI models from documented marts, relationships, DAX measures, and dashboard specs.
- Repository checks pass after all role-aligned artifacts are added.
