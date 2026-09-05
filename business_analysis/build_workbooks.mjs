import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = fileURLToPath(new URL("../", import.meta.url)).replace(/\/$/, "");

const reqs = [
  ["CR-001","Retention Manager","Which valuable groups have elevated churn risk?","data/marts/mart_churn_risk.csv","customer_id, churn_risk_tier, expected_profit_at_risk","Join governed churn, CLV and segment marts","Churn Rate; CLV at Risk","retention_action_center.csv","Executive Customer Strategy","Risk, value, count, period and source are visible","UAT-003","data/exports/retention_action_center.csv"],
  ["CR-002","Data Analyst","Which factors are associated with churn?","data/processed/customer_features.csv","recency_days, orders, return_rate, discount_dependency","Standardized multivariable driver analysis","Driver Strength","churn_driver_analysis.csv","Statistical Analysis Report","Method, strength and non-causal limitation are traceable","UAT-007","data/exports/churn_driver_analysis.csv"],
  ["CR-003","Finance Business Partner","What value is exposed in high-risk populations?","data/marts/mart_churn_risk.csv + mart_clv.csv","customer_id, expected_profit_at_risk, predicted_12m_clv","Governed join and aggregation","Revenue / CLV at Risk","retention_economics_scenarios.csv","Executive Customer Strategy","Historical inputs reconcile and scenarios are labeled","UAT-015","data/exports/customer_intelligence_reconciliation.csv"],
  ["CR-004","Product Manager","Is an experiment statistically and practically meaningful?","data/exports/ab_test_customer_assignments.csv","variant, converted","Two-proportion test plus practical threshold","Absolute Lift; p-value; Effect Size","experiment_evaluation.csv","Experiment Readout","Both significance conclusions and thresholds appear","UAT-010","reports/experiments/synthetic_retention_offer_v1_readout.md"],
  ["CR-005","Customer Strategy Manager","Which valuable segments deteriorated?","data/processed/transactions_enriched.csv","customer_id, order_date, net_revenue, return_adjusted_profit","Historical-cutoff RFM versus current RFM","Segment Migration Count","customer_segment_migration.csv","Executive Customer Strategy","Prior/current transition and value/risk changes exist","UAT-008","data/exports/segment_migration_summary.csv"],
  ["CR-006","Data Analyst","Did assignment match the planned split?","data/exports/ab_test_customer_assignments.csv","variant","Chi-square sample-ratio-mismatch test","SRM p-value","experiment_srm_validation.csv","Experiment Readout","Expected/actual counts and validity warning appear","UAT-011","data/exports/experiment_srm_validation.csv"],
  ["CR-007","Product Manager","Is the experiment lifecycle traceable?","experimentation/experiment_registry.yml","experiment_id and design fields","Registry to evaluation/readout/decision mapping","Experiment Decision","decision_log.csv","Experiment Readout","Experiment ID matches across artifacts","UAT-009","experimentation/decision_log.csv"],
  ["CR-008","Finance Business Partner","How do retention assumptions change economics?","data/marts/mart_churn_risk.csv + mart_clv.csv","risk tier, value, profit","Five explicit scenario calculations","Net Benefit; ROI","retention_economics_scenarios.csv","Executive Customer Strategy","Assumptions and estimate limitations are explicit","UAT-016","data/exports/retention_economics_scenarios.csv"],
  ["CR-009","Retention Manager","What should be reviewed first?","governed analytical outputs","risk, CLV, drivers, migration, experiment","Deterministic priority rules","Priority Score","retention_action_center.csv","Action Center","Evidence and NEEDS_REVIEW status are present","UAT-017","data/exports/retention_action_center.csv"],
  ["CR-010","BI Developer","Can BI consume stable decision outputs?","data/exports","generated CSV schemas","Machine-readable export generation","Output Availability","migration/economics/action/alerts","Power BI-ready exports","Required columns and files exist","UAT-018","data/exports/customer_intelligence_alerts.csv"],
  ["CR-011","Data Analyst","Do Python and R experiment results agree?","experiment_evaluation.csv + r_experiment_validation.csv","N, rates, lift, CI, p-value, significance","Tolerance reconciliation","Reconciliation Status","python_r_statistical_reconciliation.csv","Statistical Methodology","All defined checks pass","UAT-012","data/exports/python_r_statistical_reconciliation.csv"],
  ["CR-012","Customer Success Manager","Can recommendations remain advisory?","retention_action_center.csv","recommended_review, review_status","Governance rule enforcement","Review Status","retention_action_center.csv","Action Center","No communication or external write action exists","UAT-019","governance/ai_data_policy.md"],
  ["CR-013","BI Developer","Do source and output populations reconcile?","processed/marts/exports","customer_id and aggregate values","Cross-layer comparison with tolerances","Reconciliation Status","customer_intelligence_reconciliation.csv","Automation Report","All checks expose source, output and difference","UAT-020","data/exports/customer_intelligence_reconciliation.csv"],
  ["CR-014","Customer Strategy Manager","Are material shifts and invalidity visible?","migration, SRM, validation outputs","metric values and statuses","Explainable threshold rules","Alert Status","customer_intelligence_alerts.csv","Automation Report","Alert includes type, value, threshold and interpretation","UAT-021","data/exports/customer_intelligence_alerts.csv"],
  ["CR-015","Data Analyst","Is there a trusted AI evidence source?","governed aggregate outputs","approved aggregate fields","Deterministic JSON assembly","Packet Schema","latest_customer_insight_packet.json","AI Governance","Required keys exist with no NaN/Infinity or IDs","UAT-022","artifacts/customer_intelligence/latest_customer_insight_packet.json"],
  ["CR-016","Customer Strategy Manager","Can governed evidence be explained safely?","latest_customer_insight_packet.json","aggregate evidence only","Structured provider response","AI Eval Pass Rate","ai_evaluation_results.csv","AI Copilot","Schema and guardrail evaluations pass","UAT-023","data/exports/ai_evaluation_results.csv"],
  ["CR-017","Data Analyst","Can AI be reviewed without credentials?","ai/copilot.py","provider interface","Fake and disabled provider modes","Local Availability","fake/disabled modes","AI Governance","Both modes work without external calls","UAT-024","tests/test_ai_copilot.py"],
  ["CR-018","BI Developer","Can the lifecycle run with one command?","Makefile + existing pipeline","customer-intelligence target","Reuse and stage orchestration","Stage Pass Rate","customer_intelligence_run_manifest.csv","Automation Report","Stages record status/runtime and outputs regenerate","UAT-025","data/audit/customer_intelligence_run_manifest.csv"],
];

