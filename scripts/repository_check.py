from __future__ import annotations

import hashlib
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SCREENSHOT_FILES = [
    "executive_overview.png",
    "customer_segments.png",
    "churn_risk.png",
    "clv_analysis.png",
    "cohort_retention.png",
    "product_profitability.png",
    "revenue_leakage.png",
    "activation_lists.png",
    "data_quality.png",
]

POWERBI_SCREENSHOT_FILES = [
    "powerbi_executive_overview.png",
    "powerbi_customer_segments.png",
    "powerbi_churn_retention.png",
    "powerbi_clv_analysis.png",
    "powerbi_cohort_retention.png",
    "powerbi_product_profitability.png",
    "powerbi_activation_center.png",
]

TABLEAU_SCREENSHOT_FILES = [
    "01_executive_overview.png",
    "02_customer_segmentation.png",
    "03_churn_retention.png",
    "04_clv_analysis.png",
    "05_cohort_retention.png",
    "06_product_profitability.png",
    "07_experiment_decision_evidence.png",
    "08_customer_retention_story.png",
]


REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "Makefile",
    "docker-compose.yml",
    "requirements.txt",
    ".env.example",
    ".github/workflows/ci.yml",
    "api/main.py",
    "app/data_loader.py",
    "app/streamlit_app.py",
    "etl/run_pipeline.py",
    "etl/synthetic_data.py",
    "feature_engineering/build_features.py",
    "churn_model/train_churn_model.py",
    "clv/model_clv.py",
    "segmentation/segment_customers.py",
    "cohort_analysis/build_cohorts.py",
    "product_analytics/product_insights.py",
    "activation/build_activation_exports.py",
    "observability/enterprise_quality.py",
    "sql/postgres/init/schema_postgres.sql",
    "sql/postgres/marts/customer_intelligence_marts.sql",
    "dbt/dbt_project.yml",
    "docs/architecture_overview.md",
    "docs/data_lineage.md",
    "docs/source_to_target_mapping.md",
    "docs/dimensional_model.md",
    "docs/data_dictionary.md",
    "docs/data_cleaning_summary.md",
    "docs/data_contracts.md",
    "docs/business_requirements.md",
    "docs/data_quality_framework.md",
    "docs/observability_runbook.md",
    "docs/troubleshooting_guide.md",
    "docs/performance_optimization.md",
    "docs/feature_catalog.md",
    "docs/kpi_dictionary.md",
    "docs/semantic_layer.md",
    "docs/model_cards/churn_model_card.md",
    "docs/model_cards/clv_model_card.md",
    "docs/model_cards/segmentation_model_card.md",
    "docs/diagrams/system_architecture.md",
    "docs/diagrams/data_flow.md",
    "docs/diagrams/warehouse_model.md",
    "docs/diagrams/ml_pipeline.md",
    "docs/diagrams/dashboard_layer.md",
    "dashboards/specs/powerbi_dashboard_spec.md",
    "dashboards/specs/powerbi_implementation_guide.md",
    "dashboards/specs/tableau_dashboard_spec.md",
    "dashboards/tableau/README.md",
    "dashboards/tableau/tableau_data_manifest.yml",
    "dashboards/tableau/MANUAL_TABLEAU_BUILD_AND_VALIDATION.md",
    "dashboards/tableau/calculations/CALCULATED_FIELDS.md",
    "dashboards/tableau/workbook/WORKBOOK_SPEC.md",
    "dashboards/tableau/workbook/Customer_Intelligence_Product_Analytics.twb",
    "dashboards/tableau/workbook/Customer_Intelligence_Product_Analytics.twbx",
    "dashboards/tableau/build/build_tableau_workbook.py",
    "dashboards/tableau/validation/tableau_reconciliation_report.csv",
    "dashboards/tableau/validation/tableau_validation_report.md",
    "dashboards/tableau/validation/tableau_workbook_structural_validation.md",
    "dashboards/tableau/validation/tableau_worksheet_binding_audit.csv",
    "dashboards/tableau/validation/tableau_datasource_audit.csv",
    "dashboards/tableau/validation/tableau_36_worksheet_repair_status.csv",
    "dashboards/tableau/validation/tableau_calculation_runtime_status.csv",
    "dashboards/tableau/screenshots/README.md",
    "docs/case_studies/retention_review_case_study.md",
    "dashboards/specs/dashboard_qa_checklist.md",
    "dashboards/specs/uat_checklist.md",
    "dashboards/specs/dax_measure_catalog.md",
    "dashboards/specs/semantic_model_plan.md",
    "dashboards/screenshots/README.md",
    "reports/business_recommendations.md",
    "reports/performance/sql_performance_summary.md",
    "reports/excel/customer_intelligence_scorecard.xlsx",
    "scripts/ci_check.py",
    "scripts/repository_check.py",
    "analytics/customer_decision_support.py",
    "analytics/experiment_design.py",
    "analytics/retention_economics.py",
    "ai/copilot.py",
    "ai/evals/run_evals.py",
    "business_analysis/business_requirements.md",
    "business_analysis/user_stories.md",
    "business_analysis/implementation_plan.md",
    "business_analysis/change_impact_assessment.md",
    "business_analysis/requirements_traceability_matrix.xlsx",
    "business_analysis/uat_test_plan.xlsx",
    "governance/ai_data_policy.md",
    "governance/customer_metrics_dictionary.md",
]


