# Semantic Layer

The semantic layer centralizes metric definitions so dashboard builders do not recreate inconsistent logic.

## Metric Ownership

- Customer Analytics owns churn, retention, CLV, RFM, and lifecycle KPIs.
- Finance Analytics owns revenue, margin, leakage, and profitability KPIs.
- Product Analytics owns return, affinity, lifecycle, and category performance KPIs.
- BI Engineering owns semantic consistency and dashboard publication rules.

## Consumption Pattern

- Power BI and Tableau use marts and semantic measure logic instead of raw transactional calculations.
- Streamlit and FastAPI expose the same governed definitions.
- Activation outputs use scored marts and priority scores, not ad hoc campaign rules.

## Governance

- Metric grain, owner, formula, refresh cadence, and thresholds are documented in outputs/kpi_catalog.csv.
- Dashboard QA should compare KPI cards against kpi_summary.csv and mart reconciliation checks.
