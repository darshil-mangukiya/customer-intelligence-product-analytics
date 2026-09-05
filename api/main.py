from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Response, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from config.settings import CONFIG


MARTS = CONFIG.mart_dir
EXPORTS = CONFIG.export_dir
REPORTS = CONFIG.report_dir


class HealthResponse(BaseModel):
    status: str
    marts_available: int
    exports_available: int


class CustomerLookupResponse(BaseModel):
    customer_id: str
    churn_probability: float | None = None
    churn_risk_tier: str | None = None
    predicted_12m_clv: float | None = None
    clv_band: str | None = None
    segment_name: str | None = None
    rfm_segment: str | None = None


class KPIResponse(BaseModel):
    kpi_name: str
    value: float
    display_format: str
    grain: str
    owner: str
    threshold: str


class CustomerSearchResponse(BaseModel):
    customer_id: str
    churn_probability: float | None = None
    churn_risk_tier: str | None = None
    acquisition_channel: str | None = None
    loyalty_tier: str | None = None
    top_purchase_category: str | None = None
    expected_profit_at_risk: float | None = None
    predicted_12m_clv: float | None = None
    clv_band: str | None = None


class AbTestSummaryResponse(BaseModel):
    variant: str
    customers: int
    conversions: int
    conversion_rate: float
    avg_churn_probability: float | None = None
    avg_predicted_clv: float | None = None
    total_profit_proxy: float | None = None
    avg_profit_proxy: float | None = None


class UpliftResponse(BaseModel):
    segment_name: str | None = None
    churn_risk_tier: str | None = None
    clv_band: str | None = None
    conversion_rate_control: float | None = None
    conversion_rate_retention_offer: float | None = None
    absolute_lift: float | None = None
    profit_lift_per_customer: float | None = None


class NextBestActionResponse(BaseModel):
    customer_id: str
    recommended_action: str
    owner_team: str
    success_metric: str
    action_priority_score: float
    churn_risk_tier: str | None = None
    churn_probability: float | None = None
    expected_profit_at_risk: float | None = None
    predicted_12m_clv: float | None = None
    clv_band: str | None = None
    segment_name: str | None = None
    top_purchase_category: str | None = None
    recommended_category: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    affinity_score: float | None = None
    lift: float | None = None
    business_recommendation: str | None = None


class RevenueForecastResponse(BaseModel):
    month_start: str
    revenue_forecast: float
    history_points: int
    revenue_low: float | None = None
    revenue_high: float | None = None
    profit_forecast: float | None = None
    profit_low: float | None = None
    profit_high: float | None = None


class ChurnForecastResponse(BaseModel):
    forecast_month: str
    churn_rate_forecast: float
    history_points: int
    forecast_low: float | None = None
    forecast_high: float | None = None


class LifecycleResponse(BaseModel):
    lifecycle_stage: str
    recommended_transition: str
    customers: int
    avg_historical_clv: float | None = None
    avg_recency_days: float | None = None
    avg_return_rate: float | None = None


class ContractResponse(BaseModel):
    table_name: str
    status: str
    severity: str
    owner: str
    grain: str
    row_count: int
    min_rows: int | None = None
    missing_columns: str | None = None
    unique_key: str | None = None
    duplicate_key_count: int | None = None
    message: str


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8501",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8501",
]


def allowed_cors_origins() -> list[str]:
    configured = os.getenv("API_CORS_ORIGINS", "")
    if configured.strip():
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return DEFAULT_CORS_ORIGINS


