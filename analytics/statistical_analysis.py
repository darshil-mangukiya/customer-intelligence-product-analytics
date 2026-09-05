from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


ALPHA = 0.05
MIN_SAMPLE = 30


def _bounded_p_value(value: float) -> float:
    """Keep extreme floating-point tails reportable without representing p as exactly zero."""
    return min(1.0, max(float(value), np.finfo(float).tiny))


def holm_adjusted_p_values(p_values: Iterable[float]) -> np.ndarray:
    values = _finite(p_values)
    if not len(values) or ((values < 0) | (values > 1)).any():
        raise ValueError("p-values must be a non-empty sequence within [0, 1]")
    order = np.argsort(values)
    adjusted = np.empty(len(values), dtype=float)
    running_max = 0.0
    for rank, index in enumerate(order):
        running_max = max(running_max, min(1.0, values[index] * (len(values) - rank)))
        adjusted[index] = running_max
    return adjusted


@dataclass(frozen=True)
class TestResult:
    method: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    ci_low: float
    ci_high: float
    n_a: int
    n_b: int
    warning: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _finite(values: Iterable[float]) -> np.ndarray:
    return pd.to_numeric(pd.Series(values), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy(float)


def _require_nonempty(values: np.ndarray, name: str) -> None:
    if not len(values):
        raise ValueError(f"{name} must contain at least one finite observation")


def descriptive_summary(frame: pd.DataFrame, columns: list[str], group_by: str | None = None) -> pd.DataFrame:
    missing = [col for col in [*columns, *([group_by] if group_by else [])] if col not in frame]
    if missing:
        raise KeyError(f"missing descriptive columns: {missing}")
    groups = frame.groupby(group_by, dropna=False) if group_by else [("all", frame)]
    rows: list[dict[str, object]] = []
    for group, subset in groups:
        for column in columns:
            values = _finite(subset[column])
            if not len(values):
                continue
            rows.append({
                "group": str(group), "metric": column, "sample_size": len(values),
                "missing_count": int(len(subset) - len(values)), "mean": float(values.mean()),
                "median": float(np.median(values)), "standard_deviation": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "variance": float(values.var(ddof=1)) if len(values) > 1 else 0.0,
                "quantile_25": float(np.quantile(values, 0.25)), "quantile_75": float(np.quantile(values, 0.75)),
                "minimum": float(values.min()), "maximum": float(values.max()),
                "proportion": float(values.mean()) if set(np.unique(values)).issubset({0.0, 1.0}) else np.nan,
            })
    if not rows:
        raise ValueError("no finite observations were available for descriptive summary")
    return pd.DataFrame(rows)


def mean_confidence_interval(values: Iterable[float], confidence: float = 0.95) -> tuple[float, float]:
    sample = _finite(values)
    _require_nonempty(sample, "values")
    if len(sample) < 2 or np.isclose(sample.std(ddof=1), 0):
        mean = float(sample.mean())
        return mean, mean
    sem = stats.sem(sample)
    margin = stats.t.ppf((1 + confidence) / 2, len(sample) - 1) * sem
    return float(sample.mean() - margin), float(sample.mean() + margin)


def proportion_confidence_interval(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n <= 0 or successes < 0 or successes > n:
        raise ValueError("successes must be between zero and a positive n")
    z = stats.norm.ppf((1 + confidence) / 2)
    p = successes / n
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def cohens_d(group_a: Iterable[float], group_b: Iterable[float]) -> float:
    a, b = _finite(group_a), _finite(group_b)
    _require_nonempty(a, "group_a")
    _require_nonempty(b, "group_b")
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled_var = ((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2)
    return 0.0 if pooled_var <= 0 else float((b.mean() - a.mean()) / math.sqrt(pooled_var))


def welch_mean_test(group_a: Iterable[float], group_b: Iterable[float], alpha: float = ALPHA) -> TestResult:
    a, b = _finite(group_a), _finite(group_b)
    _require_nonempty(a, "group_a")
    _require_nonempty(b, "group_b")
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Welch test requires at least two observations per group")
    result = stats.ttest_ind(a, b, equal_var=False)
    diff = float(b.mean() - a.mean())
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    numerator = (a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) ** 2
    denominator = (a.var(ddof=1) / len(a)) ** 2 / (len(a) - 1) + (b.var(ddof=1) / len(b)) ** 2 / (len(b) - 1)
    df = numerator / denominator if denominator else len(a) + len(b) - 2
    margin = stats.t.ppf(1 - alpha / 2, df) * se
    warning = "Low sample size; interpret cautiously." if min(len(a), len(b)) < MIN_SAMPLE else ""
    return TestResult("Welch two-sample t-test", float(result.statistic), _bounded_p_value(result.pvalue), cohens_d(a, b), "Cohen's d", diff - margin, diff + margin, len(a), len(b), warning)


def two_proportion_test(success_a: int, n_a: int, success_b: int, n_b: int, alpha: float = ALPHA) -> TestResult:
    if min(n_a, n_b) <= 0 or not 0 <= success_a <= n_a or not 0 <= success_b <= n_b:
        raise ValueError("success counts must be valid and both groups non-empty")
    p_a, p_b = success_a / n_a, success_b / n_b
    pooled = (success_a + success_b) / (n_a + n_b)
    pooled_se = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z_stat = (p_b - p_a) / pooled_se if pooled_se else 0.0
    p_value = 2 * stats.norm.sf(abs(z_stat)) if pooled_se else 1.0
    unpooled_se = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    z = stats.norm.ppf(1 - alpha / 2)
    diff = p_b - p_a
    warning = "Low expected successes/failures; use an exact test." if min(success_a, n_a-success_a, success_b, n_b-success_b) < 5 else ""
    return TestResult("Two-sample proportion z-test", z_stat, _bounded_p_value(p_value), diff, "risk difference", diff-z*unpooled_se, diff+z*unpooled_se, n_a, n_b, warning)


def chi_square_test(table: pd.DataFrame) -> TestResult:
    if table.empty or min(table.shape) < 2:
        raise ValueError("chi-square test requires at least a 2x2 table")
    observed = table.apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(float)
    if observed.sum() <= 0 or (observed.sum(axis=0) == 0).any() or (observed.sum(axis=1) == 0).any():
        raise ValueError("chi-square table cannot contain empty margins")
    statistic, p_value, _, expected = stats.chi2_contingency(observed)
    n, r, k = observed.sum(), *observed.shape
    cramer_v = math.sqrt(statistic / (n * min(r - 1, k - 1))) if n and min(r, k) > 1 else 0.0
    warning = "Some expected cells are below 5." if (expected < 5).any() else ""
    return TestResult("Pearson chi-square test", float(statistic), _bounded_p_value(p_value), float(cramer_v), "Cramer's V", float("nan"), float("nan"), int(n), 0, warning)


def correlation_test(x: Iterable[float], y: Iterable[float], method: str = "spearman") -> TestResult:
    frame = pd.DataFrame({"x": x, "y": y}).apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3 or frame["x"].nunique() < 2 or frame["y"].nunique() < 2:
        raise ValueError("correlation requires at least three paired, non-constant observations")
    if method == "pearson":
        result = stats.pearsonr(frame["x"], frame["y"])
    elif method == "spearman":
        result = stats.spearmanr(frame["x"], frame["y"])
    else:
        raise ValueError("method must be 'pearson' or 'spearman'")
    coefficient = float(result.statistic)
    z = np.arctanh(np.clip(coefficient, -0.999999, 0.999999))
    margin = stats.norm.ppf(0.975) / math.sqrt(len(frame) - 3) if len(frame) > 3 else float("inf")
    low, high = np.tanh(z - margin), np.tanh(z + margin)
    return TestResult(f"{method.title()} correlation", coefficient, _bounded_p_value(result.pvalue), coefficient, f"{method} rho" if method == "spearman" else "Pearson r", float(low), float(high), len(frame), 0)


def fit_explanatory_ols(frame: pd.DataFrame, target: str, predictors: list[str]) -> tuple[pd.DataFrame, dict[str, float]]:
    missing = [col for col in [target, *predictors] if col not in frame]
    if missing:
        raise KeyError(f"missing regression columns: {missing}")
    data = frame[[target, *predictors]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) <= len(predictors) + 2:
        raise ValueError("insufficient complete rows for regression")
    varying = [col for col in predictors if data[col].nunique() > 1]
    x = data[varying]
    x_std = (x - x.mean()) / x.std(ddof=0)
    y = np.log1p(data[target].clip(lower=0))
    model = sm.OLS(y, sm.add_constant(x_std)).fit(cov_type="HC3")
    ci = model.conf_int()
    rows = []
    for predictor in varying:
        rows.append({"predictor": predictor, "standardized_coefficient": model.params[predictor], "std_error": model.bse[predictor], "p_value": model.pvalues[predictor], "ci_low": ci.loc[predictor, 0], "ci_high": ci.loc[predictor, 1], "effect_direction": "positive" if model.params[predictor] > 0 else "negative"})
    diagnostics = {"n": float(model.nobs), "r_squared": float(model.rsquared), "adjusted_r_squared": float(model.rsquared_adj), "condition_number": float(model.condition_number)}
    return pd.DataFrame(rows).sort_values("standardized_coefficient", key=lambda s: s.abs(), ascending=False), diagnostics


def minimum_detectable_effect(n_a: int, n_b: int, baseline_rate: float, alpha: float = ALPHA, power: float = 0.80) -> float:
    if min(n_a, n_b) <= 0 or not 0 < baseline_rate < 1:
        raise ValueError("positive group sizes and a baseline rate between 0 and 1 are required")
    z_alpha, z_power = stats.norm.ppf(1-alpha/2), stats.norm.ppf(power)
    return float((z_alpha + z_power) * math.sqrt(baseline_rate*(1-baseline_rate)*(1/n_a+1/n_b)))
