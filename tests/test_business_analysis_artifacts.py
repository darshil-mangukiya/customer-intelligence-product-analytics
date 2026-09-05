from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def _workbook_sheet_names(path: Path) -> str:
    with ZipFile(path) as archive:
        return archive.read("xl/workbook.xml").decode("utf-8")


def test_requirements_scope_and_user_story_counts() -> None:
    requirements = (ROOT / "business_analysis" / "business_requirements.md").read_text(encoding="utf-8")
    stories = (ROOT / "business_analysis" / "user_stories.md").read_text(encoding="utf-8")
    assert requirements.count("| CR-") == 18
    assert stories.count("**US-") == 13
    assert "reference workflow" in requirements
    assert "generated data and automated UAT evidence" in requirements


def test_traceability_and_uat_workbooks_are_real_xlsx() -> None:
    rtm = ROOT / "business_analysis" / "requirements_traceability_matrix.xlsx"
    uat = ROOT / "business_analysis" / "uat_test_plan.xlsx"
    assert rtm.stat().st_size > 5_000 and uat.stat().st_size > 5_000
    assert "Traceability Matrix" in _workbook_sheet_names(rtm)
    uat_xml = _workbook_sheet_names(uat)
    assert "UAT Plan" in uat_xml and "Execution Summary" in uat_xml


def test_uat_passes_are_tied_to_executed_evidence() -> None:
    with ZipFile(ROOT / "business_analysis" / "uat_test_plan.xlsx") as archive:
        workbook_text = "".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        )
    assert "PASS" in workbook_text
    assert "Automated local validation; see cited evidence" in workbook_text
    evidence = (ROOT / "docs" / "evidence" / "uat_execution_results.json").read_text(encoding="utf-8")
    assert evidence.count('"status": "PASS"') == 25
