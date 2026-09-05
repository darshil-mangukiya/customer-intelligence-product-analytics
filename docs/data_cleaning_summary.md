# Data Cleaning Summary

This summary documents the before-and-after treatment of common raw-data issues in the local synthetic ecommerce/SaaS analytics pipeline. The goal is to make the cleaning layer auditable before data is used in feature engineering, marts, dashboards, API responses, or activation exports.

| Data issue | Example bad value | Cleaning or validation rule | Resulting action | Output artifact |
|---|---|---|---|---|
| Missing customer ID | `customer_id = NULL` in an order row | Orders must have a non-null customer key before joining to `dim_customer`. | Reject or flag the row before mart load; exclude from customer features. | `outputs/rejected_rows.csv`, `outputs/data_quality_summary.csv` |
| Missing product ID | `product_id = ''` on a completed transaction | Completed order rows require a valid product key. | Reject or flag row; prevent product profitability distortion. | `outputs/rejected_rows.csv`, `sql/postgres/quality_checks.sql` |
| Duplicate order | Same `order_id` appears more than once | Order grain is one row per `order_id`; duplicate keys are removed or flagged. | Keep deterministic clean record and count duplicate removals in audit output. | `outputs/pipeline_audit_log.csv` |
| Negative revenue | `revenue = -49.99` with completed status | Completed order revenue must be non-negative; returns are represented through `return_flag` and `return_loss`. | Flag as invalid revenue; exclude from revenue KPI calculations. | `outputs/anomaly_log.csv`, `outputs/rejected_rows.csv` |
| Invalid order date | `order_date` before customer signup or outside simulation window | Order dates must be plausible and not before customer acquisition. | Flag impossible date and exclude from cohort base. | `reports/validation_report.md` |
| Inconsistent category/channel labels | `Paid Search`, `paid_search`, `Paid search` | Standardize labels to governed channel/category values. | Normalize values before joining to dashboard marts. | `docs/data_dictionary.md`, `outputs/data_quality_summary.csv` |
| Broken foreign keys | Order customer not present in customer table | Facts must resolve to valid dimension keys. | Flag referential integrity issue and prevent invalid fact-to-dimension reporting. | `sql/postgres/quality_checks.sql`, `outputs/data_quality_summary.csv` |
| Invalid churn labels | `churn_label = maybe` | Churn label must resolve to binary or governed status values. | Flag invalid label and keep out of model base. | `outputs/rejected_rows.csv`, `docs/data_quality_framework.md` |
| Outlier discount values | Discount greater than order revenue | Discount rate must stay within accepted business bounds. | Flag anomaly; include in discount-leakage monitoring. | `outputs/anomaly_log.csv`, `sql/analysis/customer_discount_sensitivity.sql` |
| Unusual return rates | Product return rate spikes above expected threshold | Product and category return rates are monitored against threshold rules. | Flag product/category for margin leakage review. | `outputs/anomaly_log.csv`, `sql/analysis/product_margin_leakage.sql` |

## Before And After Summary

| Layer | Before cleaning | After cleaning |
|---|---|---|
| Raw transactions | Duplicates, missing keys, negative values, inconsistent labels, return noise | Normalized order facts with return-adjusted revenue, return loss, discount amount, and completed-order flags |
| Customer records | Inconsistent acquisition labels, invalid churn values, nullable behavior fields | Standardized customer dimension and customer value features |
| Product records | Category/sub-category variation and inconsistent product attributes | Product dimension with category, lifecycle, margin, return, and retention profiles |
| Web/session data | Odd page-view depth, bounce inconsistencies, device/traffic source variation | Session facts with standardized device/source labels and odd-session flags |
| Reporting marts | Not available from raw sources | BI-ready customer, product, cohort, churn, CLV, KPI, and activation outputs |

## Audit Trail

Cleaning and validation outputs are designed to answer three questions:

1. Which rows were rejected or flagged?
2. Which data-quality checks passed or failed?
3. Which downstream marts and model outputs are fresh enough for reporting?

Primary artifacts:

- `outputs/data_quality_summary.csv`
- `outputs/rejected_rows.csv`
- `outputs/anomaly_log.csv`
- `outputs/pipeline_audit_log.csv`
- `outputs/mart_freshness_report.csv`
- `reports/validation_report.md`
