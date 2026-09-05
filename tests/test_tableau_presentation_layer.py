from __future__ import annotations

import csv
import hashlib
import json
import re
import runpy
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TABLEAU = ROOT / "dashboards" / "tableau"
TWB = TABLEAU / "workbook/Customer_Intelligence_Product_Analytics.twb"
TWBX = TABLEAU / "workbook/Customer_Intelligence_Product_Analytics.twbx"
BINDING_AUDIT_CSV = TABLEAU / "validation/tableau_worksheet_binding_audit.csv"
DATASOURCE_AUDIT_CSV = TABLEAU / "validation/tableau_datasource_audit.csv"
REPAIR_STATUS_CSV = TABLEAU / "validation/tableau_36_worksheet_repair_status.csv"
CALCULATION_STATUS_CSV = TABLEAU / "validation/tableau_calculation_runtime_status.csv"
GENERATOR = TABLEAU / "build/build_tableau_workbook.py"
SCREENSHOT_DIR = TABLEAU / "screenshots"
SCREENSHOT_FILES = {
    "01_executive_overview.png",
    "02_customer_segmentation.png",
    "03_churn_retention.png",
    "04_clv_analysis.png",
    "05_cohort_retention.png",
    "06_product_profitability.png",
    "07_experiment_decision_evidence.png",
    "08_customer_retention_story.png",
}


def _manifest_entries() -> list[dict[str, object]]:
    text = (TABLEAU / "tableau_data_manifest.yml").read_text()
    chunks = re.split(r"\n  - id: ", text)[1:]
    entries = []
    for chunk in chunks:
        source_id = chunk.splitlines()[0].strip()
        fields: dict[str, object] = {"id": source_id}
        for key in ("file", "source_mart", "grain", "row_count", "primary_key", "checksum_sha256"):
            match = re.search(rf"^    {key}: (.+)$", chunk, re.MULTILINE)
            assert match, f"{source_id} missing {key}"
            raw = match.group(1).strip()
            fields[key] = json.loads(raw) if raw.startswith('"') else int(raw) if raw.isdigit() else raw
        columns_match = re.search(
            r"    expected_columns:\n((?:      - .+\n?)+)", chunk, re.MULTILINE
        )
        assert columns_match, f"{source_id} missing expected_columns"
        fields["expected_columns"] = [
            json.loads(line.strip()[2:].strip())
            for line in columns_match.group(1).splitlines()
        ]
        entries.append(fields)
    return entries


def test_manifest_schema_and_source_contracts() -> None:
    manifest = (TABLEAU / "tableau_data_manifest.yml").read_text()
    assert "version: 1" in manifest
    assert "synthetic_data: true" in manifest
    entries = _manifest_entries()
    assert len(entries) == 9
    for entry in entries:
        path = ROOT / str(entry["file"])
        assert path.is_file()
        frame = pd.read_csv(path)
        assert len(frame) == entry["row_count"]
        assert frame.columns.tolist() == entry["expected_columns"]
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        assert checksum == entry["checksum_sha256"]
        assert frame["data_context"].str.contains("Synthetic", case=False).all()


def test_primary_keys_are_unique_and_non_null() -> None:
    for entry in _manifest_entries():
        frame = pd.read_csv(ROOT / str(entry["file"]), keep_default_na=False)
        key_columns = [part.strip() for part in str(entry["primary_key"]).split("+")]
        assert set(key_columns) <= set(frame.columns)
        assert not frame[key_columns].eq("").any().any()
        assert not frame.duplicated(key_columns).any(), entry["id"]


