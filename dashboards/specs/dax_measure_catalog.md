# DAX Measure Catalog

This catalog provides Power BI-ready measure definitions for the semantic model used by the completed local `.pbix` dashboard and future BI extensions.

## Measures

| Measure name | DAX formula | Business definition | Source mart/table | Expected filter behavior | Dashboard usage |
|---|---|---|---|---|---|
| Orders | `Orders = DISTINCTCOUNT(fact_orders[order_id])` | Count of unique orders in the current filter context. | `fact_orders` | Filters by date, customer, product, channel, region, and order status context. | Executive, product, customer |
| Completed Orders | `Completed Orders = CALCULATE([Orders], fact_orders[is_completed_order] = TRUE())` | Count of completed orders eligible for revenue and purchase behavior. | `fact_orders` | Honors all slicers and adds completed-order filter. | Executive, AOV, retention |
| Customers | `Customers = DISTINCTCOUNT(dim_customer[customer_id])` | Count of customers in the current dimension context. | `dim_customer` | Filters by customer attributes and related fact filters where relationships apply. | Executive, customer overview |
| Returned Orders | `Returned Orders = CALCULATE([Orders], fact_orders[return_flag] = TRUE())` | Count of orders marked as returned. | `fact_orders` | Honors date, product, customer, and channel filters. | Product and revenue leakage |
| Segment Revenue | `Segment Revenue = [Revenue]` | Revenue in the selected segment context. | `fact_orders`, `dim_customer` | Depends on active segment/customer filters. | Segment strategy |
| Total Revenue All Segments | `Total Revenue All Segments = CALCULATE([Revenue], ALL(dim_customer[segment_seed]))` | Revenue denominator for segment contribution. | `fact_orders`, `dim_customer` | Removes segment filter while preserving other report context. | Segment strategy |
| Revenue | `Revenue = SUM(fact_orders[net_revenue])` | Net selling revenue after discounts and order status logic. | `fact_orders` | Filters by date, product, customer, channel, and region. | Executive, product, customer, channel |
| Gross Profit | `Gross Profit = SUM(fact_orders[gross_revenue]) - SUM(fact_orders[cost])` | Profit before return adjustment. | `fact_orders` | Filters by the same dimensions as revenue. | Executive, finance review |
| Net Profit | `Net Profit = SUM(fact_orders[return_adjusted_profit])` | Profit after return adjustment. | `fact_orders` | Filters by date, product, customer, channel, and region. | Executive, product profitability |
| Margin % | `Margin % = DIVIDE([Net Profit], [Revenue])` | Return-adjusted profit divided by revenue. | `fact_orders` | Safe division in current report context. | Executive KPI cards, product dashboards |
| Return-Adjusted Revenue | `Return-Adjusted Revenue = [Revenue] - [Revenue Leakage from Returns]` | Revenue after subtracting return leakage. | `fact_orders` | Filters by product, category, customer, channel, and date. | Revenue leakage, product profitability |
| Return-Adjusted Profit | `Return-Adjusted Profit = SUM(fact_orders[return_adjusted_profit])` | Profit after returns and discounts. | `fact_orders` | Same context as revenue. | Executive, product, finance |
| Churn Rate | `Churn Rate = AVERAGE(fact_customer_value[churn_label])` | Share of customers labeled as churned/lapsed in the current context. | `fact_customer_value` | Filters by customer attributes and segment context. | Churn dashboard, executive overview |
| Retention Rate | `Retention Rate = 1 - [Churn Rate]` | Complement of churn rate. | `fact_customer_value` | Same context as churn rate. | Customer overview, executive overview |
| Repeat Purchase Rate | `Repeat Purchase Rate = AVERAGE(fact_customer_value[repeat_purchase_flag])` | Share of customers with repeat purchase behavior. | `fact_customer_value` | Filters by customer dimensions and report context. | Customer overview, lifecycle reporting |
| Average Order Value | `Average Order Value = DIVIDE([Revenue], [Completed Orders])` | Net revenue per completed order. | `fact_orders` | Uses current revenue and completed order filters. | Executive, customer, channel |
| CLV | `CLV = AVERAGE(fact_customer_value[historical_clv])` | Average historical customer lifetime value. | `fact_customer_value` | Filters by customer attributes, segment, and channel. | CLV dashboard |
| Predicted CLV | `Predicted CLV = AVERAGE(mart_clv[predicted_12m_clv])` | Average predicted 12-month CLV from the local scoring output when loaded. | `mart_clv` or CLV output | Filters by customer, segment, channel, and CLV band if loaded. | CLV dashboard, retention prioritization |
| Return Rate | `Return Rate = DIVIDE([Returned Orders], [Orders])` | Share of orders with return flag. | `fact_orders` | Filters by product, category, customer, date, and channel. | Product dashboard, revenue leakage |
| Discount Rate | `Discount Rate = DIVIDE(SUM(fact_orders[discount_amount]), SUM(fact_orders[gross_revenue]))` | Discount amount as a share of gross revenue. | `fact_orders` | Filters by product, customer, channel, and date. | Revenue leakage, product dashboards |
| Cohort Retention % | `Cohort Retention % = DIVIDE(SUM(fact_cohort_retention[customers]), SUM(fact_cohort_retention[cohort_customers]))` | Active cohort customers divided by original cohort size. | `fact_cohort_retention` | Filters by cohort month and cohort index. | Cohort retention dashboard |
| Revenue Leakage from Returns | `Revenue Leakage from Returns = SUM(fact_orders[return_loss])` | Revenue lost to returns. | `fact_orders` | Filters by product, customer, channel, region, and date. | Revenue leakage, product profitability |
| Revenue Leakage from Discounts | `Revenue Leakage from Discounts = SUM(fact_orders[discount_amount])` | Revenue reduced through discounts. | `fact_orders` | Filters by product, customer, channel, region, and date. | Revenue leakage, finance review |
| Segment Contribution % | `Segment Contribution % = DIVIDE([Segment Revenue], [Total Revenue All Segments])` | Selected segment revenue divided by total revenue across segments. | `fact_orders`, `dim_customer` | Keeps non-segment filters while removing segment filter in denominator. | Segment strategy |
| Product Affinity Score | `Product Affinity Score = MAX(mart_product_affinity[affinity_score])` | Maximum affinity score for the selected product/category pair when affinity mart is loaded. | `mart_product_affinity` or affinity output | Filters by source and recommended product/category. | Product affinity and cross-sell |

## Implementation Notes

- Use base measures such as `Orders`, `Completed Orders`, `Customers`, `Returned Orders`, and `Revenue` inside dependent measures.
- Keep formulas in a dedicated `Measures` table.
- Avoid visual-level calculations when a governed measure exists in this catalog.
- Validate KPI cards against `outputs/kpi_catalog.csv` and SQL outputs before publishing a dashboard.
- For local CSV imports, verify column names match the table names used in these formulas.
