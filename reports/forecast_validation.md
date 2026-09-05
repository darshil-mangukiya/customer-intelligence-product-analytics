# Forecast Validation and Baseline Comparison

Expanding-window, one-month-ahead backtesting compares the existing linear-seasonal approach with naive and 12-month seasonal-naive baselines.

- Backtest folds: 24
- Lowest-MAE method: seasonal_naive (8997.64)
- Metrics include MAE, RMSE, zero-safe MAPE, sMAPE, signed bias, and empirical 95% interval coverage.
- Prediction intervals are residual-based diagnostics, not guarantees. The synthetic history is short, so results do not establish production forecast performance.
