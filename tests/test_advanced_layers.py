from __future__ import annotations

from pathlib import Path

import pandas as pd

from experimentation.ab_testing import _z_test_proportions
from forecasting.forecast_metrics import _forecast_frame
from observability.schema_contracts import TableContract, evaluate_contract
from retention_analytics.lifecycle_analysis import _lifecycle_stage


def test_z_test_detects_positive_treatment_lift():
    result = _z_test_proportions(control_success=80, control_n=1000, treatment_success=120, treatment_n=1000)
    assert result.treatment_rate > result.control_rate
    assert result.absolute_lift > 0
    assert result.p_value < 0.05


def test_forecast_frame_returns_requested_future_periods():
    history = pd.DataFrame(
        {
            "month_start": pd.date_range("2025-01-01", periods=12, freq="MS"),
            "net_revenue": [100 + idx * 10 for idx in range(12)],
        }
    )
    forecast = _forecast_frame(history, "month_start", "net_revenue", periods=3)
    assert len(forecast) == 3
    assert forecast["forecast_value"].gt(0).all()


def test_lifecycle_stage_labels_high_value_loyal_customer():
    row = pd.Series(
        {
            "customer_age_days": 365,
            "orders": 8,
            "repeat_purchase_flag": 1,
            "recency_days": 20,
            "customer_value_band": "VIP",
        }
    )
    assert _lifecycle_stage(row) == "High-value loyal"


def test_schema_contract_detects_duplicate_key(tmp_path):
    source = Path(tmp_path / "contract.csv")
    pd.DataFrame([{"id": 1, "value": 10}, {"id": 1, "value": 20}]).to_csv(source, index=False)
    result = evaluate_contract(
        TableContract(
            name="contract",
            path=source,
            owner="BI",
            grain="one row per id",
            required_columns=("id", "value"),
            unique_key="id",
            min_rows=1,
        )
    )
    assert result["status"] == "FAIL"
    assert result["duplicate_key_count"] == 1
