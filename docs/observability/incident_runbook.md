# Data Incident Runbook

## Detection

Incidents can be detected by validation checks, schema contracts, model monitoring, orchestration failures, or stakeholder dashboard QA.

## Triage

1. Check `reports/orchestration_run_report.md`.
2. Check `reports/validation_report.md`.
3. Check `reports/schema_contract_report.md`.
4. Check `reports/model_monitoring_report.md`.
5. Identify owner and severity from the contract or severity matrix.

## Response

- P1: pause dashboard publication, notify BI and business owner, document the failure.
- P2: publish only after owner approval and add release note.
- P3: publish with release note if business impact is low.

## Recovery

- Re-run the failed module.
- Re-run `make advanced`.
- Re-run `python3 -m pytest`.
- Confirm updated reports and manifests show pass status.
