# Power BI Semantic Model and DAX Measure Catalog

Recommended star schema relationships:
- `fact_orders[customer_id]` to `dim_customer[customer_id]`
- `fact_orders[product_id]` to `dim_product[product_id]`
- `fact_orders[date_key]` to `dim_date[date_key]`
- `fact_sessions[customer_id]` to `dim_customer[customer_id]`
- `fact_customer_value[customer_id]` to `dim_customer[customer_id]`

```DAX
Total Net Revenue = SUM(fact_orders[net_revenue])
Return Adjusted Profit = SUM(fact_orders[return_adjusted_profit])
Return Adjusted Margin = DIVIDE([Return Adjusted Profit], [Total Net Revenue])
Completed Orders = CALCULATE(DISTINCTCOUNT(fact_orders[order_id]), fact_orders[is_completed_order] = TRUE())
Average Order Value = DIVIDE([Total Net Revenue], [Completed Orders])
Customers = DISTINCTCOUNT(dim_customer[customer_id])
Repeat Purchase Rate = AVERAGE(fact_customer_value[repeat_purchase_flag])
Churn Rate = AVERAGE(fact_customer_value[churn_label])
Retention Rate = 1 - [Churn Rate]
Return Rate = DIVIDE(CALCULATE(DISTINCTCOUNT(fact_orders[order_id]), fact_orders[return_flag] = TRUE()), DISTINCTCOUNT(fact_orders[order_id]))
Revenue Leakage = SUM(fact_orders[return_loss]) + SUM(fact_orders[discount_amount])
Predicted CLV = AVERAGE(mart_clv[predicted_12m_clv])
Cohort Retention % = AVERAGE(fact_cohort_retention[retention_rate])
```
