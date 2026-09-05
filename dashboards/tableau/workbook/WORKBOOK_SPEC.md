# Customer Intelligence & Product Analytics Workbook Contract

Final local artifacts: `Customer_Intelligence_Product_Analytics.twb` and `Customer_Intelligence_Product_Analytics.twbx`. All seven dashboards and all seven Story points manually rendered in Tableau Desktop 2026.1, the TWBX passed close/reopen validation, and the standalone TWB passed reopen validation after its path-only portability edit. The TWBX retains its native packaged `Data/data` paths, and the standalone TWB uses `../data` for all nine connections. Fixed dashboard size: 1366 × 768. Palette: navy `#17324D`, teal `#168AAD`, green `#2A9D8F`, amber `#E9C46A`, red `#C8553D`, neutral `#F4F6F8`. Red status also uses text/shape so color is never the only cue.

Every title or tooltip that could imply real impact must include “Synthetic portfolio data” or “Modeled / generated evidence.”

## Final implementation profile

The final workbook preserves this analytical contract while using a runtime-simple profile: 35 worksheets use direct governed presentation fields and one uses the safe Experiment Lift percentage-point calculation. The 16 core, eight LOD, seven table-calculation, and two helper definitions remain in the datasource catalog, but no final worksheet actively depends on an LOD, table calculation, or parameter. The four parameters remain defined and visible for the remaining Desktop interaction checks. `Product Leakage Risk` uses direct leakage metrics, and `Executive CLV Distribution` uses direct predicted CLV by segment.

| Dashboard | Business question | Worksheets | Filters / parameters | Required interaction |
|---|---|---|---|---|
| 1. Executive Overview | What is the customer, revenue, profit, retention, and risk picture? | 5 KPI cards, segment opportunity bars, risk/value scatter, decision note | Metric Selector, segment, channel | Segment filter action to Customer Segmentation and Churn & Retention; navigation buttons |
| 2. Customer Segmentation | Which segments combine value, risk, and migration signals? | segment bar, RFM heatmap, channel composition, migration flow/table | Metric Selector, segment, channel, loyalty tier | Highlight segment across views; navigate to churn |
| 3. Churn & Retention | Where is modeled risk concentrated and which aggregate groups merit review? | risk distribution, segment risk/value plot, top-K aggregate table, driver coefficient bars | Risk Threshold, Top N, segment, channel | Segment filter; Top-N parameter; associative-driver tooltip |
| 4. CLV Analysis | How do modeled 12-month value, historical value, and risk interact? | CLV histogram, historical-vs-modeled scatter, channel box plot, risk/value matrix | CLV band, channel, segment | Highlight band; customer hierarchy drill (aggregate only in portfolio screenshot) |
| 5. Cohort Retention | How does observed/generated retention evolve by acquisition cohort? | retention heatmap, retention curves, cohort size bars, period-change tooltip | cohort month, month index | Heatmap selects cohort and filters curves |
| 6. Product Profitability | Which products/categories have return-adjusted profit or leakage risk? | category summary, product rank, margin/return scatter, cumulative profit line | Top N, category, performance flag | Category → product drill; rank filtering |
| 7. Experiment & Decision Evidence | What does the synthetic experiment demonstrate statistically and practically? | variant rates, lift/CI interval, significance cards, sample-size/SRM note, scenario table | Experiment View | Parameter switches evidence emphasis; dashboard navigation only |

## Hierarchies

- Customer: `segment_name → clv_band → churn_risk_tier`.
- Product: `category → sub_category → product_name`.
- Time: `cohort_month → cohort_index` (do not fabricate quarter/day dimensions absent from the source).

## Parameters

| Parameter | Type / values | Default | Consumer |
|---|---|---|---|
| Metric Selector | String: Revenue, Profit, CLV, Churn Risk, Customer Count | Revenue | Segment metric calculation |
| Top N | Integer list: 5, 10, 20, 50 | 10 | Product and risk ranking |
| Risk Threshold | Float range 0.00–1.00, step 0.05 | 0.70 | Modeled High Risk |
| Experiment View | String: Absolute Lift, Relative Lift, Statistical Significance, Practical Significance | Absolute Lift | Experiment annotation/selector |

## Actions

The workbook contains the five filter/highlight actions below. The two Go-to-Sheet actions remain optional manual enhancements in Tableau Desktop.

1. `Executive Segment → Customer Segmentation Filter`: selected-field filter action on `segment_name`, run on select, clearing shows all; target every customer-source sheet on Customer Segmentation.
2. `Executive → Customer Segmentation Navigate`: Go to Sheet action from Executive Segment Opportunity to the Customer Segmentation dashboard, run on menu after the segment selection.
3. `Executive Segment → Churn & Retention Filter`: selected-field filter action on `segment_name`, run on select, clearing shows all; target every compatible customer-source sheet on Churn & Retention.
4. `Executive → Churn & Retention Navigate`: Go to Sheet action from Executive Segment Opportunity to the Churn & Retention dashboard, run on menu after the segment selection.
5. `Segment Highlight`: highlight action on `segment_name` across bars, channel composition, and migration table.
6. `Cohort Heatmap → Retention Curves`: filter action on `cohort_month`, run on select.
7. `Category → Product Detail`: filter action on `category`, run on select; hierarchy supports drill-down.
8. Navigation objects on every dashboard: Home, Previous, Next; include a visible Reset Filters instruction.

## Story: Customer Retention Decision Story

1. **Business context** — Executive Overview; generated data and decision-support boundary.
2. **Which customers matter most?** — Customer Segmentation; value and composition.
3. **Which customers are most at modeled risk?** — Churn & Retention; modeled associations, not causal drivers.
4. **What does generated cohort retention look like?** — Cohort Retention; generated cohort behavior.
5. **What does the synthetic experiment tell us?** — Experiment; synthetic assignment, lift, interval, p-value.
6. **Is the effect practically meaningful?** — Experiment with Practical Significance view.
7. **What action should be reviewed—not auto-activated?** — Executive/retention action summary; human review, no automatic activation.