def test_customer_one_to_one_contract_and_reconciliation() -> None:
    customer = pd.read_csv(TABLEAU / "data/tableau_customer_analytics.csv")
    cohort = pd.read_csv(TABLEAU / "data/tableau_cohort_retention.csv")
    product = pd.read_csv(TABLEAU / "data/tableau_product_profitability.csv")
    expected = json.loads((TABLEAU / "validation/expected_results.json").read_text())
    assert customer["customer_id"].nunique() == expected["total_customers"] == 5000
    assert len(cohort) == expected["cohort_rows"] == 378
    assert len(product) == expected["product_rows"] == 250
    cohort_base = pd.read_csv(ROOT / "data/processed/cohort_base.csv")
    assert expected["cohort_total_customers"] == cohort_base["customer_id"].nunique() == 3220
    segment_expected = {
        key.removeprefix("segment_customers__"): value
        for key, value in expected.items()
        if key.startswith("segment_customers__")
    }
    segment_actual = {
        str(name).lower().replace(" ", "_").replace("-", "_"): int(count)
        for name, count in customer.groupby("segment_name")["customer_id"].nunique().items()
    }
    assert segment_expected == segment_actual
    assert abs(customer["net_revenue"].sum() - expected["total_customer_revenue"]) <= 0.01
    assert abs(product["net_revenue"].sum() - expected["product_revenue"]) <= 0.01
    assert abs(customer["return_adjusted_profit"].sum() - expected["total_customer_profit"]) <= 0.01
    assert abs(product["return_adjusted_profit"].sum() - expected["product_profit"]) <= 0.01


