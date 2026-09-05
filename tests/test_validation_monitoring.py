from __future__ import annotations

import pandas as pd

from monitoring.model_monitoring import _mix_delta, _psi
from validation.validate_data import _result


def test_validation_result_status_labels_pass_and_fail():
    passing = _result("suite", "table", "expectation", "column", True, 0, "= 0")
    failing = _result("suite", "table", "expectation", "column", False, 2, "= 0", failing_rows=2)

    assert passing.status == "PASS"
    assert failing.status == "FAIL"
    assert failing.failing_rows == 2


def test_monitoring_psi_is_zero_for_same_distribution():
    series = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
    assert _psi(series, series) == 0


def test_monitoring_mix_delta_detects_distribution_shift():
    current = {"Low": 0.6, "High": 0.4}
    baseline = {"Low": 0.8, "High": 0.2}
    assert round(_mix_delta(current, baseline), 2) == 0.2

