from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from config.settings import CONFIG, ProjectConfig

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(_PROJECT_ROOT / ".matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_PROJECT_ROOT / ".cache"))

import matplotlib.pyplot as plt  # noqa: E402  # Configure Matplotlib cache paths first.
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402


def _kpi_value(kpis: pd.DataFrame, name: str) -> float:
    match = kpis.loc[kpis["kpi_name"].eq(name), "value"]
    return float(match.iloc[0]) if len(match) else 0.0


def _money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:.0f}"


def _pct(value: float) -> str:
    return f"{value:.1%}"


def build_executive_one_pager(project_config: ProjectConfig = CONFIG) -> Path:
    project_config.ensure_directories()
    output_dir = project_config.report_dir / "executive"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "executive_one_page_summary.pdf"
    png_path = output_dir / "executive_one_page_summary.png"

    kpis = pd.read_csv(project_config.export_dir / "kpi_summary.csv")
    segments = pd.read_csv(project_config.export_dir / "segment_kpi_comparison.csv").sort_values("profit", ascending=False)
    insights = pd.read_csv(project_config.export_dir / "stakeholder_insights.csv")
    categories = pd.read_csv(project_config.mart_dir / "mart_category_profitability.csv").sort_values("return_adjusted_profit", ascending=False)
    monitoring = pd.read_csv(project_config.export_dir / "model_monitoring_summary.csv")
    validation = pd.read_csv(project_config.export_dir / "validation_results.csv")

    fig = plt.figure(figsize=(11, 8.5), facecolor="#F7F3EA")
    fig.suptitle(
        "Customer Intelligence & Product Analytics Platform",
        x=0.06,
        y=0.96,
        ha="left",
        fontsize=20,
        fontweight="bold",
        color="#17212B",
    )
    fig.text(
        0.06,
        0.915,
        "Executive one-page summary | Customer value, churn risk, product profitability, and production readiness",
        ha="left",
        fontsize=9.5,
        color="#66717C",
    )

    metrics = [
        ("Net Revenue", _money(_kpi_value(kpis, "Total Net Revenue"))),
        ("Profit", _money(_kpi_value(kpis, "Total Return-adjusted Profit"))),
        ("Churn", _pct(_kpi_value(kpis, "Churn Rate"))),
        ("Retention", _pct(_kpi_value(kpis, "Retention Rate"))),
        ("Leakage", _money(_kpi_value(kpis, "Revenue Leakage from Returns and Discounts"))),
    ]
    for idx, (label, value) in enumerate(metrics):
        x = 0.06 + idx * 0.18
        fig.text(x, 0.84, value, fontsize=18, fontweight="bold", color="#17212B")
        fig.text(x, 0.812, label.upper(), fontsize=7.5, fontweight="bold", color="#176B87")

    ax1 = fig.add_axes([0.06, 0.50, 0.42, 0.23], facecolor="#F7F3EA")
    top_segments = segments.head(5).iloc[::-1]
    ax1.barh(top_segments["segment_name"].str.replace(r" \d+$", "", regex=True), top_segments["profit"], color="#176B87")
    ax1.set_title("Segment profit concentration", loc="left", fontsize=11, fontweight="bold")
    ax1.tick_params(axis="both", labelsize=7)
    ax1.xaxis.set_major_formatter(lambda value, _: _money(value))
    for spine in ax1.spines.values():
        spine.set_visible(False)

    ax2 = fig.add_axes([0.56, 0.50, 0.38, 0.23], facecolor="#F7F3EA")
    top_categories = categories.head(5).iloc[::-1]
    ax2.barh(top_categories["category"], top_categories["return_adjusted_profit"], color="#C47F2C")
    ax2.set_title("Category return-adjusted profit", loc="left", fontsize=11, fontweight="bold")
    ax2.tick_params(axis="both", labelsize=7)
    ax2.xaxis.set_major_formatter(lambda value, _: _money(value))
    for spine in ax2.spines.values():
        spine.set_visible(False)

    fig.text(0.06, 0.43, "Top stakeholder insights", fontsize=12, fontweight="bold", color="#17212B")
    for idx, row in enumerate(insights.head(4).to_dict("records")):
        y = 0.395 - idx * 0.055
        fig.text(0.06, y, f"{idx + 1}. {row['insight']}", fontsize=8.5, fontweight="bold", color="#17212B")
        fig.text(0.08, y - 0.025, row["recommended_action"], fontsize=7.5, color="#66717C")

    fig.text(0.56, 0.43, "Production readiness", fontsize=12, fontweight="bold", color="#17212B")
    readiness = [
        ("Validation", f"{(validation.status == 'PASS').sum()}/{len(validation)} checks passed"),
        ("Monitoring", f"{(monitoring.status == 'PASS').sum()}/{len(monitoring)} signals pass"),
        ("Watch item", "Retention rate below executive threshold"),
    ]
    for idx, (label, value) in enumerate(readiness):
        y = 0.395 - idx * 0.06
        fig.text(0.56, y, label.upper(), fontsize=7.5, fontweight="bold", color="#176B87")
        fig.text(0.56, y - 0.025, value, fontsize=9, color="#17212B")

    fig.text(
        0.06,
        0.075,
        "Decision rule: protect profitable loyal customers, fix return-heavy categories, grow high-CLV acquisition paths, and monitor drift/quality before every executive refresh.",
        fontsize=9,
        color="#17212B",
        fontweight="bold",
    )
    fig.text(0.06, 0.045, "Source: generated platform marts, KPI engine, validation framework, model monitoring, and model registry.", fontsize=7, color="#66717C")

    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(png_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return pdf_path


def main() -> None:
    path = build_executive_one_pager()
    print(path)


if __name__ == "__main__":
    main()
