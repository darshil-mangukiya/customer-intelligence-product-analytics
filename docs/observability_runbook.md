# Observability Runbook

Runbook for pipeline health, freshness, validation, and scoring observability.

## Daily Checks

- Confirm pipeline manifest tasks completed.
- Review validation status and failing-row counts.
- Check row counts by stage.
- Review rejected-row counts and anomaly log.
- Confirm model scoring and dashboard marts are fresh.

## Dashboard Refresh Gate

- P1 schema contract or KPI reconciliation failures block dashboard refresh.
- P2 product/customer scoring failures require owner approval.
- Freshness failures publish only with a release note.

## Troubleshooting

- Use pipeline_audit_log.csv for task timing.
- Use mart_freshness_report.csv for stale assets.
- Use anomaly_log.csv for outlier investigation.
- Use validation_report.md for detailed failed checks.