REQUIRED_OUTPUTS = [
    "outputs/feature_catalog.csv",
    "outputs/kpi_catalog.csv",
    "outputs/model_registry.csv",
    "outputs/model_scoring_log.csv",
    "outputs/data_quality_summary.csv",
    "outputs/mart_freshness_report.csv",
    "outputs/activation_export_manifest.csv",
    "outputs/activation_churn_campaign.csv",
    "outputs/activation_cross_sell_targets.csv",
    "outputs/activation_winback_campaign.csv",
    "outputs/activation_high_clv_customers.csv",
    "outputs/activation_loyalty_upgrade_targets.csv",
    "outputs/activation_discount_sensitive_customers.csv",
]


REQUIRED_DIRS = [
    "api",
    "app",
    "activation",
    "dashboards",
    "dashboards/powerbi",
    "dashboards/powerbi/screenshots",
    "dashboards/specs",
    "dashboards/tableau",
    "dashboards/tableau/data",
    "dashboards/tableau/validation",
    "dashboards/screenshots",
    "docs",
    "docs/diagrams",
    "docs/model_cards",
    "etl",
    "feature_engineering",
    "models",
    "observability",
    "outputs",
    "reports/excel",
    "reports/performance",
    "scripts",
    "sql",
    "sql/analysis",
    "tests",
    "ai",
    "business_analysis",
    "governance",
]


REQUIRED_TESTS = [
    "tests/test_repository_assets.py",
    "tests/test_api_orchestration_registry.py",
    "tests/test_feature_engineering.py",
    "tests/test_validation_monitoring.py",
    "tests/test_streamlit_dashboard.py",
    "tests/test_customer_decision_support.py",
    "tests/test_ai_copilot.py",
    "tests/test_business_analysis_artifacts.py",
    "tests/test_tableau_presentation_layer.py",
]


FORBIDDEN_PATHS = [
    ".github/workflows/pages.yml",
    ".nojekyll",
    "docs/archive",
    "docs/portfolio",
    "docs/model_registry",
    "portfolio_site",
    "portfolio_assets",
    "reports/portfolio",
    "outputs/manual-customer-intelligence",
    "docs/github_repository_setup.md",
    "docs/business_impact_summary.md",
    "docs/portfolio_case_study.md",
    "docs/churn_model_card.md",
    "reports/portfolio_case_study.py",
    "dashboards/powerbi_dax_measure_catalog.md",
]


FORBIDDEN_HELPER_NAME_PARTS = [
    "interview_answer_bank",
    "interview_walkthrough",
    "interview_talk_track",
    "interview_talking_points",
    "recruiter_pitch",
    "recruiter_project_summary",
    "resume_outputs",
    "linkedin_github_description",
    "star_stories",
    "role_positioning",
    "website_copy",
    "project_summary_short",
    "project_summary_detailed",
]


FORBIDDEN_README_PATTERNS = [
    "docs/portfolio",
    "portfolio_site",
    "portfolio_assets",
    "GitHub Pages",
    "resume bullet",
    "Resume",
    "interview",
    "Interview",
    "recruiter",
    "Recruiter",
    "LinkedIn",
    "role positioning",
    "website copy",
    "final-portfolio-check",
    "portfolio-polish",
    "make portfolio",
]


ALLOWED_DASHBOARD_SPEC_FILES = {
    "activation_dashboard_wireframe.md",
    "churn_dashboard_wireframe.md",
    "clv_dashboard_wireframe.md",
    "cohort_dashboard_wireframe.md",
    "customer_dashboard_wireframe.md",
    "dashboard_mockups.md",
    "dashboard_qa_checklist.md",
    "dax_measure_catalog.md",
    "demo_script.md",
    "executive_dashboard_wireframe.md",
    "powerbi_dashboard_build_guide.md",
    "powerbi_dashboard_spec.md",
    "product_dashboard_wireframe.md",
    "relationship_diagram.md",
    "revenue_leakage_dashboard_wireframe.md",
    "powerbi_implementation_guide.md",
    "semantic_model_plan.md",
    "tableau_dashboard_build_guide.md",
    "tableau_dashboard_spec.md",
    "tableau_extract_manifest.md",
    "uat_checklist.md",
}


