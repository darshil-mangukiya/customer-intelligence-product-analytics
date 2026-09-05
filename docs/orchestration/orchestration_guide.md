# Orchestration Guide

The orchestration layer simulates a production DAG with task dependencies, retries, SLA checks, and a run manifest.

Run sample orchestration:

```bash
python3 -m orchestration.dag_runner
```

Run downstream-only orchestration using existing marts:

```bash
python3 -m orchestration.dag_runner --downstream-only
```

Run full-refresh orchestration:

```bash
python3 -m orchestration.dag_runner --full-refresh
```

Outputs:

- `data/audit/orchestration_run_manifest.csv`
- `reports/orchestration_run_report.md`

Task order:

1. Analytics pipeline
2. Data validation
3. Model monitoring
4. Model registry
5. Executive one-page PDF