const uat = [
  ["UAT-001","CR-001","Customer 360","Verify one unique customer row and governed KPI fields","Existing processed feature refresh","Unique customer IDs and required measures","","NOT RUN","data/processed/customer_features.csv","Await automated suite"],
  ["UAT-002","CR-001","Churn","Reconcile churn population to Customer 360","Churn mart generated","Counts match with zero tolerance","","NOT RUN","data/exports/customer_intelligence_reconciliation.csv","Await workflow"],
  ["UAT-003","CR-001","Churn","Verify risk, value, count and recommendation in action center","Decision-support run","Required fields are non-null and review-only","","NOT RUN","data/exports/retention_action_center.csv","Await workflow"],
  ["UAT-004","CR-003","CLV","Verify modeled CLV is available and finite","CLV mart generated","All values are finite and clearly modeled","","NOT RUN","data/marts/mart_clv.csv","Await automated suite"],
  ["UAT-005","CR-005","RFM","Verify recency/frequency/monetary scoring","RFM mart generated","Scores and segment names meet governed rules","","NOT RUN","data/marts/mart_rfm_segments.csv","Await automated suite"],
  ["UAT-006","CR-005","Segmentation","Reconcile segment customer counts","Segment mart generated","Counts sum to unique customer population","","NOT RUN","data/exports/segment_kpi_comparison.csv","Await workflow"],
  ["UAT-007","CR-002","Drivers","Verify association wording and evidence","Analysis run","Top drivers include method, strength, p-value and non-causal limitation","","NOT RUN","data/exports/churn_driver_analysis.csv","Await tests"],
  ["UAT-008","CR-005","Migration","Verify prior/current transitions and summaries","Migration run","Detail and summary counts reconcile; no invalid values","","NOT RUN","data/exports/segment_migration_summary.csv","Await tests"],
  ["UAT-009","CR-007","Experiment Registry","Trace experiment ID across lifecycle artifacts","Experiment run","Registry, evaluation, readout and log IDs match","","NOT RUN","experimentation/experiment_registry.yml","Await tests"],
  ["UAT-010","CR-004","Experiment","Verify deterministic effect and significance output","Assignments generated","Lift, CI, p-value, effect size and both significance statuses exist","","NOT RUN","data/exports/experiment_evaluation.csv","Await tests"],
  ["UAT-011","CR-006","SRM","Verify planned versus actual split test","Experiment evaluated","Chi-square and p-value yield explicit validity status","","NOT RUN","data/exports/experiment_srm_validation.csv","Await tests"],
  ["UAT-012","CR-011","Python/R","Verify all reconciliation metrics","R 4.6.1 available","Every defined tolerance check passes","","NOT RUN","data/exports/python_r_statistical_reconciliation.csv","Await R run"],
  ["UAT-013","CR-004","Readout","Verify complete deterministic experiment readout","Experiment/analysis run","All required lifecycle sections and exact result values exist","","NOT RUN","reports/experiments/synthetic_retention_offer_v1_readout.md","Await workflow"],
  ["UAT-014","CR-007","Decision Log","Verify decision rationale and review status","Experiment run","Statistical, practical, risk and limitation evidence are traceable","","NOT RUN","experimentation/decision_log.csv","Await workflow"],
  ["UAT-015","CR-003","Economics","Reconcile at-risk CLV input","Churn and CLV marts generated","Scenario input matches governed source within tolerance","","NOT RUN","data/exports/customer_intelligence_reconciliation.csv","Await workflow"],
  ["UAT-016","CR-008","Scenarios","Verify five scenario calculations and labels","Economics run","Five named scenarios, assumptions, outputs and limitations exist","","NOT RUN","data/exports/retention_economics_scenarios.csv","Await tests"],
  ["UAT-017","CR-009","Action Center","Verify deterministic priorities","Decision-support run","Priority follows governed rules and status is NEEDS_REVIEW","","NOT RUN","data/exports/retention_action_center.csv","Await tests"],
  ["UAT-018","CR-010","BI Outputs","Verify machine-readable schemas","Workflow completed","Required decision-support CSVs exist with stable columns","","NOT RUN","data/exports/","Await workflow"],
  ["UAT-019","CR-012","Governance","Verify no execution/write-back capability","Source review complete","Recommendations are advisory; no communication/CRM write","","NOT RUN","governance/ai_data_policy.md","Await code review"],
  ["UAT-020","CR-013","Reconciliation","Verify cross-layer counts and values","Workflow completed","Every reconciliation check passes","","NOT RUN","data/exports/customer_intelligence_reconciliation.csv","Await workflow"],
  ["UAT-021","CR-014","Alerts","Verify threshold evidence","Workflow completed","Each alert has status, value, threshold and interpretation","","NOT RUN","data/exports/customer_intelligence_alerts.csv","Await workflow"],
  ["UAT-022","CR-015","Insight Packet","Validate packet schema and finiteness","Decision-support run","Required aggregate keys exist; no identifiers/NaN/Infinity","","NOT RUN","artifacts/customer_intelligence/latest_customer_insight_packet.json","Await tests"],
  ["UAT-023","CR-016","AI Copilot","Run numeric, statistical, SRM, hallucination, causality, quality and privacy evals","Insight packet exists","All deterministic fake-provider evaluations pass","","NOT RUN","data/exports/ai_evaluation_results.csv","Await eval suite"],
  ["UAT-024","CR-017","AI Local Modes","Verify fake and disabled providers without credentials","No OpenAI credentials required","Both modes return valid structured responses","","NOT RUN","tests/test_ai_copilot.py","Await pytest"],
  ["UAT-025","CR-018","Automation","Run make customer-intelligence","Raw synthetic data available","All feasible stages complete and manifest records results","","NOT RUN","data/audit/customer_intelligence_run_manifest.csv","Await end-to-end run"],
];