def require_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> None:
    expected = os.getenv("CUSTOMER_INTELLIGENCE_API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI(
    title="Customer Intelligence & Product Analytics API",
    version="1.0.0",
    description="API endpoints for KPI, churn, CLV, segmentation, cohort, and product analytics marts.",
    dependencies=[Depends(require_api_key)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _read(path: Path, usecols: list[str] | None = None, nrows: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing dataset: {path.name}")
    return pd.read_csv(path, usecols=usecols, nrows=nrows)


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    clean = frame.copy()
    clean = clean.replace([float("inf"), float("-inf")], None)
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict("records")


def _paged_records(frame: pd.DataFrame, response: Response, limit: int, offset: int = 0) -> list[dict[str, object]]:
    total = len(frame)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return _records(frame.iloc[offset : offset + limit])


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        marts_available=len(list(MARTS.glob("*.csv"))),
        exports_available=len(list(EXPORTS.glob("*.csv"))),
    )


@app.get("/kpis", response_model=list[KPIResponse])
def list_kpis() -> list[KPIResponse]:
    kpis = _read(EXPORTS / "kpi_summary.csv")
    return [KPIResponse(**row) for row in kpis.to_dict("records")]


@app.get("/kpis/{kpi_name}", response_model=KPIResponse)
def get_kpi(kpi_name: str) -> KPIResponse:
    kpis = _read(EXPORTS / "kpi_summary.csv")
    match = kpis.loc[kpis["kpi_name"].str.lower().eq(kpi_name.lower())]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"KPI not found: {kpi_name}")
    return KPIResponse(**match.iloc[0].to_dict())


@app.get("/metrics/customer-overview")
def get_customer_overview_metrics() -> dict[str, object]:
    kpis = _read(EXPORTS / "kpi_summary.csv")
    customer_path = MARTS / "mart_customer_overview.csv"
    customers = _read(customer_path, nrows=100_000) if customer_path.exists() else pd.DataFrame()
    return {
        "kpis": _records(kpis),
        "customer_sample_rows": len(customers),
        "available_fields": list(customers.columns),
        "source_mart": customer_path.name,
    }


@app.get("/metrics/churn")
def get_churn_metrics() -> dict[str, object]:
    churn = _read(MARTS / "mart_churn_risk.csv")
    return {
        "customers": int(churn["customer_id"].nunique()) if "customer_id" in churn else len(churn),
        "avg_churn_probability": float(churn["churn_probability"].mean()) if "churn_probability" in churn else None,
        "expected_profit_at_risk": float(churn.get("expected_profit_at_risk", pd.Series(dtype=float)).sum()),
        "risk_tiers": _records(churn.groupby("churn_risk_tier").size().rename("customers").reset_index()) if "churn_risk_tier" in churn else [],
        "source_mart": "mart_churn_risk.csv",
    }


@app.get("/metrics/clv")
def get_clv_metrics() -> dict[str, object]:
    clv = _read(MARTS / "mart_clv.csv")
    return {
        "customers": int(clv["customer_id"].nunique()) if "customer_id" in clv else len(clv),
        "avg_predicted_12m_clv": float(clv["predicted_12m_clv"].mean()) if "predicted_12m_clv" in clv else None,
        "total_expected_clv_at_risk": float(clv.get("expected_clv_at_risk", pd.Series(dtype=float)).sum()),
        "clv_bands": _records(clv.groupby("clv_band").size().rename("customers").reset_index()) if "clv_band" in clv else [],
        "source_mart": "mart_clv.csv",
    }


@app.get("/metrics/cohorts")
def get_cohort_metrics() -> dict[str, object]:
    cohort = _read(MARTS / "mart_cohort_retention.csv")
    month_summary = (
        cohort.groupby("cohort_index")["retention_rate"].mean().reset_index().sort_values("cohort_index")
        if {"cohort_index", "retention_rate"}.issubset(cohort.columns)
        else pd.DataFrame()
    )
    return {
        "cohort_rows": len(cohort),
        "avg_month_1_retention": float(cohort.loc[cohort["cohort_index"].eq(1), "retention_rate"].mean()) if {"cohort_index", "retention_rate"}.issubset(cohort.columns) else None,
        "avg_month_3_retention": float(cohort.loc[cohort["cohort_index"].eq(3), "retention_rate"].mean()) if {"cohort_index", "retention_rate"}.issubset(cohort.columns) else None,
        "retention_curve": _records(month_summary),
        "source_mart": "mart_cohort_retention.csv",
    }


@app.get("/metrics/products")
def get_product_metrics() -> dict[str, object]:
    product = _read(MARTS / "mart_product_profitability.csv")
    category_summary = (
        product.groupby("category")
        .agg(
            products=("product_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
            return_adjusted_profit=("return_adjusted_profit", "sum"),
            return_rate=("return_rate", "mean"),
        )
        .reset_index()
        .sort_values("return_adjusted_profit", ascending=False)
        if {"category", "product_id", "net_revenue", "return_adjusted_profit", "return_rate"}.issubset(product.columns)
        else pd.DataFrame()
    )
    return {
        "products": int(product["product_id"].nunique()) if "product_id" in product else len(product),
        "total_net_revenue": float(product.get("net_revenue", pd.Series(dtype=float)).sum()),
        "total_return_adjusted_profit": float(product.get("return_adjusted_profit", pd.Series(dtype=float)).sum()),
        "avg_return_rate": float(product["return_rate"].mean()) if "return_rate" in product else None,
        "category_summary": _records(category_summary),
        "source_mart": "mart_product_profitability.csv",
    }


@app.get("/metrics/segments")
def get_segment_metrics() -> list[dict[str, object]]:
    path = EXPORTS / "segment_kpi_comparison.csv"
    if not path.exists():
        path = EXPORTS / "segment_profiles.csv"
    segments = _read(path)
    sort_col = "profit" if "profit" in segments.columns else "customers"
    return _records(segments.sort_values(sort_col, ascending=False))


@app.get(
    "/customers/search",
    response_model=list[CustomerSearchResponse],
    summary="Search scored customers by churn risk and CLV band",
)
def search_customers(
    response: Response,
    risk_tier: str | None = Query(default=None),
    clv_band: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[CustomerSearchResponse]:
    churn = _read(
        MARTS / "mart_churn_risk.csv",
        [
            "customer_id",
            "churn_probability",
            "churn_risk_tier",
            "expected_profit_at_risk",
            "acquisition_channel",
            "loyalty_tier",
            "top_purchase_category",
        ],
    )
    clv = _read(MARTS / "mart_clv.csv", ["customer_id", "predicted_12m_clv", "clv_band"])
    scored = churn.merge(clv, on="customer_id", how="left")
    if risk_tier:
        scored = scored.loc[scored["churn_risk_tier"].str.lower().eq(risk_tier.lower())]
    if clv_band:
        scored = scored.loc[scored["clv_band"].str.lower().eq(clv_band.lower())]
    scored = scored.sort_values(["expected_profit_at_risk", "predicted_12m_clv"], ascending=False)
    return _paged_records(scored, response, limit, offset)


@app.get("/customers/{customer_id}", response_model=CustomerLookupResponse)
def get_customer(customer_id: str) -> CustomerLookupResponse:
    churn = _read(
        MARTS / "mart_churn_risk.csv",
        ["customer_id", "churn_probability", "churn_risk_tier"],
    )
    clv = _read(MARTS / "mart_clv.csv", ["customer_id", "predicted_12m_clv", "clv_band"])
    segments = _read(MARTS / "mart_customer_segments.csv", ["customer_id", "segment_name"])
    rfm = _read(MARTS / "mart_rfm_segments.csv", ["customer_id", "rfm_segment"])

    row = {"customer_id": customer_id}
    found = False
    for frame in [churn, clv, segments, rfm]:
        match = frame.loc[frame["customer_id"].eq(customer_id)]
        if not match.empty:
            found = True
            row.update(match.iloc[0].dropna().to_dict())
    if not found:
        raise HTTPException(status_code=404, detail=f"Customer not found: {customer_id}")
    return CustomerLookupResponse(**row)


@app.get("/customers/{customer_id}/profile")
def get_customer_profile(customer_id: str) -> dict[str, object]:
    return get_customer(customer_id).model_dump()


@app.get("/customers/{customer_id}/churn-risk")
def get_customer_churn_risk(customer_id: str) -> dict[str, object]:
    churn = _read(MARTS / "mart_churn_risk.csv")
    match = churn.loc[churn["customer_id"].eq(customer_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Customer churn score not found: {customer_id}")
    return _records(match)[0]


@app.get("/customers/{customer_id}/recommendations")
def get_customer_recommendations(customer_id: str) -> list[dict[str, object]]:
    actions = _read(EXPORTS / "next_best_actions.csv")
    match = actions.loc[actions["customer_id"].eq(customer_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Customer recommendations not found: {customer_id}")
    return _records(match.sort_values("action_priority_score", ascending=False))


@app.get("/segments")
def get_segments() -> list[dict[str, object]]:
    segments = _read(EXPORTS / "segment_kpi_comparison.csv")
    return _records(segments.sort_values("profit", ascending=False))


@app.get("/products/profitability")
def get_product_profitability(
    response: Response,
    category: str | None = None,
    sort_by: Literal["profit", "revenue", "return_rate", "margin"] = "profit",
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    product = _read(MARTS / "mart_product_profitability.csv")
    if category:
        product = product.loc[product["category"].str.lower().eq(category.lower())]
    sort_map = {
        "profit": "return_adjusted_profit",
        "revenue": "net_revenue",
        "return_rate": "return_rate",
        "margin": "return_adjusted_margin",
    }
    product = product.sort_values(sort_map[sort_by], ascending=False)
    return _paged_records(product, response, limit, offset)


@app.get("/products/{product_id}/profitability")
def get_single_product_profitability(product_id: str) -> dict[str, object]:
    product = _read(MARTS / "mart_product_profitability.csv")
    match = product.loc[product["product_id"].eq(product_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Product not found: {product_id}")
    return _records(match)[0]


@app.get("/cohorts/retention")
def get_cohort_retention() -> list[dict[str, object]]:
    cohort = _read(MARTS / "mart_cohort_retention.csv")
    return _records(cohort)


@app.get("/insights")
def get_insights(priority: str | None = None) -> list[dict[str, object]]:
    insights = _read(EXPORTS / "stakeholder_insights.csv")
    if priority:
        insights = insights.loc[insights["priority"].str.lower().eq(priority.lower())]
    return _records(insights)


@app.get("/monitoring")
def get_monitoring() -> dict[str, list[dict[str, object]]]:
    validation = _read(EXPORTS / "validation_results.csv")
    monitoring = _read(EXPORTS / "model_monitoring_summary.csv")
    return {
        "validation": _records(validation),
        "model_monitoring": _records(monitoring),
    }


@app.get("/experimentation/ab-test", response_model=list[AbTestSummaryResponse])
def get_ab_test_summary() -> list[AbTestSummaryResponse]:
    return _records(_read(EXPORTS / "ab_test_summary.csv"))


@app.get("/experimentation/uplift", response_model=list[UpliftResponse])
def get_uplift_by_segment(
    response: Response,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[UpliftResponse]:
    uplift = _read(EXPORTS / "uplift_by_segment.csv")
    uplift = uplift.sort_values(["profit_lift_per_customer", "absolute_lift"], ascending=False)
    return _paged_records(uplift, response, limit, offset)


@app.get("/analytics/statistics")
def get_statistical_results() -> list[dict[str, object]]:
    return _records(_read(EXPORTS / "statistical_test_results.csv"))


@app.get("/analytics/experiments")
def get_experiment_evaluation() -> list[dict[str, object]]:
    return _records(_read(EXPORTS / "experiment_evaluation.csv"))


@app.get("/analytics/churn-drivers")
def get_churn_driver_analysis() -> list[dict[str, object]]:
    return _records(_read(EXPORTS / "churn_driver_analysis.csv"))


@app.get("/analytics/clv-drivers")
def get_clv_driver_analysis() -> list[dict[str, object]]:
    return _records(_read(EXPORTS / "clv_driver_analysis.csv"))


@app.get("/actions/next-best", response_model=list[NextBestActionResponse])
def get_next_best_actions(
    response: Response,
    recommended_action: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[NextBestActionResponse]:
    actions = _read(EXPORTS / "next_best_actions.csv")
    if recommended_action:
        actions = actions.loc[actions["recommended_action"].str.lower().eq(recommended_action.lower())]
    actions = actions.sort_values("action_priority_score", ascending=False)
    return _paged_records(actions, response, limit, offset)


@app.get("/forecasts/revenue", response_model=list[RevenueForecastResponse])
def get_revenue_forecast() -> list[RevenueForecastResponse]:
    return _records(_read(EXPORTS / "revenue_profit_forecast.csv"))


@app.get("/forecasts/churn", response_model=list[ChurnForecastResponse])
def get_churn_forecast() -> list[ChurnForecastResponse]:
    return _records(_read(EXPORTS / "churn_forecast.csv"))


@app.get("/retention/lifecycle", response_model=list[LifecycleResponse])
def get_retention_lifecycle() -> list[LifecycleResponse]:
    return _records(_read(EXPORTS / "lifecycle_stage_transitions.csv"))


@app.get("/observability/contracts", response_model=list[ContractResponse])
def get_schema_contracts() -> list[ContractResponse]:
    return _records(_read(EXPORTS / "schema_contract_results.csv"))


@app.get("/activation/churn-campaign")
def get_activation_churn_campaign(
    response: Response,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    campaign = _read(EXPORTS / "activation_churn_campaign.csv")
    campaign = campaign.sort_values("priority_score", ascending=False)
    return _paged_records(campaign, response, limit, offset)


@app.get("/activation/cross-sell")
def get_activation_cross_sell(
    response: Response,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    campaign = _read(EXPORTS / "activation_cross_sell_targets.csv")
    campaign = campaign.sort_values("priority_score", ascending=False)
    return _paged_records(campaign, response, limit, offset)
