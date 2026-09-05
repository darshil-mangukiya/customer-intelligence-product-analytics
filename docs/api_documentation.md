# API Documentation

## Statistical analytics endpoints

- `GET /analytics/statistics` returns question-level methods, intervals, p-values, effect sizes, interpretations, actions, and monitoring KPIs.
- `GET /analytics/experiments` returns the formal synthetic control/treatment evaluation.
- `GET /analytics/churn-drivers` and `GET /analytics/clv-drivers` return ranked associated signals.

Run `make analytics` before using these endpoints. Missing output files follow the API's existing 404 behavior. All results use synthetic project data.

FastAPI endpoint documentation for governed analytics consumption.

## Core Endpoints

- /health, /metrics/customer-overview, /metrics/churn, /metrics/clv, /metrics/cohorts, /metrics/products, /metrics/segments.

## Customer Endpoints

- /customers/{customer_id}/profile, /customers/{customer_id}/churn-risk, /customers/{customer_id}/recommendations.

## Product and Activation Endpoints

- /products/{product_id}/profitability, /activation/churn-campaign, /activation/cross-sell.

## Controls

- Defaults are tuned for local review with GET-only CORS access for dashboard clients.
- Optional CUSTOMER_INTELLIGENCE_API_KEY enables API key protection.
- Pagination headers are returned for list endpoints.
