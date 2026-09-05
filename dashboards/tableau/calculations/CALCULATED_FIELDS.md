# Tableau Calculated-field Catalog

These fields support visualization and interaction without redefining governed KPIs. Fields marked **LOD** or **table calculation** require the addressing and partitioning described below. Currency calculations use generated project data. In the final workbook, all definitions remain available, but only Experiment Absolute Lift is used by a worksheet; prepared presentation fields replace active LOD, table-calculation, and parameter dependencies.

| Name | Tableau expression | Meaning / grain | Source fields | Validation |
|---|---|---|---|---|
| Customer Count | `COUNTD([customer_id])` | Distinct customers in the current view | customer_id | `total_customers` |
| Revenue per Customer | `SUM([net_revenue]) / COUNTD([customer_id])` | Revenue per distinct customer | net_revenue, customer_id | customer source aggregate |
| Profit per Customer | `SUM([return_adjusted_profit]) / COUNTD([customer_id])` | Return-adjusted profit per customer | return_adjusted_profit, customer_id | customer source aggregate |
| Observed Churn Rate | `AVG(FLOAT([churn_label]))` | Observed/generated churn-label share; customer grain | churn_label | KPI summary |
| Observed Retention Rate | `1 - [Observed Churn Rate]` | Complement of observed churn label | churn_label | KPI summary |
| Modeled High Risk | `IF [churn_probability] >= [Risk Threshold] THEN "Above threshold" ELSE "Below threshold" END` | Parameter-driven modeled risk status | churn_probability | threshold count |
| Risk × Value Score | `[churn_probability] * [predicted_12m_clv]` | Modeled prioritization score, not causal | churn_probability, predicted_12m_clv | row spot-check |
| Metric Selector Value | `CASE [Metric Selector] WHEN "Revenue" THEN SUM([net_revenue]) WHEN "Profit" THEN SUM([return_adjusted_profit]) WHEN "CLV" THEN AVG([predicted_12m_clv]) WHEN "Churn Risk" THEN AVG([churn_probability]) WHEN "Customer Count" THEN COUNTD([customer_id]) END` | Switches the segment view metric | governed customer fields | dashboard cross-check |
| CLV Band (Display) | `IFNULL([clv_band], "Unknown")` | Display-safe label that preserves the governed model output instead of redefining its thresholds in Tableau | clv_band | exact match to governed `clv_band` |
| Product Return Rate | `SUM([returns]) / SUM([orders])` | Returned orders/items proxy per governed product mart | returns, orders | product aggregate |
| Profit Margin | `SUM([return_adjusted_profit]) / SUM([net_revenue])` | Return-adjusted margin | profit, revenue | product aggregate |
| Experiment Absolute Lift | `MAX([absolute_difference]) * 100` | Treatment minus control conversion rate, converted to percentage points for display | absolute_difference | `2.780782 pp` from governed rate `0.02780782` |
| Experiment Relative Lift | `MAX([relative_lift])` | Absolute lift divided by control rate | relative_lift | experiment evaluation |
| Statistical Status | `IF MAX([p_value]) < MAX([alpha]) THEN "Statistically significant" ELSE "Not statistically significant" END` | Statistical threshold status | p_value, alpha | experiment evaluation |
| Practical Status | `IF ABS(MAX([absolute_difference])) >= MAX([practical_threshold]) THEN "Practically significant" ELSE "Below practical threshold" END` | Practical threshold status | lift, threshold | experiment evaluation |
| Confidence Interval Label | `STR(ROUND(MAX([confidence_interval_low]) * 100, 2)) + "% to " + STR(ROUND(MAX([confidence_interval_high]) * 100, 2)) + "%"` | 95% CI display | CI bounds | experiment evaluation |

## Level-of-detail expressions

| Name | Tableau expression | Why LOD is appropriate | Validation reference |
|---|---|---|---|
| Customer Lifetime Revenue (LOD) | `{ FIXED [customer_id] : MAX([net_revenue]) }` | Keeps one governed customer value stable under view dimensions | sum equals total customer revenue |
| Customer Lifetime Profit (LOD) | `{ FIXED [customer_id] : MAX([return_adjusted_profit]) }` | Prevents duplication when additional dimensions enter the view | sum equals total customer profit |
| Segment Customer Count (LOD) | `{ FIXED [segment_name] : COUNTD([customer_id]) }` | Stable segment denominator for shares and tooltips | segment counts sum to 5,000 |
| Segment Revenue (LOD) | `{ FIXED [segment_name] : SUM([net_revenue]) }` | Stable governed revenue by segment | group-by reconciliation |
| All-customer Revenue (LOD) | `{ FIXED : SUM([net_revenue]) }` | Denominator for segment revenue share | total customer revenue |
| Segment Revenue Share (LOD) | `[Segment Revenue (LOD)] / [All-customer Revenue (LOD)]` | Reusable fixed denominator | segment shares sum to 1 |
| Cohort Size (LOD) | `{ FIXED [cohort_month] : MAX([cohort_size]) }` | Cohort denominator remains fixed across month index | source cohort_size |
| Category Revenue (LOD) | `{ FIXED [category] : SUM([net_revenue]) }` | Stable category denominator for product shares | product group-by aggregate |

Use FIXED expressions deliberately: context filters affect the LOD; ordinary dimension filters generally do not. Put `data_context` and intended global date filters in context only after verifying expected behavior.

## Table calculations

| Name | Expression | Compute using / partition | Use |
|---|---|---|---|
| Segment Percent of Total | `SUM([net_revenue]) / TOTAL(SUM([net_revenue]))` | Table across segment; restart per selected metric pane | Segment mix |
| Product Rank | `RANK_DENSE(SUM([return_adjusted_profit]), 'desc')` | Product within category | Top-N profitability |
| Cumulative Profit | `RUNNING_SUM(SUM([return_adjusted_profit]))` | Product sorted descending; restart per category | Concentration curve |
| Cohort Retention % | `SUM([active_customers]) / MIN([cohort_size])` | Table across cohort_index; partition by cohort_month | Cohort heatmap |
| Retention Period Change | `[Cohort Retention %] - LOOKUP([Cohort Retention %], -1)` | Table across cohort_index; partition by cohort_month | Period change tooltip |
| Three-period Moving Retention | `WINDOW_AVG([Cohort Retention %], -2, 0)` | Table across cohort_index; partition by cohort_month | Retention curve smoothing |
| Conversion Rate Difference | `LOOKUP(AVG([conversion_rate]), 0) - LOOKUP(AVG([conversion_rate]), -1)` | Variant order: Control, Retention Offer | Variant comparison |

For every table calculation, open **Edit Table Calculation → Specific Dimensions**, check only the addressing dimension named above, and visually confirm the partition boundary.
