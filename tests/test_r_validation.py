from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.r_validation import METRICS, RRuntimeUnavailable, reconcile_results, run_r_validation
from config.settings import ProjectConfig


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    python = pd.DataFrame([{
        "control_n": 100, "treatment_n": 100, "baseline_rate": 0.10,
        "treatment_rate": 0.13, "absolute_difference": 0.03, "relative_lift": 0.30,
        "confidence_interval_low": 0.01, "confidence_interval_high": 0.05,
        "z_statistic": 2.5, "p_value": 0.012, "statistically_significant": True,
        "practically_significant": True,
    }])
    r = pd.DataFrame([{
        "control_n": 100, "treatment_n": 100, "control_rate": 0.10,
        "treatment_rate": 0.13, "absolute_lift": 0.03, "relative_lift": 0.30,
        "ci_lower": 0.01, "ci_upper": 0.05, "test_statistic": 2.5,
        "p_value": 0.012, "statistically_significant": True,
        "practically_significant": True,
    }])
    return python, r


def test_reconciliation_passes_equivalent_results() -> None:
    python, r = _frames()
    result = reconcile_results(python, r)
    assert len(result) == len(METRICS)
    assert result["status"].eq("PASS").all()


def test_reconciliation_fails_outside_tolerance() -> None:
    python, r = _frames()
    r.loc[0, "p_value"] = 0.02
    result = reconcile_results(python, r)
    assert result.loc[result["metric"].eq("p_value"), "status"].item() == "FAIL"


def test_reconciliation_requires_one_row_per_language() -> None:
    python, r = _frames()
    with pytest.raises(ValueError):
        reconcile_results(pd.concat([python, python]), r)


def test_reconciliation_rejects_missing_columns() -> None:
    python, r = _frames()
    with pytest.raises(KeyError):
        reconcile_results(python.drop(columns="p_value"), r)


def test_reconciliation_rejects_malformed_boolean() -> None:
    python, r = _frames()
    r["statistically_significant"] = r["statistically_significant"].astype(object)
    r.loc[0, "statistically_significant"] = "unknown"
    with pytest.raises(ValueError):
        reconcile_results(python, r)


def test_reconciliation_marks_nan_as_failure() -> None:
    python, r = _frames()
    r.loc[0, "absolute_lift"] = np.nan
    result = reconcile_results(python, r)
    assert result.loc[result["metric"].eq("absolute_lift"), "status"].item() == "FAIL"


def test_missing_r_runtime_is_reported_without_fake_output(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("analytics.r_validation.shutil.which", lambda _: None)
    config = ProjectConfig(
        root=tmp_path, raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed",
        mart_dir=tmp_path / "marts", export_dir=tmp_path / "exports",
        rejected_dir=tmp_path / "rejected", audit_dir=tmp_path / "audit",
        report_dir=tmp_path / "reports", model_dir=tmp_path / "models",
    )
    with pytest.raises(RRuntimeUnavailable, match="Rscript"):
        run_r_validation(config, rscript="/definitely/missing/Rscript")
    assert not (config.export_dir / "r_experiment_validation.csv").exists()
