from __future__ import annotations

import math

import pandas as pd
from scipy import stats


def required_sample_size_per_group(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be between 0 and 1")
    if minimum_detectable_effect <= 0 or baseline_rate + minimum_detectable_effect >= 1:
        raise ValueError("minimum_detectable_effect must produce a treatment rate between 0 and 1")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must be between 0 and 1")
    treatment_rate = baseline_rate + minimum_detectable_effect
    pooled = (baseline_rate + treatment_rate) / 2
    numerator = (
        stats.norm.ppf(1 - alpha / 2) * math.sqrt(2 * pooled * (1 - pooled))
        + stats.norm.ppf(power)
        * math.sqrt(
            baseline_rate * (1 - baseline_rate)
            + treatment_rate * (1 - treatment_rate)
        )
    ) ** 2
    return math.ceil(numerator / minimum_detectable_effect**2)


def sample_ratio_mismatch(
    control_n: int,
    treatment_n: int,
    expected_control_share: float = 0.5,
    alpha: float = 0.01,
) -> dict[str, object]:
    if min(control_n, treatment_n) < 0 or control_n + treatment_n <= 0:
        raise ValueError("non-negative group sizes with a positive total are required")
    if not 0 < expected_control_share < 1:
        raise ValueError("expected_control_share must be between 0 and 1")
    total = control_n + treatment_n
    expected_control = total * expected_control_share
    expected_treatment = total - expected_control
    statistic = (control_n - expected_control) ** 2 / expected_control
    statistic += (treatment_n - expected_treatment) ** 2 / expected_treatment
    p_value = float(stats.chi2.sf(statistic, 1))
    status = "PASS" if p_value >= alpha else "FAIL"
    return {
        "expected_control": expected_control,
        "expected_treatment": expected_treatment,
        "actual_control": control_n,
        "actual_treatment": treatment_n,
        "chi_square": statistic,
        "p_value": p_value,
        "alpha": alpha,
        "status": status,
        "interpretation": (
            "Allocation is consistent with the planned split."
            if status == "PASS"
            else "Allocation differs materially from the planned split; do not interpret treatment impact until investigated."
        ),
    }


def experiment_design_summary(registry: dict[str, object]) -> pd.DataFrame:
    baseline = float(registry["baseline"])
    mde = float(registry["minimum_detectable_effect"])
    alpha = float(registry["alpha"])
    power = float(registry["power"])
    required = required_sample_size_per_group(baseline, mde, alpha, power)
    return pd.DataFrame([{
        "experiment_id": registry["experiment_id"],
        "baseline_rate": baseline,
        "minimum_detectable_effect": mde,
        "alpha": alpha,
        "power": power,
        "required_sample_size_per_group": required,
        "required_total_sample_size": required * 2,
        "method": "Normal approximation for equal-sized two-sample proportions",
    }])
