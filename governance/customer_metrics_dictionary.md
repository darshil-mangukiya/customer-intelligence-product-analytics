# Customer Metrics Dictionary

All definitions apply to deterministic synthetic data. Grain is customer unless noted.

| Metric | Definition / formula | Grain | Source | Exclusions / validation | Output |
|---|---|---|---|---|---|
| Customer | Unique `customer_id` in governed features | Customer | `customer_features.csv` | Non-null, unique | Customer 360 |
| Active Customer | Customer with qualifying activity inside the governed recency window | Customer | enriched transactions | Valid dates/orders | KPI exports |
| Repeat Customer | Customer with more than one distinct order | Customer | enriched transactions | Valid order IDs | customer features |
| Retained Customer | Customer satisfying the lifecycle retention rule | Customer/cohort | lifecycle mart | Eligible observation window | retention outputs |
| Churned Customer | Deterministic churn label under the configured inactivity rule | Customer | customer features | Analysis-date rule | churn mart |
| Churn Rate | churned customers / eligible customers | Population | churn mart | Denominator > 0 | KPI summary |
| Retention Rate | 1 − churn rate | Population | churn mart | Reconciles to churn | KPI summary |
| Recency | Days from analysis date/cutoff to last order | Customer | transactions | Non-negative | RFM mart |
| Frequency | Distinct qualifying orders | Customer | transactions | Deduplicated orders | RFM mart |
| Monetary Value | Sum of net revenue | Customer | transactions | Returns/discounts reflected | RFM mart |
| RFM | Quantile scores for recency, frequency, monetary value | Customer | RFM inputs | Stable scoring rules | RFM segments |
| CLV | Modeled 12-month customer value estimate | Customer | CLV model/features | Scenario estimate | CLV mart |
| AOV | net revenue / distinct orders | Customer/population | transactions | Orders > 0 | customer features |
| Repeat Purchase Rate | repeat customers / eligible customers | Population | customer features | Denominator > 0 | KPI summary |
| Cohort Retention | active cohort members / original cohort size | Cohort-month | cohort mart | Complete eligible windows | cohort retention |
| Customer Profitability | Return-adjusted profit proxy | Customer | enriched transactions | Synthetic cost/margin rules | customer features |
| Experiment Conversion Rate | conversions / assigned customers | Variant | assignment export | One assignment/customer | experiment evaluation |
| Absolute Lift | treatment rate − control rate | Experiment | experiment evaluation | Finite rates | readout |
| Relative Lift | absolute lift / control rate | Experiment | experiment evaluation | Control rate > 0 | readout |
| Effect Size | Method-specific standardized/practical magnitude | Analysis | statistics outputs | Method named | statistical report |
| Confidence Interval | 95% uncertainty interval from deterministic method | Analysis | statistics outputs | Finite bounds | readout/report |
| Statistical Significance | p-value < predefined alpha | Analysis | statistics outputs | Alpha declared | readout |
| Practical Significance | Effect meets predefined business threshold | Experiment | registry/evaluation | Threshold declared | readout |
| MDE | Smallest effect targeted/detectable at specified alpha/power | Experiment design | registry/design | Baseline, alpha, power validated | experiment design |
| Revenue / CLV at Risk | Value associated with High/Critical churn population | Population | churn + CLV marts | Reconciled join | scenario output |
| Retention Opportunity | Scenario-estimated preserved value/net benefit | Scenario | retention economics | Assumptions explicit | scenario output |
| SRM | Chi-square test of actual versus expected assignment split | Experiment | assignments | Alpha 0.01 | SRM validation |
