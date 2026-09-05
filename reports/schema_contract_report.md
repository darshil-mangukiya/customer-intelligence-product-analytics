# Schema Contract Report

> Evidence profile: `full_250k` (250,000 customers) — full-volume schema and lifecycle evidence; not authoritative for current 5K model KPIs.

- Contracts evaluated: 6
- Passing contracts: 6
- Failing contracts: 0

| Table | Status | Severity | Owner | Rows | Missing Columns | Duplicate Keys |
|---|---|---|---|---:|---|---:|
| fact_orders | PASS | P1 | BI Engineering | 1,050,000 |  | 0 |
| mart_churn_risk | PASS | P1 | Customer Analytics | 250,000 |  | 0 |
| mart_clv | PASS | P1 | Customer Analytics | 250,000 |  | 0 |
| mart_product_profitability | PASS | P2 | Product Analytics | 1,500 |  | 0 |
| kpi_summary | PASS | P1 | BI Engineering | 16 |  | 0 |
| next_best_actions | PASS | P2 | Lifecycle Marketing | 250,000 |  | 0 |

## Incident Rules
- P1 failures block executive dashboard refreshes.
- P2 failures require data-steward review before downstream publication.
- P3 failures can publish with a release note when business impact is low.
