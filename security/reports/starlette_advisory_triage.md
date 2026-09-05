# Starlette Advisory Triage

Triage date: 2026-08-22. Scope: the local P3 API and deterministic synthetic portfolio data. This is dependency-risk evidence, not a claim of production security.

## Package state and decision

- Starting Python: 3.12.13 in the existing managed `.venv`.
- Final clean-validation Python: 3.12.7, within the declared Python 3.12 project range.
- Starting FastAPI / Starlette: 0.128.8 / 0.52.1.
- Final locked FastAPI / Starlette: 0.141.1 / 1.3.1.
- Related locked packages: Pydantic 2.13.4, AnyIO 4.14.2, Uvicorn 0.35.0, HTTPX 0.28.1, Streamlit 1.62.0.
- Resolver evidence: FastAPI 0.141.1 requires Starlette `>=0.46.0`; Streamlit 1.62.0 requires Starlette `>=0.46.0,<1.4.0`. Starlette 1.3.1 therefore resolves without an incompatible override.
- Change scope: only the FastAPI and Starlette declared bounds and their locked versions changed.

## Advisory inventory

| Advisory | CVE | Severity / CVSS | Affected range | Fixed | P3 applicability before update | Reason | Final status |
|---|---|---:|---|---|---|---|---|
| [GHSA-86qp-5c8j-p5mr](https://github.com/advisories/GHSA-86qp-5c8j-p5mr) / PYSEC-2026-161 | CVE-2026-48710 | Medium / 6.5 | `<=1.0.0` | 1.0.1 | NOT APPLICABLE TO CURRENT P3 USAGE | P3 does not use `request.url` or `request.url.path` for authentication, authorization, routing policy, redirects, or other security decisions. Authentication reads `X-API-Key` through FastAPI's header dependency. | RESOLVED BY 1.3.1 |
| [GHSA-jp82-jpqv-5vv3](https://github.com/advisories/GHSA-jp82-jpqv-5vv3) / PYSEC-2026-248 | CVE-2026-54282 | Low / 3.7 | `<1.3.0` | 1.3.0 | NOT APPLICABLE TO CURRENT P3 USAGE | No P3 middleware, endpoint, redirect, callback, cache key, SSRF target, or audit decision reads `request.url.hostname` or `request.url.netloc`. | RESOLVED BY 1.3.1 |
| [GHSA-82w8-qh3p-5jfq](https://github.com/advisories/GHSA-82w8-qh3p-5jfq) / PYSEC-2026-249 | CVE-2026-54283 | High / 7.5 | `>=0.4.1,<1.3.1` | 1.3.1 | NOT APPLICABLE TO CURRENT P3 USAGE | The API exposes governed GET routes and does not call `request.form()`, declare `Form`, `File`, or `UploadFile`, or parse `application/x-www-form-urlencoded` bodies. | RESOLVED BY 1.3.1 |
| [GHSA-wqp7-x3pw-xc5r](https://github.com/advisories/GHSA-wqp7-x3pw-xc5r) / PYSEC-2026-2281 | CVE-2026-48818 | High / 7.5 | `<1.1.0` | 1.1.0 | NOT APPLICABLE TO CURRENT P3 USAGE | P3 does not instantiate or mount Starlette `StaticFiles`; validated containers run Linux, and the advisory's vulnerable resolver is Windows-specific. | RESOLVED BY 1.3.1 |
| [GHSA-x746-7m8f-x49c](https://github.com/advisories/GHSA-x746-7m8f-x49c) / PYSEC-2026-2280 | CVE-2026-48817 | Medium / 5.3 | `<1.1.0` | 1.1.0 | NOT APPLICABLE TO CURRENT P3 USAGE | P3 uses FastAPI operation decorators with explicit GET methods; it has no `HTTPEndpoint` subclass or unconstrained Starlette `Route`. | RESOLVED BY 1.3.1 |

The starting Starlette version was inside all five package-level affected ranges even though the vulnerable application code paths were absent. Updating removes the dependency findings as defense in depth and avoids relying solely on compensating controls.

## Code-path evidence

Repository searches found one Starlette middleware surface: FastAPI's `CORSMiddleware`, configured for GET requests and explicit local origins. No application Python code uses `request.url`, form or multipart parsing, file uploads, static-file mounts, WebSockets, session or cookie middleware, proxy-header authorization, `HTTPEndpoint`, or Starlette `Route`. The API is read-only, uses bounded query parameters, reads governed CSV outputs, and applies an optional global API-key header dependency.

## Validation and residual risk

- Hash-locked clean install: PASS.
- Clean-environment `pip check`: PASS.
- pytest: 92/92 PASS on the final locked versions.
- API and operational targeted tests: 11/11 PASS.
- Direct Ruff in the clean locked environment: PASS.
- `pip-audit` 2.10.1 against `requirements.lock`: no known vulnerabilities found.
- CycloneDX 1.6 SBOM: regenerated and validated; 99 components; FastAPI 0.141.1 and Starlette 1.3.1.
- Existing API image: rebuilt from the hash lock and directly verified as FastAPI 0.141.1 / Starlette 1.3.1.

The remaining security risk is ordinary future dependency/advisory drift and the fact that local regression evidence is not production penetration testing. The final tests emit a Starlette deprecation warning recommending `httpx2` for `TestClient`; this is not a vulnerability finding, does not fail tests, and is not addressed here because the task prohibits unrelated dependency churn.

The in-repository `.venv` is managed and rejected pip's atomic package rename, so it remains internally consistent on FastAPI 0.128.8 / Starlette 0.52.1. It is not the final release environment and must be rebuilt from `requirements.lock` before reuse for a release. The patched state was validated in a fresh hash-locked environment rather than forcing or destructively recreating the managed `.venv`.
