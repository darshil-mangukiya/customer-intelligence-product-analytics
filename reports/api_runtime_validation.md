# FastAPI Runtime Validation

Validation was performed over live HTTP against deterministic synthetic project outputs.

- Checks passed: 17/17
- API key value was not written to evidence.

| Check | Path | Observed | Status | Detail |
|---|---|---:|---|---|
| health | `/health` | 200 | PASS | HTTP 200; content-type=application/json |
| openapi_schema | `/openapi.json` | 200 | PASS | HTTP 200; content-type=application/json |
| kpi_contract | `/kpis` | 200 | PASS | HTTP 200; content-type=application/json |
| customer_overview | `/metrics/customer-overview?limit=10` | 200 | PASS | HTTP 200; content-type=application/json |
| churn_metrics | `/metrics/churn` | 200 | PASS | HTTP 200; content-type=application/json |
| clv_metrics | `/metrics/clv` | 200 | PASS | HTTP 200; content-type=application/json |
| segment_metrics | `/metrics/segments` | 200 | PASS | HTTP 200; content-type=application/json |
| experiment_metrics | `/experimentation/ab-test` | 200 | PASS | HTTP 200; content-type=application/json |
| missing_customer | `/customers/DOES_NOT_EXIST` | 404 | PASS | HTTP 404; content-type=application/json |
| malformed_parameter | `/customers/search?limit=not-an-integer` | 422 | PASS | HTTP 422; content-type=application/json |
| unexpected_query_field | `/customers/search?unexpected_field=bounded-test&limit=1` | 200 | PASS | HTTP 200; content-type=application/json |
| injection_like_identifier | `/customers/%27%20OR%201%3D1--` | 404 | PASS | HTTP 404; content-type=application/json |
| unsupported_method | `/health` | 405 | PASS | HTTP 405; content-type=application/json |
| missing_api_key | `/health` | 401 | PASS | authentication rejection without diagnostic leakage |
| invalid_api_key | `/health` | 401 | PASS | authentication rejection without diagnostic leakage |
| numeric_fidelity_kpis | `/kpis` | 200 | PASS | matched=16/16; max_abs_difference=0 |
| health_schema | `/health` | 200 | PASS | expected response fields present |
