# Dashboard Screenshots

Real dashboard captures generated from local synthetic project outputs.

## Streamlit Screenshots

Streamlit captures are stored in `dashboards/screenshots/` and were captured June 2026 at 1440x1100.

### Reproduce

`make streamlit`

or:

`streamlit run app/streamlit_app.py`

Then open `http://localhost:8501`.

### Pages

| Page | Screenshot |
|---|---|
| Executive Overview | `executive_overview.png` |
| Customer Segments | `customer_segments.png` |
| Churn Risk | `churn_risk.png` |
| CLV Analysis | `clv_analysis.png` |
| Cohort Retention | `cohort_retention.png` |
| Product Profitability | `product_profitability.png` |
| Revenue Leakage | `revenue_leakage.png` |
| Activation Lists | `activation_lists.png` |
| Data Quality & Pipeline Health | `data_quality.png` |

## Power BI Screenshots

Power BI captures are stored in `dashboards/powerbi/screenshots/`.

| Page | Screenshot |
|---|---|
| Executive Overview | `powerbi_executive_overview.png` |
| Customer Segments | `powerbi_customer_segments.png` |
| Churn & Retention | `powerbi_churn_retention.png` |
| CLV Analysis | `powerbi_clv_analysis.png` |
| Cohort Retention | `powerbi_cohort_retention.png` |
| Product Profitability | `powerbi_product_profitability.png` |
| Activation Center | `powerbi_activation_center.png` |

## Notes

- Captures come from the running app, not mocked images.
- The app uses generated marts/exports when present, with committed sample fallbacks for lightweight review.
- The Power BI `.pbix` file is stored with Git LFS under `dashboards/powerbi/`.
