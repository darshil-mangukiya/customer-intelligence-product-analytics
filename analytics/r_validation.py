from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv


@dataclass(frozen=True)
class ReconciliationMetric:
    metric: str
    python_column: str
    r_column: str
    tolerance: float
    kind: str = "numeric"


METRICS = [
    ReconciliationMetric("control_n", "control_n", "control_n", 0.0),
    ReconciliationMetric("treatment_n", "treatment_n", "treatment_n", 0.0),
    ReconciliationMetric("control_rate", "baseline_rate", "control_rate", 1e-10),
    ReconciliationMetric("treatment_rate", "treatment_rate", "treatment_rate", 1e-10),
    ReconciliationMetric("absolute_lift", "absolute_difference", "absolute_lift", 1e-10),
    ReconciliationMetric("relative_lift", "relative_lift", "relative_lift", 1e-10),
    ReconciliationMetric("ci_lower", "confidence_interval_low", "ci_lower", 1e-10),
    ReconciliationMetric("ci_upper", "confidence_interval_high", "ci_upper", 1e-10),
    ReconciliationMetric("test_statistic", "z_statistic", "test_statistic", 1e-10),
    ReconciliationMetric("p_value", "p_value", "p_value", 1e-10),
    ReconciliationMetric("statistically_significant", "statistically_significant", "statistically_significant", 0.0, "boolean"),
    ReconciliationMetric("practically_significant", "practically_significant", "practically_significant", 0.0, "boolean"),
]


class RRuntimeUnavailable(RuntimeError):
    """Raised when the optional R interpreter is not installed."""


def _resolve_rscript(explicit: str | None = None) -> str:
    if explicit:
        if Path(explicit).is_file():
            return explicit
        raise RRuntimeUnavailable(f"Rscript was not found at the requested path: {explicit}")
    discovered = shutil.which("Rscript")
    if discovered:
        return discovered
    for candidate in [
        Path("/usr/local/bin/Rscript"),
        Path("/opt/homebrew/bin/Rscript"),
        Path("/Library/Frameworks/R.framework/Resources/bin/Rscript"),
    ]:
        if candidate.is_file():
            return str(candidate)
    raise RRuntimeUnavailable("Rscript is unavailable; install R and rerun `make r-validate`")


def _single_row(frame: pd.DataFrame, label: str) -> pd.Series:
    if len(frame) != 1:
        raise ValueError(f"{label} result must contain exactly one row")
    return frame.iloc[0]


def _as_bool(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def reconcile_results(python_result: pd.DataFrame, r_result: pd.DataFrame) -> pd.DataFrame:
    python_row = _single_row(python_result, "Python")
    r_row = _single_row(r_result, "R")
    required_python = {metric.python_column for metric in METRICS}
    required_r = {metric.r_column for metric in METRICS}
    missing_python = sorted(required_python - set(python_result.columns))
    missing_r = sorted(required_r - set(r_result.columns))
    if missing_python or missing_r:
        raise KeyError(f"missing reconciliation columns; Python={missing_python}, R={missing_r}")

    rows: list[dict[str, object]] = []
    for metric in METRICS:
        python_value, r_value = python_row[metric.python_column], r_row[metric.r_column]
        if metric.kind == "boolean":
            python_bool, r_bool = _as_bool(python_value), _as_bool(r_value)
            difference = 0.0 if python_bool == r_bool else 1.0
            passed = python_bool == r_bool
            python_display, r_display = str(python_bool), str(r_bool)
        else:
            python_number, r_number = float(python_value), float(r_value)
            if not np.isfinite(python_number) or not np.isfinite(r_number):
                difference, passed = np.nan, False
            else:
                difference = abs(python_number - r_number)
                passed = difference <= metric.tolerance
            python_display, r_display = python_number, r_number
        rows.append({
            "metric": metric.metric,
            "python_value": python_display,
            "r_value": r_display,
            "absolute_difference": difference,
            "tolerance": metric.tolerance,
            "status": "PASS" if passed else "FAIL",
            "notes": "Equivalent within declared tolerance" if passed else "Values exceed declared tolerance or are non-finite",
        })
    return pd.DataFrame(rows)


def run_r_validation(project_config: ProjectConfig = CONFIG, rscript: str | None = None) -> pd.DataFrame:
    executable = _resolve_rscript(rscript)
    script = project_config.root / "analytics" / "r" / "experiment_validation.R"
    subprocess.run([executable, str(script), str(project_config.root)], cwd=project_config.root, check=True)
    python_path = project_config.export_dir / "experiment_evaluation.csv"
    r_path = project_config.export_dir / "r_experiment_validation.csv"
    if not python_path.exists():
        raise FileNotFoundError(python_path)
    if not r_path.exists():
        raise FileNotFoundError(r_path)
    reconciliation = reconcile_results(pd.read_csv(python_path), pd.read_csv(r_path))
    write_csv(reconciliation, project_config.export_dir / "python_r_statistical_reconciliation.csv")
    status = "PASS" if reconciliation["status"].eq("PASS").all() else "FAIL"
    print(f"Python vs R statistical reconciliation: {status}")
    if status == "FAIL":
        raise RuntimeError("Python vs R statistical reconciliation failed")
    return reconciliation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R experiment validation and reconcile it to Python.")
    parser.add_argument("--rscript", help="Optional explicit Rscript executable path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        run_r_validation(rscript=args.rscript)
    except RRuntimeUnavailable as exc:
        raise SystemExit(f"R validation unavailable: {exc}") from None


if __name__ == "__main__":
    main()
