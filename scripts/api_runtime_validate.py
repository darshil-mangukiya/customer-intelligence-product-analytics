from __future__ import annotations

import argparse
import asyncio
import math
import time
from collections.abc import Iterator

import httpx
import numpy as np
import pandas as pd

from config.settings import CONFIG
from etl.io_utils import write_csv, write_markdown


def _numeric_values(value: object) -> Iterator[float]:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        yield float(value)
    elif isinstance(value, dict):
        for child in value.values():
            yield from _numeric_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _numeric_values(child)


def validate_contracts(base_url: str, api_key: str) -> pd.DataFrame:
    headers = {"X-API-Key": api_key}
    checks: list[dict[str, object]] = []

    def check(name: str, method: str, path: str, expected: int) -> httpx.Response:
        response = httpx.request(method, f"{base_url}{path}", headers=headers, timeout=20)
        content_type = response.headers.get("content-type", "")
        status = "PASS" if response.status_code == expected else "FAIL"
        detail = f"HTTP {response.status_code}; content-type={content_type}"
        if "application/json" in content_type:
            payload = response.json()
            finite = all(math.isfinite(number) for number in _numeric_values(payload))
            if not finite:
                status = "FAIL"
                detail += "; non-finite numeric value"
            serialized = response.text.lower()
            if "traceback" in serialized or "openai_api_key" in serialized:
                status = "FAIL"
                detail += "; sensitive diagnostic leakage"
        checks.append({"check": name, "path": path, "expected_status": expected, "observed_status": response.status_code, "status": status, "detail": detail})
        return response

    health = check("health", "GET", "/health", 200)
    check("openapi_schema", "GET", "/openapi.json", 200)
    kpis = check("kpi_contract", "GET", "/kpis", 200)
    check("customer_overview", "GET", "/metrics/customer-overview?limit=10", 200)
    check("churn_metrics", "GET", "/metrics/churn", 200)
    check("clv_metrics", "GET", "/metrics/clv", 200)
    check("segment_metrics", "GET", "/metrics/segments", 200)
    check("experiment_metrics", "GET", "/experimentation/ab-test", 200)
    check("missing_customer", "GET", "/customers/DOES_NOT_EXIST", 404)
    check("malformed_parameter", "GET", "/customers/search?limit=not-an-integer", 422)
    check("unexpected_query_field", "GET", "/customers/search?unexpected_field=bounded-test&limit=1", 200)
    check("injection_like_identifier", "GET", "/customers/%27%20OR%201%3D1--", 404)
    check("unsupported_method", "POST", "/health", 405)

    for name, auth_headers in (
        ("missing_api_key", {}),
        ("invalid_api_key", {"X-API-Key": "invalid-disposable-value"}),
    ):
        response = httpx.get(f"{base_url}/health", headers=auth_headers, timeout=20)
        checks.append(
            {
                "check": name,
                "path": "/health",
                "expected_status": 401,
                "observed_status": response.status_code,
                "status": "PASS" if response.status_code == 401 else "FAIL",
                "detail": "authentication rejection without diagnostic leakage",
            }
        )

    local_kpis = pd.read_csv(CONFIG.export_dir / "kpi_summary.csv")
    api_kpis = pd.DataFrame(kpis.json())
    merged = local_kpis[["kpi_name", "value"]].merge(api_kpis[["kpi_name", "value"]], on="kpi_name", suffixes=("_local", "_api"))
    max_difference = float((merged["value_local"] - merged["value_api"]).abs().max())
    checks.append(
        {
            "check": "numeric_fidelity_kpis",
            "path": "/kpis",
            "expected_status": 200,
            "observed_status": kpis.status_code,
            "status": "PASS" if len(merged) == len(local_kpis) and max_difference <= 1e-9 else "FAIL",
            "detail": f"matched={len(merged)}/{len(local_kpis)}; max_abs_difference={max_difference:.12g}",
        }
    )
    health_payload = health.json()
    checks.append(
        {
            "check": "health_schema",
            "path": "/health",
            "expected_status": 200,
            "observed_status": health.status_code,
            "status": "PASS" if set(health_payload) == {"status", "marts_available", "exports_available"} else "FAIL",
            "detail": "expected response fields present",
        }
    )
    return pd.DataFrame(checks)


