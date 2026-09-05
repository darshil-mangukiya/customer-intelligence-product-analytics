from __future__ import annotations

import importlib
import struct
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_app_and_loader_exist() -> None:
    assert (ROOT / "app" / "streamlit_app.py").exists()
    assert (ROOT / "app" / "data_loader.py").exists()


def test_data_loader_imports_and_loads_core_outputs() -> None:
    loader = importlib.import_module("app.data_loader")
    datasets = loader.load_dashboard_data()
    for key in ["kpis", "customer_overview", "churn", "clv", "cohort", "product", "quality", "activation_churn"]:
        assert key in datasets
        assert hasattr(datasets[key], "frame")
    assert not datasets["kpis"].frame.empty


def test_streamlit_app_declares_expected_pages() -> None:
    text = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    expected_pages = [
        "Executive Overview",
        "Customer Segments",
        "Churn Risk",
        "CLV Analysis",
        "Cohort Retention",
        "Product Profitability",
        "Revenue Leakage",
        "Customer Drivers & Experiments",
        "Activation Lists",
        "Data Quality & Pipeline Health",
    ]
    for page in expected_pages:
        assert page in text


def test_dashboard_uses_relative_project_paths() -> None:
    combined = "\n".join(
        [
            (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8"),
            (ROOT / "app" / "data_loader.py").read_text(encoding="utf-8"),
        ]
    )
    assert "/" + "Users/" not in combined
    assert "C:\\" not in combined


def test_screenshot_readme_exists_and_no_fake_screenshots() -> None:
    screenshot_dir = ROOT / "dashboards" / "screenshots"
    assert (screenshot_dir / "README.md").exists()
    forbidden_terms = ("fake", "mock", "placeholder")
    image_files = [p for p in screenshot_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    assert not [p for p in image_files if any(term in p.name.lower() for term in forbidden_terms)]


def test_real_dashboard_screenshots_are_complete() -> None:
    screenshot_dir = ROOT / "dashboards" / "screenshots"
    expected = {
        "executive_overview.png",
        "customer_segments.png",
        "churn_risk.png",
        "clv_analysis.png",
        "cohort_retention.png",
        "product_profitability.png",
        "revenue_leakage.png",
        "activation_lists.png",
        "data_quality.png",
    }
    for filename in expected:
        path = screenshot_dir / filename
        assert path.exists(), f"Missing real dashboard capture: {filename}"
        assert path.stat().st_size > 25_000, f"Dashboard capture looks incomplete: {filename}"
        with path.open("rb") as image_file:
            assert image_file.read(8) == b"\x89PNG\r\n\x1a\n"
            image_file.read(8)
            width, height = struct.unpack(">II", image_file.read(8))
        assert (width, height) == (1440, 1100)


def test_churn_probability_distribution_uses_chart_safe_labels() -> None:
    app = importlib.import_module("app.streamlit_app")
    distribution = app.churn_probability_distribution(pd.Series([0.0, 0.2, 0.4, 0.7, 0.9, None]))
    assert distribution.index.tolist() == ["0-25%", "25-50%", "50-75%", "75-100%"]
    assert distribution["customers"].tolist() == [2, 1, 1, 1]


def test_return_leakage_uses_order_level_loss_or_sample_fallback() -> None:
    app = importlib.import_module("app.streamlit_app")

    orders = pd.DataFrame({"return_loss": [10.5, 4.5, None]})
    assert app.return_leakage_value(orders) == 15.0

    sample_orders = pd.DataFrame(
        {
            "revenue": [100.0, 80.0, 50.0],
            "discount": [0.10, 0.25, 0.0],
            "return_flag": [1, 0, 1],
        }
    )
    assert app.return_leakage_value(sample_orders) == 140.0


def test_sample_fallback_loader_works_for_missing_generated_file() -> None:
    loader = importlib.import_module("app.data_loader")
    dataset = loader.load_dataset(
        "Fallback check",
        [ROOT / "does_not_exist" / "missing.csv"],
        fallback=ROOT / "data" / "sample" / "customer_intelligence" / "customers_sample.csv",
        nrows=5,
    )
    assert dataset.is_fallback
    assert dataset.source_label == "data/sample/customer_intelligence/customers_sample.csv"
    assert not dataset.frame.empty
