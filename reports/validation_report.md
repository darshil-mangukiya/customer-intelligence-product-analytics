# Validation Report

- Total checks: 69
- Passing checks: 64
- Failing checks: 5

| Suite | Table | Expectation | Column | Status | Observed | Threshold | Failing Rows | Severity |
|---|---|---|---|---|---|---|---:|---|
| raw_volume | transactions | `expect_table_row_count_to_be_at_least` | `*` | FAIL | 25,037 | >= 1,000,000 | 974963 | HIGH |
| raw_volume | customers | `expect_table_row_count_to_be_at_least` | `*` | FAIL | 5,000 | >= 100,000 | 95000 | HIGH |
| raw_volume | products | `expect_table_row_count_to_be_at_least` | `*` | FAIL | 250 | >= 1,000 | 750 | HIGH |
| raw_volume | web_behavior | `expect_table_row_count_to_be_at_least` | `*` | FAIL | 18,018 | >= 500,000 | 481982 | HIGH |
| raw_volume | engagement | `expect_table_row_count_to_be_at_least` | `*` | FAIL | 5,000 | >= 100,000 | 95000 | HIGH |
| key_integrity | dim_customer | `expect_column_values_to_be_unique` | `customer_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | dim_customer | `expect_column_values_to_not_be_null` | `customer_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | dim_product | `expect_column_values_to_be_unique` | `product_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | dim_product | `expect_column_values_to_not_be_null` | `product_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | fact_orders | `expect_column_values_to_be_unique` | `order_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | fact_orders | `expect_column_values_to_not_be_null` | `order_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | mart_churn_risk | `expect_column_values_to_be_unique` | `customer_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | mart_churn_risk | `expect_column_values_to_not_be_null` | `customer_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | mart_clv | `expect_column_values_to_be_unique` | `customer_id` | PASS | 0 | = 0 | 0 | HIGH |
| key_integrity | mart_clv | `expect_column_values_to_not_be_null` | `customer_id` | PASS | 0 | = 0 | 0 | HIGH |
| numeric_ranges | fact_orders | `expect_column_values_to_be_between` | `net_revenue` | PASS | min=0.0000, max=8871.5188 | 0 to inf | 0 | HIGH |
| numeric_ranges | mart_churn_risk | `expect_column_values_to_be_between` | `churn_probability` | PASS | min=0.0000, max=1.0000 | 0 to 1 | 0 | HIGH |
| numeric_ranges | mart_cohort_retention | `expect_column_values_to_be_between` | `retention_rate` | PASS | min=0.0149, max=1.0000 | 0 to 1 | 0 | HIGH |
| numeric_ranges | mart_product_profitability | `expect_column_values_to_be_between` | `return_rate` | PASS | min=0.0345, max=0.4667 | 0 to 1 | 0 | HIGH |
| accepted_values | fact_orders | `expect_column_values_to_be_in_set` | `order_status` | PASS | 0 invalid | ['Cancelled', 'Completed', 'Returned', 'Unknown'] | 0 | HIGH |
| analytical_outputs | descriptive_statistics | `expect_output_file_to_exist` | `*` | PASS | True | True | 0 | HIGH |
| analytical_outputs | descriptive_statistics | `expect_required_columns_to_exist` | `*` | PASS | none | none missing | 0 | HIGH |
| analytical_outputs | descriptive_statistics | `expect_analytical_ids_to_be_unique` | `_compound_key` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | statistical_test_results | `expect_output_file_to_exist` | `*` | PASS | True | True | 0 | HIGH |
| analytical_outputs | statistical_test_results | `expect_required_columns_to_exist` | `*` | PASS | none | none missing | 0 | HIGH |
| analytical_outputs | statistical_test_results | `expect_analytical_ids_to_be_unique` | `analysis_id` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | statistical_test_results | `expect_p_values_between_zero_and_one` | `p_value` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | statistical_test_results | `expect_confidence_interval_ordering` | `confidence_interval_low` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | experiment_evaluation | `expect_output_file_to_exist` | `*` | PASS | True | True | 0 | HIGH |
| analytical_outputs | experiment_evaluation | `expect_required_columns_to_exist` | `*` | PASS | none | none missing | 0 | HIGH |
| analytical_outputs | experiment_evaluation | `expect_analytical_ids_to_be_unique` | `experiment_id` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | experiment_evaluation | `expect_p_values_between_zero_and_one` | `p_value` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | experiment_evaluation | `expect_confidence_interval_ordering` | `confidence_interval_low` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | churn_driver_analysis | `expect_output_file_to_exist` | `*` | PASS | True | True | 0 | HIGH |
| analytical_outputs | churn_driver_analysis | `expect_required_columns_to_exist` | `*` | PASS | none | none missing | 0 | HIGH |
| analytical_outputs | churn_driver_analysis | `expect_analytical_ids_to_be_unique` | `metric_or_driver` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | churn_driver_analysis | `expect_p_values_between_zero_and_one` | `p_value` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | churn_driver_analysis | `expect_confidence_interval_ordering` | `confidence_interval_low` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | clv_driver_analysis | `expect_output_file_to_exist` | `*` | PASS | True | True | 0 | HIGH |
| analytical_outputs | clv_driver_analysis | `expect_required_columns_to_exist` | `*` | PASS | none | none missing | 0 | HIGH |
| analytical_outputs | clv_driver_analysis | `expect_analytical_ids_to_be_unique` | `metric_or_driver` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | clv_driver_analysis | `expect_p_values_between_zero_and_one` | `p_value` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | clv_driver_analysis | `expect_confidence_interval_ordering` | `confidence_interval_low` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | regression_analysis | `expect_output_file_to_exist` | `*` | PASS | True | True | 0 | HIGH |
| analytical_outputs | regression_analysis | `expect_required_columns_to_exist` | `*` | PASS | none | none missing | 0 | HIGH |
| analytical_outputs | regression_analysis | `expect_analytical_ids_to_be_unique` | `predictor` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | regression_analysis | `expect_p_values_between_zero_and_one` | `p_value` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_outputs | regression_analysis | `expect_confidence_interval_ordering` | `ci_low` | PASS | 0 | = 0 | 0 | HIGH |
| analytical_reports | statistical_analysis_report.md | `expect_generated_report_to_exist` | `*` | PASS | True | True and >500 bytes | 0 | HIGH |
| analytical_reports | executive_customer_strategy.md | `expect_generated_report_to_exist` | `*` | PASS | True | True and >500 bytes | 0 | HIGH |
| r_statistical_validation | r_experiment_validation | `expect_required_columns_to_exist` | `*` | PASS | none | none missing | 0 | HIGH |
| r_statistical_validation | r_experiment_validation | `expect_p_values_between_zero_and_one` | `p_value` | PASS | 0 | = 0 | 0 | HIGH |
| r_statistical_validation | python_r_statistical_reconciliation | `expect_required_metrics_to_pass` | `status` | PASS | failed=0, missing=[] | no failures or missing metrics | 0 | HIGH |
| accepted_values | mart_churn_risk | `expect_column_values_to_be_in_set` | `churn_risk_tier` | PASS | 0 invalid | ['Critical', 'High', 'Low', 'Medium'] | 0 | HIGH |
| referential_integrity | fact_orders | `expect_foreign_key_to_exist` | `customer_id` | PASS | 0 missing customer keys | all customer_id values in dim_customer | 0 | HIGH |
| referential_integrity | fact_orders | `expect_foreign_key_to_exist` | `product_id` | PASS | 0 missing product keys | all product_id values in dim_product | 0 | HIGH |
| metric_reconciliation | fact_orders | `expect_total_net_revenue_to_match_kpi_export` | `net_revenue` | PASS | delta=0.00 | <= 1.00 | 0 | HIGH |
| freshness | pipeline_run_manifest | `expect_pipeline_outputs_to_be_recent` | `modified_time` | PASS | 3 days old | <= 14 days | 0 | MEDIUM |
| customer_intelligence_upgrade | experiment_design.csv | `expect_generated_output_to_exist_and_be_nonempty` | `*` | PASS | 249 | > 20 bytes | 0 | HIGH |
| customer_intelligence_upgrade | experiment_srm_validation.csv | `expect_generated_output_to_exist_and_be_nonempty` | `*` | PASS | 279 | > 20 bytes | 0 | HIGH |
| customer_intelligence_upgrade | segment_migration_summary.csv | `expect_generated_output_to_exist_and_be_nonempty` | `*` | PASS | 4330 | > 20 bytes | 0 | HIGH |
| customer_intelligence_upgrade | retention_economics_scenarios.csv | `expect_generated_output_to_exist_and_be_nonempty` | `*` | PASS | 1731 | > 20 bytes | 0 | HIGH |
| customer_intelligence_upgrade | retention_action_center.csv | `expect_generated_output_to_exist_and_be_nonempty` | `*` | PASS | 4908 | > 20 bytes | 0 | HIGH |
| customer_intelligence_upgrade | customer_intelligence_reconciliation.csv | `expect_generated_output_to_exist_and_be_nonempty` | `*` | PASS | 310 | > 20 bytes | 0 | HIGH |
| customer_intelligence_upgrade | ai_evaluation_results.csv | `expect_generated_output_to_exist_and_be_nonempty` | `*` | PASS | 1019 | > 20 bytes | 0 | HIGH |
| reconciliation | customer_intelligence_reconciliation | `expect_all_source_output_checks_to_pass` | `status` | PASS | 0 failed | 0 failed | 0 | HIGH |
| customer_intelligence_upgrade | latest_customer_insight_packet | `expect_governed_finite_aggregate_packet` | `schema` | PASS | True | required keys; no IDs/NaN/Infinity | 0 | HIGH |
| business_analysis | business_analysis/requirements_traceability_matrix.xlsx | `expect_real_xlsx_artifact` | `file` | PASS | 8254 | > 5,000 bytes | 0 | HIGH |
| business_analysis | business_analysis/uat_test_plan.xlsx | `expect_real_xlsx_artifact` | `file` | PASS | 9077 | > 5,000 bytes | 0 | HIGH |

## Failed Checks
- transactions.*: expect_table_row_count_to_be_at_least failed with 25,037.
- customers.*: expect_table_row_count_to_be_at_least failed with 5,000.
- products.*: expect_table_row_count_to_be_at_least failed with 250.
- web_behavior.*: expect_table_row_count_to_be_at_least failed with 18,018.
- engagement.*: expect_table_row_count_to_be_at_least failed with 5,000.
