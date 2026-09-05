# Data Validation Expectation Suite

This project uses a lightweight Great Expectations-style validation framework in `validation/validate_data.py`.

## Suites

- `raw_volume`: validates full-scale source data volume.
- `key_integrity`: validates primary keys, uniqueness, and required IDs.
- `numeric_ranges`: validates probabilities, rates, revenue, and retention ranges.
- `accepted_values`: validates governed categorical values.
- `referential_integrity`: validates fact-to-dimension joins.
- `metric_reconciliation`: validates KPI export totals against fact tables.
- `freshness`: validates that pipeline outputs are recent.

## Outputs

- `data/exports/validation_results.csv`
- `reports/validation_report.md`

## How to Run

```bash
python3 -m validation.validate_data
```