function decorate(sheet, title, headers, rows, widths) {
  sheet.showGridLines = false;
  const cols = headers.length;
  sheet.getRangeByIndexes(0, 0, 1, cols).merge();
  sheet.getCell(0, 0).values = [[title]];
  sheet.getRangeByIndexes(0, 0, 1, cols).format = { fill: "#17365D", font: { color: "#FFFFFF", bold: true, size: 16 }, rowHeight: 28 };
  sheet.getRangeByIndexes(1, 0, 1, cols).values = [headers];
  sheet.getRangeByIndexes(1, 0, 1, cols).format = { fill: "#D9EAF7", font: { color: "#17365D", bold: true }, wrapText: true, borders: { preset: "all", style: "thin", color: "#B4C7DC" } };
  sheet.getRangeByIndexes(2, 0, rows.length, cols).values = rows;
  sheet.getRangeByIndexes(2, 0, rows.length, cols).format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: "#D9D9D9" } };
  for (let i = 0; i < widths.length; i++) sheet.getRangeByIndexes(0, i, rows.length + 2, 1).format.columnWidth = widths[i];
  sheet.getRangeByIndexes(2, 0, rows.length, cols).format.rowHeight = 54;
  sheet.freezePanes.freezeRows(2);
  sheet.tables.add(sheet.getRangeByIndexes(1, 0, rows.length + 1, cols), true, `${sheet.name.replace(/\W/g, "")}Table`);
}