def test_reconciliation_report_is_complete() -> None:
    expected = json.loads((TABLEAU / "validation/expected_results.json").read_text())
    with (TABLEAU / "validation/tableau_reconciliation_report.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert {row["metric"] for row in rows} == set(expected)
    assert all(row["status"] == "PASS_EXPECTED_CONTRACT" for row in rows)


def test_calculation_catalog_completeness() -> None:
    text = (TABLEAU / "calculations/CALCULATED_FIELDS.md").read_text()
    required = {
        "Customer Count",
        "Revenue per Customer",
        "Profit per Customer",
        "Observed Churn Rate",
        "Risk × Value Score",
        "Experiment Absolute Lift",
        "Practical Status",
        "Customer Lifetime Revenue (LOD)",
        "Cohort Size (LOD)",
        "Segment Percent of Total",
        "Product Rank",
        "Retention Period Change",
    }
    assert all(name in text for name in required)
    assert text.count("{ FIXED") >= 7
    assert all(token in text for token in ("RANK_DENSE", "RUNNING_SUM", "LOOKUP", "WINDOW_AVG", "TOTAL"))


def test_workbook_spec_covers_dashboards_story_parameters_and_actions() -> None:
    text = (TABLEAU / "workbook/WORKBOOK_SPEC.md").read_text()
    dashboards = [
        "Executive Overview",
        "Customer Segmentation",
        "Churn & Retention",
        "CLV Analysis",
        "Cohort Retention",
        "Product Profitability",
        "Experiment & Decision Evidence",
    ]
    parameters = ["Metric Selector", "Top N", "Risk Threshold", "Experiment View"]
    actions = [
        "Executive Segment → Customer Segmentation Filter",
        "Executive → Customer Segmentation Navigate",
        "Executive Segment → Churn & Retention Filter",
        "Executive → Churn & Retention Navigate",
        "Segment Highlight",
        "Cohort Heatmap → Retention Curves",
        "Category → Product Detail",
    ]
    assert all(name in text for name in dashboards + parameters + actions)
    assert "Story: Customer Retention Decision Story" in text
    assert text.count("**") >= 14  # seven titled story points


def test_manual_guide_records_final_evidence_and_claim_boundary() -> None:
    text = (TABLEAU / "MANUAL_TABLEAU_BUILD_AND_VALIDATION.md").read_text()
    for check in (
        "TWB opens in Tableau Desktop 2026.1",
        "Customer Retention Decision Story",
        "Tableau closed and TWBX reopened",
        "Canonical genuine screenshots",
        "Governed metric reconciliation",
        "External publication",
    ):
        assert check in text
    assert "8/8 PASS" in text
    assert "27/27 PASS" in text
    assert "not evidenced as separately exercised" in text
    assert "What does generated cohort retention look like?" in text


def test_readme_links_and_status_boundary() -> None:
    text = (TABLEAU / "README.md").read_text()
    links = re.findall(r"\[[^]]+\]\(([^)]+)\)", text)
    for link in links:
        assert (TABLEAU / link).exists(), link
    assert "TABLEAU IMPLEMENTATION COMPLETE" in text
    assert "8/8 genuine Tableau exports are present" in text
    assert "TWBX close/reopen" in text
    assert "PORTABILITY VALIDATION PASSED" in text
    assert "Not separately certified" in text


def test_new_tableau_content_is_publication_safe() -> None:
    paths = list(TABLEAU.rglob("*")) + [
        ROOT / "docs/case_studies/retention_review_case_study.md",
    ]
    text_paths = [path for path in paths if path.is_file() and path.suffix in {".md", ".yml", ".json", ".py"}]
    forbidden = [
        "/Users/" + "darshil/",
        "TO" + "DO",
        "FIX" + "ME",
        "Chat" + "GPT",
        "Co" + "dex",
        "sk-",
        "AKIA",
        "implemented production Tableau",
        "realized retention improvement",
        "real customer churn",
    ]
    for path in text_paths:
        text = path.read_text()
        for token in forbidden:
            assert token not in text, f"{token!r} found in {path.relative_to(ROOT)}"


def test_final_twb_structure() -> None:
    assert TWB.is_file()
    root = ET.parse(TWB).getroot()
    assert root.tag == "workbook"
    assert root.attrib["version"] == "18.1"
    assert root.attrib["original-version"] == "18.1"
    manifest = root.find("./document-format-change-manifest")
    assert manifest is not None
    assert {
        "AnimationOnByDefault",
        "MarkAnimation",
        "SheetIdentifierTracking",
        "WindowsPersistSimpleIdentifiers",
    } <= {child.tag for child in manifest}
    sources = root.findall("./datasources/datasource")
    assert len([source for source in sources if source.get("name") != "Parameters"]) == 9
    connections = root.findall("./datasources/datasource/connection/named-connections/named-connection/connection")
    assert len(connections) == 9
    assert all(connection.get("directory") == "../data" for connection in connections)
    assert all((TABLEAU / "data" / str(connection.get("filename"))).is_file() for connection in connections)
    assert len(root.findall("./worksheets/worksheet")) == 36
    dashboards = root.findall("./dashboards/dashboard")
    assert len([dashboard for dashboard in dashboards if dashboard.get("type") != "storyboard"]) == 7
    assert len(root.findall("./dashboards/dashboard[@type='storyboard']/zones//story-point")) == 7


def test_native_textscan_connections_relations_and_metadata_resolve() -> None:
    root = ET.parse(TWB).getroot()
    valid_types = {"string", "integer", "real", "boolean", "date", "datetime"}
    datasources = [node for node in root.findall("./datasources/datasource") if node.get("name") != "Parameters"]
    assert len(datasources) == 9
    for datasource in datasources:
        connection = datasource.find("./connection")
        assert connection is not None
        child_tags = [child.tag for child in connection]
        assert child_tags[:2] == ["named-connections", "relation"]
        assert child_tags[-1] == "metadata-records"
        assert set(child_tags) <= {"named-connections", "relation", "refresh", "metadata-records"}
        named = connection.find("./named-connections/named-connection")
        relation = connection.find("./relation")
        leaf = named.find("./connection") if named is not None else None
        assert named is not None and relation is not None and leaf is not None
        assert leaf.get("class") == "textscan"
        assert leaf.get("auto-extract") is None
        assert leaf.get("directory") == "../data"
        filename = str(leaf.get("filename"))
        assert (TABLEAU / "data" / filename).is_file()
        relation_name = Path(filename).stem + "#csv"
        assert relation.get("connection") == named.get("name")
        assert str(datasource.get("name")).startswith("federated.p3_")
        assert str(named.get("name")).startswith("textscan.p3_")
        assert relation.get("name") == relation_name
        assert relation.get("table") == f"[{relation_name}]"
        assert connection.find("./metadata-records/metadata-record[@class='capability']") is not None
        assert {column.get("datatype") for column in relation.findall("./columns/column")} <= valid_types


def test_boolean_fields_are_categorical_and_not_numeric_measures() -> None:
    root = ET.parse(TWB).getroot()
    for name in ("statistically_significant", "practically_significant"):
        column = root.find(f".//datasource-dependencies/column[@name='[{name}]']")
        assert column is not None
        assert column.get("datatype") == "boolean"
        assert column.get("role") == "dimension"
        assert column.get("type") == "nominal"
        records = root.findall("./datasources/datasource/connection/metadata-records/metadata-record")
        record = next(node for node in records if node.findtext("./local-name") == f"[{name}]")
        assert record.findtext("./local-type") == "boolean"
        assert record.findtext("./aggregation") == "Count"


def test_worksheet_datasource_and_field_bindings_resolve() -> None:
    root = ET.parse(TWB).getroot()
    source_names = {node.get("name") for node in root.findall("./datasources/datasource")}
    for worksheet in root.findall("./worksheets/worksheet"):
        view = worksheet.find("./table/view")
        assert view is not None
        listed_sources = {node.get("name") for node in view.findall("./datasources/datasource")}
        dependencies = {node.get("datasource"): node for node in view.findall("./datasource-dependencies")}
        assert listed_sources <= source_names
        assert listed_sources == set(dependencies)
        for source_name, dependency in dependencies.items():
            columns = {node.get("name") for node in dependency.findall("./column")}
            instances = {node.get("name"): node.get("column") for node in dependency.findall("./column-instance")}
            assert set(instances.values()) <= columns
            referenced = " ".join(
                filter(None, [view.findtext("../rows"), view.findtext("../cols")])
            )
            referenced += " " + " ".join(
                str(node.get("column")) for node in worksheet.findall(".//*[@column]")
            )
            for ds_name, instance in re.findall(r"\[([^\]]+)\]\.\[(?:[^:\]]*:)?([^\]]+)\]", referenced):
                if ds_name == source_name and instance in instances:
                    assert instances[instance] in columns
    with BINDING_AUDIT_CSV.open() as handle:
        audit = list(csv.DictReader(handle))
    assert {row["worksheet"] for row in audit} == {
        worksheet.get("name") for worksheet in root.findall("./worksheets/worksheet")
    }
    assert all(row["status"] == "RESOLVED" for row in audit)


def test_parameter_dependencies_use_complete_native_column_shape() -> None:
    root = ET.parse(TWB).getroot()
    definitions = {
        column.get("name"): column
        for column in root.findall("./datasources/datasource[@name='Parameters']/column")
    }
    assert len(definitions) == 4
    for definition in definitions.values():
        domain = definition.get("param-domain-type")
        assert domain in {"list", "range"}
        assert definition.find("./members" if domain == "list" else "./range") is not None
    dependencies = root.findall(".//datasource-dependencies[@datasource='Parameters']")
    assert dependencies
    for dependency in dependencies:
        for column in dependency.findall("./column"):
            assert column.find("./calculation") is not None
            assert column.get("name") in definitions
            assert column.get("param-domain-type") == definitions[column.get("name")].get("param-domain-type")


def test_final_workbook_executive_kpi_source_and_cards_are_self_contained() -> None:
    root = ET.parse(TWB).getroot()
    datasource = root.find("./datasources/datasource[@caption='Executive KPI']")
    assert datasource is not None
    leaf = datasource.find("./connection/named-connections/named-connection/connection")
    assert leaf is not None
    assert leaf.get("filename") == "tableau_executive_kpis.csv"
    assert leaf.get("directory") == "../data"
    assert leaf.get("auto-extract") is None
    with (TABLEAU / "data/tableau_executive_kpis.csv").open() as handle:
        csv_fields = next(csv.reader(handle))
    relation_fields = [
        column.get("name") for column in datasource.findall("./connection/relation/columns/column")
    ]
    assert relation_fields == csv_fields
    for sheet_name in (
        "KPI Net Revenue",
        "KPI Return-adjusted Profit",
        "KPI Churn Rate",
        "KPI Predicted CLV",
        "KPI Revenue Leakage",
    ):
        worksheet = root.find(f"./worksheets/worksheet[@name='{sheet_name}']")
        assert worksheet is not None
        dependency = worksheet.find("./table/view/datasource-dependencies")
        assert dependency is not None and dependency.get("datasource") == datasource.get("name")


def test_generator_output_is_deterministic_in_memory() -> None:
    module = runpy.run_path(str(GENERATOR))
    model = module["build_model"]()
    full_a = ET.tostring(module["build_twb"](model).getroot(), encoding="utf-8")
    full_b = ET.tostring(module["build_twb"](model).getroot(), encoding="utf-8")
    assert full_a == full_b


def test_final_executive_dashboard_has_all_required_workbook_zones() -> None:
    root = ET.parse(TWB).getroot()
    dashboard = root.find("./dashboards/dashboard[@name='Executive Overview']")
    assert dashboard is not None
    zone_names = {zone.get("name") for zone in dashboard.findall("./zones//zone[@name]")}
    required = {
        "KPI Total Customers",
        "KPI Net Revenue",
        "KPI Return-adjusted Profit",
        "KPI Churn Rate",
        "KPI Predicted CLV",
        "KPI Revenue Leakage",
        "KPI Experiment Lift",
        "Executive Segment Distribution",
        "Executive CLV Distribution",
        "Executive Product Profitability",
        "Executive Experiment Summary",
    }
    assert required <= zone_names
    worksheet_names = {node.get("name") for node in root.findall("./worksheets/worksheet")}
    assert required <= worksheet_names


def test_executive_kpi_cards_use_governed_values_and_native_formats() -> None:
    root = ET.parse(TWB).getroot()
    direct_cards = {
        "KPI Net Revenue": ("Total Net Revenue", 'c"$"#,##0'),
        "KPI Return-adjusted Profit": ("Total Return-adjusted Profit", 'c"$"#,##0'),
        "KPI Churn Rate": ("Churn Rate", "p0.0%"),
        "KPI Predicted CLV": ("Predicted CLV", 'c"$"#,##0.00'),
        "KPI Revenue Leakage": ("Revenue Leakage from Returns and Discounts", 'c"$"#,##0'),
    }
    for sheet_name, (member, number_format) in direct_cards.items():
        worksheet = root.find(f"./worksheets/worksheet[@name='{sheet_name}']")
        assert worksheet is not None
        datasource = worksheet.find("./table/view/datasources/datasource")
        assert datasource is not None and datasource.get("caption") == "Executive KPI"
        groupfilter = worksheet.find("./table/view/filter/groupfilter")
        assert groupfilter is not None and groupfilter.get("member") == json.dumps(member)
        format_node = worksheet.find("./table/style/style-rule[@element='cell']/format[@attr='text-format']")
        assert format_node is not None and format_node.get("value") == number_format


def test_csv_binding_and_datasource_audits_are_complete() -> None:
    with BINDING_AUDIT_CSV.open() as handle:
        binding_rows = list(csv.DictReader(handle))
    assert list(binding_rows[0]) == [
        "worksheet",
        "datasource",
        "field_reference",
        "field_exists",
        "calculation_exists",
        "parameter_exists",
        "status",
    ]
    assert {row["worksheet"] for row in binding_rows} == {
        node.get("name") for node in ET.parse(TWB).getroot().findall("./worksheets/worksheet")
    }
    assert all(row["status"] == "RESOLVED" for row in binding_rows)
    with DATASOURCE_AUDIT_CSV.open() as handle:
        datasource_rows = list(csv.DictReader(handle))
    assert len(datasource_rows) == 9
    assert all(row["connection_class"] == "textscan" for row in datasource_rows)
    assert all(row["runtime_pattern_source"] == "manually validated final workbook" for row in datasource_rows)
    assert all(row["relative_path"].startswith("../data/") for row in datasource_rows)


def test_final_repair_status_covers_all_36_sheets() -> None:
    with REPAIR_STATUS_CSV.open() as handle:
        statuses = list(csv.DictReader(handle))
    assert len(statuses) == 36
    assert len({row["worksheet"] for row in statuses}) == 36
    assert all(row["status"] != "DEFERRED" for row in statuses)
    assert any(row["status"] == "SIMPLIFIED_FOR_RUNTIME" for row in statuses)


def test_final_worksheets_have_no_active_lod_table_calc_or_parameter_dependency() -> None:
    root = ET.parse(TWB).getroot()
    active_calculations = []
    for worksheet in root.findall("./worksheets/worksheet"):
        assert worksheet.find("./table/view/datasource-dependencies[@datasource='Parameters']") is None
        for column in worksheet.findall("./table/view/datasource-dependencies/column[calculation]"):
            active_calculations.append(str(column.get("caption") or column.get("name")).strip("[]"))
            assert column.find("./calculation/table-calc") is None
            assert "{ FIXED" not in str(column.find("./calculation").get("formula"))
    assert active_calculations == ["Experiment Absolute Lift"]
    with CALCULATION_STATUS_CSV.open() as handle:
        calculation_status = list(csv.DictReader(handle))
    assert len(calculation_status) == 33
    assert sum(row["status"] == "USED" for row in calculation_status) == 1
    assert sum(row["status"] == "DEFERRED" for row in calculation_status) == 1


def test_previously_blank_executive_view_is_direct_field_only() -> None:
    root = ET.parse(TWB).getroot()
    worksheet = root.find("./worksheets/worksheet[@name='Executive CLV Distribution']")
    assert worksheet is not None
    dependency = worksheet.find("./table/view/datasource-dependencies")
    assert dependency is not None and dependency.get("datasource") == "federated.p3_customer_analytics"
    assert not dependency.findall("./column[calculation]")
    assert {column.get("name") for column in dependency.findall("./column")} == {
        "[segment_name]",
        "[predicted_12m_clv]",
    }
    assert worksheet.find("./table/cols").text == "[federated.p3_customer_analytics].[avg:predicted_12m_clv:qk]"
    assert worksheet.find("./table/rows").text == "[federated.p3_customer_analytics].[none:segment_name:nk]"


def test_final_generator_has_no_development_workbook_outputs() -> None:
    module = runpy.run_path(str(GENERATOR))
    assert module["TWB_PATH"] == TWB
    source = GENERATOR.read_text()
    obsolete_tokens = [
        "wrong" + "_sales",
        "failed" + "_pass",
        "pre" + "_pass",
        "pre" + "_bulk",
        "executive_overview" + "_candidate",
        "tableau_2026_1" + "_reference",
    ]
    assert all(token not in source for token in obsolete_tokens)


def test_generated_twb_uses_tableau_native_sheet_dashboard_story_and_window_shapes() -> None:
    root = ET.parse(TWB).getroot()
    assert [child.tag for child in root][:7] == [
        "document-format-change-manifest",
        "preferences",
        "datasources",
        "actions",
        "worksheets",
        "dashboards",
        "windows",
    ]
    assert set(child.tag for child in root[7:]) <= {"thumbnails"}
    assert root.find("./actions/nav-action") is None
    assert root.find("./explain-data") is None
    worksheets = root.findall("./worksheets/worksheet")
    assert all([child.tag for child in worksheet][-2:] == ["table", "simple-id"] for worksheet in worksheets)
    assert not root.findall("./worksheets/worksheet/worksheet-number")
    zones = root.findall("./dashboards/dashboard/zones//zone")
    assert zones
    assert all(zone.get("id") is not None for zone in zones)
    assert all(zone.get("number") is None for zone in zones)
    typed_zones = [zone for zone in zones if zone.get("name") is None]
    assert all(zone.get("type-v2") is not None for zone in typed_zones)
    story = root.find("./dashboards/dashboard[@type='storyboard']")
    assert story is not None
    nav = story.find("./zones//zone[@type-v2='flipboard-nav']")
    flipboard = story.find("./zones//zone[@type-v2='flipboard']")
    assert nav is not None and flipboard is not None
    assert nav.get("paired-zone-id") == flipboard.get("id")
    assert flipboard.get("paired-zone-id") == nav.get("id")
    windows = root.findall("./windows/window")
    assert len(windows) == 44  # 36 worksheets + 7 dashboards + 1 Story
    assert all(window.find("./simple-id") is not None for window in windows)
    assert all(
        window.find("./cards") is not None
        for window in windows
        if window.get("class") == "worksheet"
    )


def test_final_twb_calculations_parameters_actions_and_safety() -> None:
    root = ET.parse(TWB).getroot()
    calculation_captions = {
        column.get("caption") or str(column.get("name")).strip("[]")
        for column in root.findall("./datasources/datasource/column[calculation]")
        if column.get("name") not in {f"[{name}]" for name in ("Metric Selector", "Top N", "Risk Threshold", "Experiment View")}
    }
    required_calculations = {
        "Customer Count",
        "CLV Band (Display)",
        "Customer Lifetime Revenue (LOD)",
        "Segment Revenue Share (LOD)",
        "Cohort Retention %",
        "Product Rank",
        "Experiment Absolute Lift",
    }
    assert required_calculations <= calculation_captions
    parameters = {column.get("caption") for column in root.findall("./datasources/datasource[@name='Parameters']/column")}
    assert parameters == {"Metric Selector", "Top N", "Risk Threshold", "Experiment View"}
    actions = {node.get("caption") for node in root.findall("./actions/action")}
    assert actions == {
        "Executive Segment → Customer Segmentation Filter",
        "Executive Segment → Churn & Retention Filter",
        "Segment Highlight",
        "Cohort Heatmap → Retention Curves",
        "Category → Product Detail",
    }
    text = TWB.read_text()
    forbidden = [
        "tableau" + ".com",
        "pass" + "word=",
        "user" + "name=",
        "<nav-action",
        "<explain-data",
        "TO" + "DO",
        "FIX" + "ME",
        "Chat" + "GPT",
        "Co" + "dex",
        "Clau" + "de",
    ]
    assert all(token not in text for token in forbidden)
    connection_dirs = {
        node.get("directory")
        for node in root.findall("./datasources/datasource/connection/named-connections/named-connection/connection")
    }
    assert connection_dirs == {"../data"}


def test_packaged_workbook_is_complete_and_portable() -> None:
    assert TWBX.is_file()
    expected_entries = {"Customer_Intelligence_Product_Analytics.twb"} | {
        f"Data/data/{entry['file'].split('/')[-1]}" for entry in _manifest_entries()
    }
    forbidden = (
        b"/Users/" + b"darshil/",
        b"file:///Users/" + b"darshil/",
        b"/var/" + b"folders/",
        b"Tableau" + b"Temp",
    )
    with zipfile.ZipFile(TWBX) as package:
        assert package.testzip() is None
        assert set(package.namelist()) == expected_entries
        payloads = {name: package.read(name) for name in package.namelist()}
    assert all(token not in payload for payload in payloads.values() for token in forbidden)
    packaged_root = ET.fromstring(payloads["Customer_Intelligence_Product_Analytics.twb"])
    packaged_dirs = {
        node.get("directory")
        for node in packaged_root.findall("./datasources/datasource/connection/named-connections/named-connection/connection")
    }
    assert packaged_dirs == {"Data/data"}
    packaged_sources = packaged_root.findall("./datasources/datasource")
    assert len([source for source in packaged_sources if source.get("name") != "Parameters"]) == 9
    assert len(packaged_root.findall("./worksheets/worksheet")) == 36
    packaged_dashboards = packaged_root.findall("./dashboards/dashboard")
    assert len([dashboard for dashboard in packaged_dashboards if dashboard.get("type") != "storyboard"]) == 7
    assert len(packaged_root.findall("./dashboards/dashboard[@type='storyboard']/zones//story-point")) == 7
    assert len(packaged_root.findall("./datasources/datasource[@name='Parameters']/column")) == 4
    assert len(packaged_root.findall("./actions/action")) == 5


def test_canonical_tableau_screenshot_evidence_is_complete_and_unique() -> None:
    pngs = {path.name for path in SCREENSHOT_DIR.glob("*.png")}
    assert pngs == SCREENSHOT_FILES
    hashes: set[str] = set()
    for filename in sorted(SCREENSHOT_FILES):
        path = SCREENSHOT_DIR / filename
        assert path.stat().st_size > 100_000
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.width >= 2_000
            assert image.height >= 1_100
            image.verify()
        hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    assert len(hashes) == len(SCREENSHOT_FILES)
