# Dependency Vulnerability Audit

- Tool: `pip-audit` 2.10.1
- Input: fully hashed `requirements.lock`
- Result: no known vulnerabilities found after the compatible FastAPI/Starlette update.
- Historical result: 7 records affecting `starlette==0.52.1`, representing 5 unique advisory IDs.
- Final locked versions: `fastapi==0.141.1`; `starlette==1.3.1`.

| Package | Starting version | Advisory | Fixed version | Action |
|---|---:|---|---:|---|
| Starlette | 0.52.1 | PYSEC-2026-161 | 1.0.1 | Resolved by Starlette 1.3.1. |
| Starlette | 0.52.1 | PYSEC-2026-248 | 1.3.0 | Resolved by Starlette 1.3.1. |
| Starlette | 0.52.1 | PYSEC-2026-249 | 1.3.1 | Resolved by Starlette 1.3.1. |
| Starlette | 0.52.1 | PYSEC-2026-2281 | 1.1.0 | Resolved by Starlette 1.3.1. |
| Starlette | 0.52.1 | PYSEC-2026-2280 | 1.1.0 | Resolved by Starlette 1.3.1. |

The current FastAPI and Streamlit constraints permit Starlette 1.3.1, so no incompatible direct override was used. See `security/reports/starlette_advisory_triage.md` for the five individual severity, affected-range, applicability, and code-path assessments. Tolerances and tests were not weakened.
