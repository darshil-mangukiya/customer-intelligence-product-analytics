# Dashboard QA Checklist

QA checklist for dashboard release readiness.

## Data

- KPI cards reconcile to kpi_summary.csv.
- Marts are fresh and pass schema contracts.
- Dashboard row counts match mart row counts at the intended grain.

## UX

- Filters, tooltips, drilldowns, and empty states are tested.
- High-risk customer and product tables sort by business priority.
- Dashboard copy uses the repository's generated-data scope and governed metric definitions consistently.

## Release

- Stakeholder UAT signoff is captured before publishing.
