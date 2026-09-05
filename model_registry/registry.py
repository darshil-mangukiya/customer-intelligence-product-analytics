from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


@dataclass(frozen=True)
class RegisteredModel:
    model_name: str
    artifact_path: Path
    metrics_path: Path
    model_type: str
    evaluation_output: str
    owner: str
    business_use: str
    champion_metric: str
    minimum_threshold: float
    refresh_strategy: str
    model_card_path: str


def _models(project_config: ProjectConfig) -> list[RegisteredModel]:
    return [
        RegisteredModel(
            "churn_model",
            project_config.model_dir / "churn_model.joblib",
            project_config.model_dir / "churn_metrics.json",
            "Logistic Regression",
            "outputs/churn_model_evaluation.csv",
            "Customer Analytics",
            "Score churn probability and expected profit at risk.",
            "roc_auc",
            0.75,
            "Retrain after major feature changes or scheduled scoring refresh.",
            "docs/model_cards/churn_model_card.md",
        ),
        RegisteredModel(
            "clv_model",
            project_config.model_dir / "clv_model.joblib",
            project_config.model_dir / "clv_model_metrics.json",
            "Regression",
            "outputs/clv_model_evaluation.csv",
            "Customer Analytics",
            "Estimate predicted customer value and CLV at risk.",
            "r2",
            0.10,
            "Retrain after customer value distribution or channel mix shifts.",
            "docs/model_cards/clv_model_card.md",
        ),
        RegisteredModel(
            "segmentation_model",
            project_config.model_dir / "segmentation_model.joblib",
            project_config.model_dir / "segmentation_metrics.json",
            "K-Means",
            "outputs/segmentation_evaluation.csv",
            "Customer Analytics",
            "Assign customer segments and business recommendations.",
            "silhouette_score",
            0.20,
            "Review clusters after major cohort, channel, or product mix changes.",
            "docs/model_cards/segmentation_model_card.md",
        ),
    ]


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_metrics(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def register_models(project_config: ProjectConfig = CONFIG) -> pd.DataFrame:
    project_config.ensure_directories()
    (project_config.root / "outputs").mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows: list[dict[str, object]] = []

    for model in _models(project_config):
        metrics = _read_metrics(model.metrics_path)
        champion_value = metrics.get(model.champion_metric)
        artifact_exists = model.artifact_path.exists()
        status = (
            "CHAMPION"
            if artifact_exists and isinstance(champion_value, (int, float)) and champion_value >= model.minimum_threshold
            else "WATCH"
        )
        rows.append(
            {
                "run_id": run_id,
                "model_name": model.model_name,
                "version": f"{model.model_name}-{run_id}",
                "model_type": model.model_type,
                "artifact_path": _relative(model.artifact_path, project_config.root),
                "artifact_exists": artifact_exists,
                "artifact_sha256": _sha256(model.artifact_path),
                "metrics_path": _relative(model.metrics_path, project_config.root),
                "evaluation_output": model.evaluation_output,
                "champion_metric": model.champion_metric,
                "champion_metric_value": champion_value,
                "minimum_threshold": model.minimum_threshold,
                "registry_status": status,
                "owner": model.owner,
                "business_use": model.business_use,
                "refresh_strategy": model.refresh_strategy,
                "model_card_path": model.model_card_path,
            }
        )

    registry = pd.DataFrame(rows)
    write_csv(registry, project_config.audit_dir / "model_registry.csv")

    history_path = project_config.audit_dir / "model_registry_history.csv"
    if history_path.exists():
        history = pd.read_csv(history_path)
        history = pd.concat([history, registry], ignore_index=True)
    else:
        history = registry.copy()
    write_csv(history, history_path)
    _write_public_registry(registry, project_config)
    _ensure_approved_model_cards(registry, project_config)
    return registry


def _write_public_registry(registry: pd.DataFrame, project_config: ProjectConfig) -> None:
    segmentation_metrics = _read_metrics(project_config.model_dir / "segmentation_metrics.json")
    customer_volume = int(segmentation_metrics.get("customers_scored", 0))
    profile = "sample_5k" if customer_volume == 5_000 else "full_250k" if customer_volume == 250_000 else "volume_unspecified"
    registry = registry.assign(
        profile=profile,
        customer_volume=customer_volume,
        authoritative_current=profile == "sample_5k",
    )
    public_registry = registry[
        [
            "profile",
            "customer_volume",
            "authoritative_current",
            "model_name",
            "model_type",
            "artifact_path",
            "evaluation_output",
            "champion_metric",
            "champion_metric_value",
            "owner",
            "business_use",
            "refresh_strategy",
        ]
    ].rename(
        columns={
            "champion_metric": "primary_metric",
            "champion_metric_value": "primary_metric_value",
        }
    )
    write_csv(public_registry, project_config.root / "outputs" / "model_registry.csv")


def _ensure_approved_model_cards(registry: pd.DataFrame, project_config: ProjectConfig) -> None:
    for row in registry.to_dict("records"):
        path = project_config.root / str(row["model_card_path"])
        if path.exists():
            continue
        lines = [
            "# " + str(row["model_name"]).replace("_", " ").title(),
            "",
            "Registry-generated model card placeholder for approved model-card coverage.",
            "",
            "## Business Use",
            f"- {row['business_use']}",
            "",
            "## Registry Status",
            f"- Status: `{row['registry_status']}`",
            f"- Primary metric: `{row['champion_metric']}` = `{row['champion_metric_value']}`",
            f"- Minimum threshold: `{row['minimum_threshold']}`",
        ]
        write_markdown(lines, path)


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description="Register current model artifacts and metrics.").parse_args()


def main() -> None:
    parse_args()
    register_models()


if __name__ == "__main__":
    main()