def _is_external(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "#"))


def _clean_target(target: str) -> str:
    target = target.strip().split()[0]
    target = target.split("#", 1)[0]
    return unquote(target)


def _check_required_files() -> list[str]:
    errors: list[str] = []
    for rel_path in REQUIRED_FILES + REQUIRED_OUTPUTS + REQUIRED_TESTS:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"Missing required file: {rel_path}")
            continue
        if path.suffix != ".csv" and path.name != ".gitkeep":
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if len(text) < 20:
                errors.append(f"File looks empty or placeholder-only: {rel_path}")
            pending_marker = "TO" + "DO"
            if path.suffix in {".md", ".txt"} and pending_marker in text:
                errors.append(f"File contains pending-work marker: {rel_path}")
    return errors


def _check_required_dirs() -> list[str]:
    return [f"Missing required directory: {rel_path}" for rel_path in REQUIRED_DIRS if not (ROOT / rel_path).is_dir()]


def _check_sql_analysis_examples() -> list[str]:
    sql_dir = ROOT / "sql" / "analysis"
    if not sql_dir.is_dir():
        return ["Missing SQL analysis directory: sql/analysis"]
    sql_files = sorted(sql_dir.glob("*.sql"))
    errors: list[str] = []
    if len(sql_files) < 8:
        errors.append(f"Expected at least 8 SQL analysis files, found {len(sql_files)}")
    required_terms = ["business question", "source marts/tables", "with ", "case", "select"]
    for path in sql_files:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        missing_terms = [term for term in required_terms if term not in text]
        if missing_terms:
            errors.append(f"SQL analysis file lacks required analyst structure ({', '.join(missing_terms)}): {path.relative_to(ROOT)}")
    return errors


def _check_excel_artifact() -> list[str]:
    xlsx = ROOT / "reports" / "excel" / "customer_intelligence_scorecard.xlsx"
    csv_fallback = ROOT / "reports" / "excel" / "customer_intelligence_scorecard.csv"
    fallback_readme = ROOT / "reports" / "excel" / "README.md"
    if xlsx.exists() and xlsx.stat().st_size > 1000:
        return []
    if csv_fallback.exists() and fallback_readme.exists():
        return []
    return ["Missing Excel scorecard artifact or documented CSV fallback under reports/excel/"]


def _check_streamlit_dashboard() -> list[str]:
    errors: list[str] = []
    app_path = ROOT / "app" / "streamlit_app.py"
    loader_path = ROOT / "app" / "data_loader.py"
    screenshot_readme = ROOT / "dashboards" / "screenshots" / "README.md"
    if not app_path.exists():
        errors.append("Missing Streamlit app: app/streamlit_app.py")
    if not loader_path.exists():
        errors.append("Missing Streamlit data loader: app/data_loader.py")
    if not screenshot_readme.exists():
        errors.append("Missing dashboard screenshot README")
    app_text = app_path.read_text(encoding="utf-8", errors="ignore") if app_path.exists() else ""
    required_page_names = [
        "Executive Overview",
        "Customer Segments",
        "Churn Risk",
        "CLV Analysis",
        "Cohort Retention",
        "Product Profitability",
        "Revenue Leakage",
        "Activation Lists",
        "Data Quality & Pipeline Health",
    ]
    for page_name in required_page_names:
        if page_name not in app_text:
            errors.append(f"Streamlit app missing expected page label: {page_name}")
    forbidden_path_tokens = ["/" + "Users/", "C:\\\\", "portfolio_site", "portfolio_assets"]
    combined = app_text + "\n" + (loader_path.read_text(encoding="utf-8", errors="ignore") if loader_path.exists() else "")
    for token in forbidden_path_tokens:
        if token in combined:
            errors.append(f"Streamlit dashboard should not hardcode local/helper path token: {token}")
    screenshot_dir = ROOT / "dashboards" / "screenshots"
    if screenshot_dir.exists():
        for path in screenshot_dir.iterdir():
            lowered = path.name.lower()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and any(term in lowered for term in ["fake", "mock", "placeholder"]):
                errors.append(f"Fake/mock/placeholder screenshot file is not allowed: {path.relative_to(ROOT)}")
        screenshot_doc = screenshot_readme.read_text(encoding="utf-8", errors="ignore") if screenshot_readme.exists() else ""
        for filename in SCREENSHOT_FILES:
            path = screenshot_dir / filename
            if not path.exists():
                errors.append(f"Missing real Streamlit screenshot: dashboards/screenshots/{filename}")
                continue
            if path.stat().st_size <= 25_000:
                errors.append(f"Streamlit screenshot looks incomplete: dashboards/screenshots/{filename}")
            if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                errors.append(f"Streamlit screenshot is not a valid PNG: dashboards/screenshots/{filename}")
            if filename not in screenshot_doc:
                errors.append(f"Screenshot README does not document: {filename}")
    return errors


