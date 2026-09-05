# Customer Intelligence API

Run locally:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Core endpoints:

- `GET /health`
- `GET /kpis`
- `GET /kpis/{kpi_name}`
- `GET /customers/{customer_id}`
- `GET /customers/search?risk_tier=Critical&limit=25`
- `GET /segments`
- `GET /products/profitability?sort_by=profit`
- `GET /cohorts/retention`
- `GET /insights`
- `GET /monitoring`
- `GET /experimentation/ab-test`
- `GET /experimentation/uplift`
- `GET /actions/next-best`
- `GET /forecasts/revenue`
- `GET /forecasts/churn`
- `GET /retention/lifecycle`
- `GET /observability/contracts`
