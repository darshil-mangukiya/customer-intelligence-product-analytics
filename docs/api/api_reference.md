# API Reference

The API layer exposes governed platform outputs without requiring analysts to open CSV files directly.

Run:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

Primary endpoints:

- `/kpis`
- `/customers/{customer_id}`
- `/customers/search`
- `/segments`
- `/products/profitability`
- `/cohorts/retention`
- `/insights`
- `/monitoring`
- `/experimentation/ab-test`
- `/experimentation/uplift`
- `/actions/next-best`
- `/forecasts/revenue`
- `/forecasts/churn`
- `/retention/lifecycle`
- `/observability/contracts`
