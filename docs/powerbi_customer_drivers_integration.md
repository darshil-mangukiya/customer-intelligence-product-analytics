# Power BI: Customer Drivers & Experiment Insights

The existing PBIX was not edited. A future refresh can import these Power BI-ready CSV files from `data/exports`:

- `statistical_test_results.csv`
- `descriptive_statistics.csv`
- `experiment_evaluation.csv`
- `churn_driver_analysis.csv`
- `clv_driver_analysis.csv`
- `regression_analysis.csv`

Recommended page elements are an experiment absolute-lift card, interval endpoints, statistical/practical-significance indicators, churn and CLV driver ranking bars, a question-level comparison table, and a recommendation/KPI table. Keep driver charts sorted by `importance_or_strength`; show direction separately so bar magnitude is not confused with favorable impact. Add a visible synthetic-data and non-causality note.

Suggested relationships are unnecessary because each file is a purpose-built, pre-aggregated analytical output. If the semantic model requires a shared refresh dimension, use `generated_at` as audit metadata, not a business event date.
