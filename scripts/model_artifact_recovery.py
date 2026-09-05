from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from churn_model.train_churn_model import train_churn_model
from clv.model_clv import run_clv_model
from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown
from segmentation.segment_customers import run_segmentation


def temporary_config(root: Path) -> ProjectConfig:
    return ProjectConfig(
        root=root,
        raw_dir=root / "data" / "raw",
        processed_dir=root / "data" / "processed",
        mart_dir=root / "data" / "marts",
        export_dir=root / "data" / "exports",
        rejected_dir=root / "data" / "rejected",
        audit_dir=root / "data" / "audit",
        report_dir=root / "reports",
        model_dir=root / "models",
    )


def prepare_inputs(config: ProjectConfig) -> None:
    config.ensure_directories()
    for name in (
        "churn_model_base.csv",
        "segmentation_base.csv",
        "customer_features.csv",
        "customers_clean.csv",
        "transactions_enriched.csv",
        "web_behavior_clean.csv",
        "engagement_clean.csv",
    ):
        shutil.copy2(CONFIG.processed_dir / name, config.processed_dir / name)


def run_once(root: Path) -> dict[str, object]:
    config = temporary_config(root)
    prepare_inputs(config)
    churn = train_churn_model(config)
    segmentation = run_segmentation(config)
    clv = run_clv_model(config)
    return {"churn": churn, "segmentation": segmentation, "clv": clv}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p3-model-recovery-") as temporary:
        first = run_once(Path(temporary) / "first")
        second = run_once(Path(temporary) / "second")

        churn_first = first["churn"]["scored"].sort_values("customer_id")
        churn_second = second["churn"]["scored"].sort_values("customer_id")
        churn_difference = float(
            np.max(np.abs(churn_first["churn_probability"].to_numpy() - churn_second["churn_probability"].to_numpy()))
        )

        segment_first = first["segmentation"]["assignments"].sort_values("customer_id")
        segment_second = second["segmentation"]["assignments"].sort_values("customer_id")
        segment_match = float((segment_first["cluster_id"].to_numpy() == segment_second["cluster_id"].to_numpy()).mean())

        clv_first = first["clv"]["clv"].sort_values("customer_id")
        clv_second = second["clv"]["clv"].sort_values("customer_id")
        clv_difference = float(
            np.max(np.abs(clv_first["predicted_12m_clv"].to_numpy() - clv_second["predicted_12m_clv"].to_numpy()))
        )

    rows = [
        {"model": "churn", "comparison": "maximum probability difference", "observed": churn_difference, "required": 0.0, "status": "PASS" if churn_difference == 0 else "FAIL"},
        {"model": "segmentation", "comparison": "cluster assignment match rate", "observed": segment_match, "required": 1.0, "status": "PASS" if segment_match == 1 else "FAIL"},
        {"model": "clv", "comparison": "maximum predicted CLV difference", "observed": clv_difference, "required": 0.0, "status": "PASS" if clv_difference == 0 else "FAIL"},
    ]
    results = pd.DataFrame(rows)
    write_csv(results, CONFIG.audit_dir / "model_artifact_recovery.csv")
    report = [
        "# Model Artifact Recovery Check",
        "",
        "Churn, segmentation, and CLV artifacts were regenerated twice from the same processed synthetic inputs, code, configuration, and seed in disposable directories.",
        "",
        "| Model | Meaningful comparison | Observed | Required | Status |",
        "|---|---|---:|---:|---|",
    ]
    for row in rows:
        report.append(f"| {row['model']} | {row['comparison']} | {row['observed']:.12g} | {row['required']:.12g} | {row['status']} |")
    report.extend(
        [
            "",
            "Meaningful predictions/assignments were compared instead of serialized bytes because serialization metadata is not the model behavior contract.",
        ]
    )
    write_markdown(report, CONFIG.report_dir / "model_artifact_recovery.md")
    if not results["status"].eq("PASS").all():
        raise SystemExit("Model artifact recovery check failed")


if __name__ == "__main__":
    main()