async function buildRtm() {
  const wb = Workbook.create();
  const sheet = wb.worksheets.add("Traceability Matrix");
  const headers = ["Requirement ID","Persona","Business Question","Source","Source Field","Transformation / Analysis","KPI","Analytical Output","Dashboard / Report","Acceptance Criteria","UAT Case","Evidence","Status"];
  let statuses = new Map();
  try {
    const execution = JSON.parse(await fs.readFile(`${ROOT}/docs/evidence/uat_execution_results.json`, "utf8"));
    statuses = new Map(execution.map(row => [row.uat_id, row.status]));
  } catch {}
  decorate(sheet, "P3 Customer Intelligence — Requirements Traceability Matrix", headers, reqs.map(r => [...r, statuses.get(r[10]) === "PASS" ? "IMPLEMENTED / AUTOMATED UAT PASS" : "IMPLEMENTED / VALIDATION PENDING"]), [14,20,30,30,28,32,20,28,25,38,12,34,22]);
  const out = await SpreadsheetFile.exportXlsx(wb);
  await out.save(`${ROOT}/business_analysis/requirements_traceability_matrix.xlsx`);
  const preview = await wb.render({ sheetName: "Traceability Matrix", autoCrop: "all", scale: 0.65, format: "png" });
  await fs.writeFile(`${ROOT}/business_analysis/requirements_traceability_matrix_preview.png`, new Uint8Array(await preview.arrayBuffer()));
  const inspection = await wb.inspect({ kind: "sheet,table,formula", maxChars: 5000, tableMaxRows: 4, tableMaxCols: 6 });
  await fs.writeFile(`${ROOT}/business_analysis/requirements_traceability_matrix_inspect.txt`, inspection.ndjson ?? String(inspection));
}

