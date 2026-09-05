# PostgreSQL Execution Report

This report records local execution against PostgreSQL using deterministic synthetic P3 data.

- Schemas observed: 9
- Tables/views observed: 37
- Rows across observed relations: 223,186
- Primary keys observed: 6
- Foreign keys observed: 6
- Reconciliation: PASS

## Reconciliation

| Metric | Local | PostgreSQL | Difference | Tolerance | Status |
|---|---:|---:|---:|---:|---|
| customer_count | 5000.000000 | 5000.000000 | 0.000000 | 0.000000 | PASS |
| transaction_count | 25037.000000 | 25037.000000 | 0.000000 | 0.000000 | PASS |
| gross_revenue | 2367053.785350 | 2367053.785350 | 0.000000 | 0.010000 | PASS |
| product_count | 250.000000 | 250.000000 | 0.000000 | 0.000000 | PASS |
| segment_population | 5000.000000 | 5000.000000 | 0.000000 | 0.000000 | PASS |
| churn_population | 5000.000000 | 5000.000000 | 0.000000 | 0.000000 | PASS |
| predicted_12m_clv | 1079464.097140 | 1079464.097140 | 0.000000 | 0.010000 | PASS |
| experiment_population | 3511.000000 | 3511.000000 | 0.000000 | 0.000000 | PASS |

All experiment records and outcomes are synthetic; no real customer experiment is represented.