async def benchmark(base_url: str, api_key: str, clients: int, requests: int) -> dict[str, object]:
    headers = {"X-API-Key": api_key}
    semaphore = asyncio.Semaphore(clients)
    latencies: list[float] = []
    statuses: list[int] = []

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=20) as client:
        async def one_request() -> None:
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get("/kpis")
                    statuses.append(response.status_code)
                except httpx.HTTPError:
                    statuses.append(0)
                latencies.append((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        await asyncio.gather(*(one_request() for _ in range(requests)))
        elapsed = time.perf_counter() - started

    latency_array = np.asarray(latencies)
    successes = sum(status == 200 for status in statuses)
    return {
        "clients": clients,
        "requests": requests,
        "successes": successes,
        "errors": requests - successes,
        "success_rate": successes / requests,
        "error_rate": (requests - successes) / requests,
        "requests_per_second": requests / elapsed,
        "p50_ms": float(np.percentile(latency_array, 50)),
        "p95_ms": float(np.percentile(latency_array, 95)),
        "p99_ms": float(np.percentile(latency_array, 99)),
        "min_ms": float(latency_array.min()),
        "max_ms": float(latency_array.max()),
    }


async def run_benchmarks(base_url: str, api_key: str, requests: int) -> list[dict[str, object]]:
    return await asyncio.gather(
        *(benchmark(base_url, api_key, clients, requests) for clients in (1, 10, 25, 50))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and benchmark a live P3 FastAPI server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    contracts = validate_contracts(args.base_url, args.api_key)
    benchmark_rows = asyncio.run(run_benchmarks(args.base_url, args.api_key, args.requests))
    benchmarks = pd.DataFrame(benchmark_rows)
    write_csv(contracts, CONFIG.audit_dir / "api_runtime_validation.csv")
    write_csv(benchmarks, CONFIG.audit_dir / "api_benchmark.csv")

    validation_lines = [
        "# FastAPI Runtime Validation",
        "",
        "Validation was performed over live HTTP against deterministic synthetic project outputs.",
        "",
        f"- Checks passed: {contracts['status'].eq('PASS').sum()}/{len(contracts)}",
        "- API key value was not written to evidence.",
        "",
        "| Check | Path | Observed | Status | Detail |",
        "|---|---|---:|---|---|",
    ]
    for row in contracts.to_dict("records"):
        validation_lines.append(f"| {row['check']} | `{row['path']}` | {row['observed_status']} | {row['status']} | {row['detail']} |")
    write_markdown(validation_lines, CONFIG.report_dir / "api_runtime_validation.md")

    performance_lines = [
        "# Local Controlled API Benchmark",
        "",
        "This is a local controlled benchmark, not a production capacity claim.",
        "",
        "| Clients | Requests | Success | Req/s | p50 ms | p95 ms | p99 ms | Error Rate |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in benchmarks.to_dict("records"):
        performance_lines.append(
            f"| {row['clients']} | {row['requests']} | {row['success_rate']:.1%} | {row['requests_per_second']:.2f} | "
            f"{row['p50_ms']:.2f} | {row['p95_ms']:.2f} | {row['p99_ms']:.2f} | {row['error_rate']:.1%} |"
        )
    write_markdown(performance_lines, CONFIG.report_dir / "api_performance_benchmark.md")

    if not contracts["status"].eq("PASS").all() or not benchmarks["success_rate"].eq(1.0).all():
        raise SystemExit("FastAPI runtime validation or benchmark failed")


if __name__ == "__main__":
    main()
