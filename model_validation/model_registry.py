from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd

from churn_model.train_churn_model import CHURN_FEATURES
from config.settings import CONFIG, ProjectConfig
from segmentation.segment_customers import SEGMENT_FEATURES


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_version(values: object, prefix: str) -> str:
    payload = json.dumps(values, sort_keys=True, default=str).encode()
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:12]}"


def _git_revision(root: Path, override: str | None = None) -> str:
    if override:
        return override
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return "git_revision_unavailable"
    return result.stdout.strip() or "git_revision_unavailable"


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build_model_registry(project_config: ProjectConfig = CONFIG, code_version: str | None = None) -> dict[str, object]:
    validated_at = datetime.now(UTC).isoformat()
    verified_revision = _git_revision(project_config.root, code_version)
    churn_threshold = pd.read_csv(project_config.export_dir / "churn_threshold_analysis.csv")
    selected = churn_threshold.loc[churn_threshold["recommended_under_modeled_capacity"], "threshold"]
    selected_threshold = float(selected.iloc[0]) if not selected.empty else None
    calibration = pd.read_csv(project_config.export_dir / "churn_calibration_comparison.csv")
    retained = calibration.loc[calibration["retained_for_operational_use"], "method"].tolist()
    churn_eval = pd.read_csv(project_config.export_dir / "churn_model_metrics.csv").iloc[0].to_dict()
    definitions = [
        {
            "model_name": "churn_model", "algorithm": "Standardized logistic regression", "artifact": "models/churn_model.joblib",
            "metrics": churn_eval, "decision_threshold": selected_threshold, "calibration_status": retained[0] if retained else "raw_probability_retained",
            "feature_names": CHURN_FEATURES, "dataset": "data/processed/churn_model_base.csv", "validation_status": "VALIDATED_SYNTHETIC_HELDOUT",
        },
        {
            "model_name": "clv_model", "algorithm": "Regression pipeline", "artifact": "models/clv_model.joblib",
            "metrics": _json(project_config.model_dir / "clv_model_metrics.json"), "decision_threshold": None, "calibration_status": "not_applicable",
            "feature_names": [], "dataset": "data/processed/clv_base.csv", "validation_status": "VALIDATED_SYNTHETIC_HELDOUT",
        },
        {
            "model_name": "segmentation_model", "algorithm": "Standardized K-Means", "artifact": "models/segmentation_model.joblib",
            "metrics": _json(project_config.model_dir / "segmentation_metrics.json"), "decision_threshold": None, "calibration_status": "not_applicable",
            "feature_names": SEGMENT_FEATURES, "dataset": "data/processed/segmentation_base.csv", "validation_status": "VALIDATED_SYNTHETIC_UNSUPERVISED",
        },
    ]
    rows = []
    for item in definitions:
        artifact_path = project_config.root / str(item["artifact"])
        dataset_path = project_config.root / str(item["dataset"])
        model = joblib.load(artifact_path)
        params = {key: value for key, value in model.get_params(deep=True).items() if isinstance(value, (str, int, float, bool, type(None)))}
        artifact_hash = sha256_file(artifact_path)
        feature_version = _stable_version(item["feature_names"], "features")
        dataset_version = f"dataset-{sha256_file(dataset_path)[:12]}"
        rows.append({
            "model_name": item["model_name"], "model_version": f"{item['model_name']}-{artifact_hash[:12]}",
            "training_timestamp": datetime.fromtimestamp(artifact_path.stat().st_mtime, UTC).isoformat(),
            "validation_timestamp": validated_at, "dataset_version": dataset_version, "feature_version": feature_version,
            "code_version": verified_revision, "algorithm": item["algorithm"], "hyperparameters": params,
            "evaluation_metrics": item["metrics"], "decision_threshold": item["decision_threshold"],
            "calibration_status": item["calibration_status"], "artifact_path": item["artifact"], "artifact_hash": artifact_hash,
            "validation_status": item["validation_status"],
        })
    customer_volume = int(_json(project_config.model_dir / "segmentation_metrics.json").get("customers_scored", 0))
    profile = "sample_5k" if customer_volume == 5_000 else "full_250k" if customer_volume == 250_000 else "volume_unspecified"
    registry = {
        "registry_schema_version": "1.0.0",
        "generated_at": validated_at,
        "profile": profile,
        "customer_volume": customer_volume,
        "authoritative_current": profile == "sample_5k",
        "code_version_semantics": "Git revision at which artifact hashes were verified; not necessarily the original training revision.",
        "provenance_note": f"Artifact hashes verified at Git revision {verified_revision}.",
        "models": rows,
    }
    path = project_config.root / "artifacts" / "model_registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, allow_nan=False), encoding="utf-8")
    return registry


if __name__ == "__main__":
    build_model_registry()
