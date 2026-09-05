from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def _design(index: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(index)), index, np.sin(2 * np.pi * index / 12), np.cos(2 * np.pi * index / 12)])


def _metrics(group: pd.DataFrame) -> dict[str, float]:
    actual, predicted = group["actual"].to_numpy(), group["prediction"].to_numpy()
    error = predicted - actual
    nonzero = actual != 0
    return {"mae": float(np.mean(abs(error))), "rmse": float(np.sqrt(np.mean(error ** 2))),
            "mape": float(np.mean(abs(error[nonzero] / actual[nonzero]))) if nonzero.any() else 0.0,
            "smape": float(np.mean(2 * abs(error) / np.maximum(abs(actual) + abs(predicted), 1e-12))),
            "bias": float(np.mean(error)), "interval_coverage": float(group["covered"].mean()), "folds": len(group)}


def run_forecast_validation(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    orders = pd.read_csv(project_config.mart_dir / "fact_orders.csv", parse_dates=["order_date"])
    monthly = orders.assign(month=orders["order_date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False)["net_revenue"].sum()
    values = monthly["net_revenue"].to_numpy(float)
    rows = []
    for test_index in range(12, len(values)):
        train = values[:test_index]
        actual = values[test_index]
        residual_sd = float(np.std(np.diff(train), ddof=1)) if len(train) > 2 else 0.0
        candidates = {"naive": train[-1], "seasonal_naive": train[-12]}
        x_train = _design(np.arange(len(train)))
        coefficient, *_ = np.linalg.lstsq(x_train, train, rcond=None)
        candidates["linear_seasonal"] = float((_design(np.array([test_index])) @ coefficient).item())
        fitted = x_train @ coefficient
        model_sd = float(np.std(train - fitted, ddof=min(4, len(train) - 1))) if len(train) > 4 else residual_sd
        for method, prediction in candidates.items():
            width = 1.96 * (model_sd if method == "linear_seasonal" else residual_sd)
            rows.append({"forecast_month": monthly.iloc[test_index]["month"], "method": method, "actual": actual,
                         "prediction": prediction, "lower_95": max(0.0, prediction - width), "upper_95": prediction + width,
                         "covered": max(0.0, prediction - width) <= actual <= prediction + width})
    predictions = pd.DataFrame(rows)
    results = pd.DataFrame([{"method": method, **_metrics(group)} for method, group in predictions.groupby("method")])
    results["beats_naive_mae"] = results["mae"] < float(results.loc[results["method"].eq("naive"), "mae"].iloc[0])
    write_csv(predictions, project_config.export_dir / "forecast_backtest_predictions.csv")
    write_csv(results, project_config.export_dir / "forecast_backtest_results.csv")
    best = results.sort_values("mae").iloc[0]
    write_markdown([
        "# Forecast Validation and Baseline Comparison", "",
        "Expanding-window, one-month-ahead backtesting compares the existing linear-seasonal approach with naive and 12-month seasonal-naive baselines.", "",
        f"- Backtest folds: {int(best['folds'])}", f"- Lowest-MAE method: {best['method']} ({best['mae']:.2f})",
        "- Metrics include MAE, RMSE, zero-safe MAPE, sMAPE, signed bias, and empirical 95% interval coverage.",
        "- Prediction intervals are residual-based diagnostics, not guarantees. The synthetic history is short, so results do not establish production forecast performance.",
    ], project_config.report_dir / "forecast_validation.md")
    return {"predictions": predictions, "results": results}


if __name__ == "__main__":
    run_forecast_validation()
