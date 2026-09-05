# Data Quality Severity Matrix

| Severity | Meaning | Example | Action |
|---|---|---|---|
| P1 | Executive reporting blocker | Missing KPI table, broken customer key, failed core mart contract | Stop dashboard refresh and notify owner |
| P2 | Material business risk | Product profitability missing margin field, action queue below expected row count | Publish only after data-steward review |
| P3 | Low-risk quality issue | Optional enrichment field missing, minor extract freshness delay | Document in release notes |

## Ownership Rules

- BI Engineering owns marts, dashboard extracts, and semantic metric consistency.
- Customer Analytics owns churn, CLV, segmentation, lifecycle, and action outputs.
- Product Analytics owns product profitability, returns, affinity, and category extracts.
- Lifecycle Marketing owns experiment interpretation and next-best-action activation.
