from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProjectConfig:
    """Centralized path and business calendar configuration."""

    root: Path = PROJECT_ROOT
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    mart_dir: Path = PROJECT_ROOT / "data" / "marts"
    export_dir: Path = PROJECT_ROOT / "data" / "exports"
    rejected_dir: Path = PROJECT_ROOT / "data" / "rejected"
    audit_dir: Path = PROJECT_ROOT / "data" / "audit"
    report_dir: Path = PROJECT_ROOT / "reports"
    model_dir: Path = PROJECT_ROOT / "models"
    analysis_date: str = "2026-01-31"
    currency: str = "USD"

    def ensure_directories(self) -> None:
        for path in [
            self.raw_dir,
            self.processed_dir,
            self.mart_dir,
            self.export_dir,
            self.rejected_dir,
            self.audit_dir,
            self.report_dir,
            self.model_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


CONFIG = ProjectConfig()