async function buildUat() {
  const wb = Workbook.create();
  const plan = wb.worksheets.add("UAT Plan");
  let uatRows = uat;
  try {
    const execution = JSON.parse(await fs.readFile(`${ROOT}/docs/evidence/uat_execution_results.json`, "utf8"));
    const byId = new Map(execution.map(row => [row.uat_id, row]));
    uatRows = uat.map(row => {
      const result = byId.get(row[0]);
      return result ? [...row.slice(0, 6), result.actual_result, result.status, row[8], "Automated local validation; see cited evidence"] : row;
    });
  } catch {}
  decorate(plan, "P3 Customer Intelligence — UAT Test Plan", ["UAT ID","Requirement ID","Area","Scenario","Precondition","Expected Result","Actual Result","Status","Evidence","Notes"], uatRows, [12,14,18,34,28,38,30,14,38,24]);
  plan.getRange(`H3:H${uat.length + 2}`).dataValidation = { rule: { type: "list", values: ["NOT RUN","PASS","FAIL","BLOCKED"] } };
  const summary = wb.worksheets.add("Execution Summary");
  summary.showGridLines = false;
  summary.getRange("A1:D1").merge(); summary.getRange("A1").values = [["UAT Execution Summary"]];
  summary.getRange("A1:D1").format = { fill: "#17365D", font: { color: "#FFFFFF", bold: true, size: 16 }, rowHeight: 28 };
  summary.getRange("A3:D3").values = [["Status","Case Count","Share","Interpretation"]];
  summary.getRange("A3:D3").format = { fill: "#D9EAF7", font: { bold: true, color: "#17365D" }, borders: { preset: "all", style: "thin", color: "#B4C7DC" } };
  summary.getRange("A4:A7").values = [["PASS"],["FAIL"],["BLOCKED"],["NOT RUN"]];
  summary.getRange("B4").formulas = [[`=COUNTIF('UAT Plan'!$H$3:$H$${uat.length + 2},A4)`]]; summary.getRange("B4:B7").fillDown();
  summary.getRange("C4").formulas = [[`=B4/COUNTA('UAT Plan'!$A$3:$A$${uat.length + 2})`]]; summary.getRange("C4:C7").fillDown();
  summary.getRange("C4:C7").setNumberFormat("0.0%");
  summary.getRange("D4:D7").values = [["Validated with cited evidence"],["Expected result not met"],["Cannot execute until precondition is met"],["No execution claim made"]];
  summary.getRange("A4:D7").format = { borders: { preset: "all", style: "thin", color: "#D9D9D9" }, wrapText: true };
  summary.getRange("A10:D11").merge(); summary.getRange("A10").values = [[uatRows.some(row => row[7] === "PASS") ? "Statuses were populated from executed automated local validation evidence. PASS is not inferred from documentation alone." : "Initial artifact status is NOT RUN. Actual Result and Status may be updated only after executing the cited behavior; do not infer PASS from documentation alone."]];
  summary.getRange("A10:D11").format = { fill: "#FFF2CC", font: { color: "#7F6000" }, wrapText: true };
  [16,16,14,48].forEach((w, i) => summary.getRangeByIndexes(0, i, 12, 1).format.columnWidth = w);
  const out = await SpreadsheetFile.exportXlsx(wb);
  await out.save(`${ROOT}/business_analysis/uat_test_plan.xlsx`);
  for (const name of ["UAT Plan", "Execution Summary"]) {
    const preview = await wb.render({ sheetName: name, autoCrop: "all", scale: 0.7, format: "png" });
    await fs.writeFile(`${ROOT}/business_analysis/uat_test_plan_${name.replace(/\s/g, "_").toLowerCase()}_preview.png`, new Uint8Array(await preview.arrayBuffer()));
  }
  const inspection = await wb.inspect({ kind: "sheet,table,formula", maxChars: 7000, tableMaxRows: 4, tableMaxCols: 6 });
  await fs.writeFile(`${ROOT}/business_analysis/uat_test_plan_inspect.txt`, inspection.ndjson ?? String(inspection));
}

await fs.mkdir(`${ROOT}/business_analysis`, { recursive: true });
await buildRtm();
await buildUat();