def _is_lfs_pointer(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return (
        text.startswith("version https://git-lfs.github.com/spec/v1")
        and "\noid sha256:" in text
        and "\nsize " in text
    )


def _check_powerbi_dashboard() -> list[str]:
    errors: list[str] = []
    pbix_path = ROOT / "dashboards" / "powerbi" / "Customer_Intelligence_Product_Analytics.pbix"
    screenshot_dir = ROOT / "dashboards" / "powerbi" / "screenshots"
    if not pbix_path.exists():
        errors.append("Missing Power BI dashboard: dashboards/powerbi/Customer_Intelligence_Product_Analytics.pbix")
    elif pbix_path.stat().st_size <= 100_000:
        if not (os.getenv("CI") == "true" and _is_lfs_pointer(pbix_path)):
            errors.append("Power BI dashboard file looks too small to be a valid PBIX asset")
    if not screenshot_dir.exists():
        errors.append("Missing Power BI screenshot directory: dashboards/powerbi/screenshots")
        return errors
    for filename in POWERBI_SCREENSHOT_FILES:
        path = screenshot_dir / filename
        if not path.exists():
            errors.append(f"Missing Power BI screenshot: dashboards/powerbi/screenshots/{filename}")
            continue
        if path.stat().st_size <= 25_000:
            errors.append(f"Power BI screenshot looks incomplete: dashboards/powerbi/screenshots/{filename}")
        if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            errors.append(f"Power BI screenshot is not a valid PNG: dashboards/powerbi/screenshots/{filename}")
    return errors


def _check_tableau_evidence() -> list[str]:
    errors: list[str] = []
    screenshot_dir = ROOT / "dashboards" / "tableau" / "screenshots"
    screenshot_readme = screenshot_dir / "README.md"
    if not screenshot_dir.exists():
        return ["Missing Tableau screenshot directory: dashboards/tableau/screenshots"]
    documented = screenshot_readme.read_text(encoding="utf-8", errors="ignore") if screenshot_readme.exists() else ""
    actual_pngs = {path.name for path in screenshot_dir.glob("*.png")}
    expected_pngs = set(TABLEAU_SCREENSHOT_FILES)
    if actual_pngs != expected_pngs:
        errors.append(
            "Tableau screenshot set must contain exactly the eight canonical files; "
            f"missing={sorted(expected_pngs - actual_pngs)}, extra={sorted(actual_pngs - expected_pngs)}"
        )
    hashes: set[str] = set()
    for filename in TABLEAU_SCREENSHOT_FILES:
        path = screenshot_dir / filename
        if not path.exists():
            continue
        if path.stat().st_size <= 100_000:
            errors.append(f"Tableau screenshot looks incomplete: dashboards/tableau/screenshots/{filename}")
        data = path.read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            errors.append(f"Tableau screenshot is not a valid PNG: dashboards/tableau/screenshots/{filename}")
        hashes.add(hashlib.sha256(data).hexdigest())
        if filename not in documented:
            errors.append(f"Tableau screenshot README does not document: {filename}")
    if len(hashes) != len(TABLEAU_SCREENSHOT_FILES):
        errors.append("Tableau screenshots must be eight distinct PNG files")
    twb = ROOT / "dashboards" / "tableau" / "workbook" / "Customer_Intelligence_Product_Analytics.twb"
    if twb.exists():
        twb_bytes = twb.read_bytes()
        for token in (b"/Users/" + b"darshil/", b"file:///Users/" + b"darshil/", b"/var/" + b"folders/", b"Tableau" + b"Temp"):
            if token in twb_bytes:
                errors.append("Final Tableau TWB contains a forbidden local filesystem path token")
                break
    twbx = ROOT / "dashboards" / "tableau" / "workbook" / "Customer_Intelligence_Product_Analytics.twbx"
    if twbx.exists():
        try:
            with zipfile.ZipFile(twbx) as package:
                corrupt_entry = package.testzip()
                if corrupt_entry is not None:
                    errors.append(f"Tableau TWBX contains a corrupt entry: {corrupt_entry}")
                for name in package.namelist():
                    payload = package.read(name)
                    for token in (b"/Users/" + b"darshil/", b"file:///Users/" + b"darshil/", b"/var/" + b"folders/", b"Tableau" + b"Temp"):
                        if token in payload:
                            errors.append(f"Tableau TWBX entry contains a forbidden local path token: {name}")
                            break
        except zipfile.BadZipFile:
            errors.append("Final Tableau TWBX is not a valid packaged workbook archive")
    return errors


def _check_forbidden_paths() -> list[str]:
    errors: list[str] = []
    for rel_path in FORBIDDEN_PATHS:
        if (ROOT / rel_path).exists():
            errors.append(f"Forbidden website/helper/duplicate path still exists: {rel_path}")
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        lowered = rel.lower()
        if any(part in lowered for part in FORBIDDEN_HELPER_NAME_PARTS):
            errors.append(f"Forbidden job-search or website helper file still exists: {rel}")
    return sorted(set(errors))


def _check_dashboard_location() -> list[str]:
    errors: list[str] = []
    dashboard_root = ROOT / "dashboards"
    if not dashboard_root.exists():
        return ["Missing dashboards directory"]
    for path in dashboard_root.rglob("*.md"):
        rel = path.relative_to(ROOT).as_posix()
        if path == ROOT / "dashboards" / "screenshots" / "README.md":
            continue
        if (ROOT / "dashboards" / "tableau") in path.parents:
            continue
        if path.parent != ROOT / "dashboards" / "specs":
            errors.append(f"Dashboard markdown should live under dashboards/specs/: {rel}")
        elif path.name not in ALLOWED_DASHBOARD_SPEC_FILES:
            errors.append(f"Unexpected dashboard spec file: {rel}")
    return errors


def _check_model_cards_location() -> list[str]:
    errors: list[str] = []
    for path in ROOT.rglob("*model_card*.md"):
        if ".git" in path.parts or not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if path.parent != ROOT / "docs" / "model_cards":
            errors.append(f"Model card should live under docs/model_cards/: {rel}")
    return errors


def _check_links() -> list[str]:
    errors: list[str] = []
    markdown_files = [ROOT / "README.md"] + list((ROOT / "docs").rglob("*.md")) + list((ROOT / "dashboards").rglob("*.md"))
    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8", errors="ignore")
        for raw_target in LINK_RE.findall(text):
            target = _clean_target(raw_target)
            if not target or _is_external(target):
                continue
            base = markdown_file.parent
            if not (base / target).exists() and not (ROOT / target).exists():
                errors.append(f"{markdown_file.relative_to(ROOT)} has missing local link: {raw_target}")
    return errors


def _check_readme_is_clean() -> list[str]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    return [f"README should not reference `{pattern}`" for pattern in FORBIDDEN_README_PATTERNS if pattern in readme]


def _check_makefile_targets() -> list[str]:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8", errors="ignore")
    required_targets = ["customer-intelligence:", "enterprise-upgrade:", "enterprise-assets:", "enterprise-quality:", "activation:", "sql-analysis-check:", "reports-check:", "streamlit:", "streamlit-check:", "final-repo-check:", "ci-check:", "test:"]
    forbidden_targets = ["portfolio-polish:", "final-portfolio-check:", "portfolio:"]
    errors = [f"Missing Makefile target: {target}" for target in required_targets if target not in makefile]
    errors.extend(f"Forbidden portfolio-only Makefile target still exists: {target}" for target in forbidden_targets if target in makefile)
    return errors


def main() -> None:
    errors: list[str] = []
    errors.extend(_check_required_dirs())
    errors.extend(_check_required_files())
    errors.extend(_check_sql_analysis_examples())
    errors.extend(_check_excel_artifact())
    errors.extend(_check_streamlit_dashboard())
    errors.extend(_check_powerbi_dashboard())
    errors.extend(_check_tableau_evidence())
    errors.extend(_check_forbidden_paths())
    errors.extend(_check_dashboard_location())
    errors.extend(_check_model_cards_location())
    errors.extend(_check_links())
    errors.extend(_check_readme_is_clean())
    errors.extend(_check_makefile_targets())
    if errors:
        formatted = "\n".join(f"- {error}" for error in sorted(set(errors)))
        raise SystemExit(f"Final repository check failed:\n{formatted}")
    print("Final repository check passed.")


if __name__ == "__main__":
    main()
