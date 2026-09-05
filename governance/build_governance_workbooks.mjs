import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const navy="#17324D", blue="#246B9A", pale="#EAF2F8", grid="#D7E0E8";
const preview="governance/.workbook_previews";
function col(i){let s="";for(let n=i+1;n>0;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s}
function sheet(wb,name,title,note,headers,rows,table){const s=wb.worksheets.add(name),last=col(headers.length-1);s.showGridLines=false;s.getRange(`A1:${last}1`).merge();s.getRange("A1").values=[[title]];s.getRange(`A1:${last}1`).format={fill:navy,font:{color:"#FFFFFF",bold:true,size:18},rowHeight:30};s.getRange(`A2:${last}2`).merge();s.getRange("A2").values=[[note]];s.getRange(`A2:${last}2`).format={fill:pale,font:{color:navy,italic:true},wrapText:true,rowHeight:32};s.getRange(`A4:${last}4`).values=[headers];s.getRange(`A4:${last}4`).format={fill:blue,font:{color:"#FFFFFF",bold:true},wrapText:true,rowHeight:32,borders:{preset:"all",style:"thin",color:grid}};s.getRange(`A5:${last}${rows.length+4}`).values=rows;s.getRange(`A5:${last}${rows.length+4}`).format={wrapText:true,verticalAlignment:"top",rowHeight:68,borders:{preset:"all",style:"thin",color:grid}};s.tables.add(`A4:${last}${rows.length+4}`,true,table);s.freezePanes.freezeRows(4);s.freezePanes.freezeColumns(2);s.getRange(`A4:${last}${rows.length+4}`).format.autofitColumns();for(let i=0;i<headers.length;i++)s.getRange(`${col(i)}:${col(i)}`).format.columnWidth=headers[i].match(/Definition|Rule|Lineage|Limitation|Use|Formula/)?30:18;return s}

const fields=[
["customer_id","Synthetic customer identifier","STRING",false,"data/raw/customers.csv","dim_customer","Pseudonymous/Synthetic","Analytics Engineering","Not null and unique","Used only in governed local joins; never exposed by AI"],
["signup_date","Synthetic customer signup date","DATE",false,"customers.csv","customer_features","Internal","Analytics Engineering","Valid date; not future-dated","Defines monitoring time slices"],
["orders","Distinct customer orders","INTEGER",false,"transactions.csv","customer_features","Internal","Analytics Engineering",">= 0","Customer behavior feature"],
["net_revenue","Revenue after discounts and returns","DECIMAL",false,"transactions.csv","fact_orders/customer_features","Internal","Finance Analytics","Finite; reconciled to order facts","Synthetic financial measure"],
["return_adjusted_profit","Profit after modeled return loss","DECIMAL",false,"transactions.csv + products.csv","fact_orders","Internal","Finance Analytics","Finite; reconciliation","Synthetic economics"],
["recency_days","Days from analysis date to last order","INTEGER",true,"transactions.csv","customer_features","Internal","Customer Analytics",">= 0 when order exists","High-impact churn feature"],
["engagement_score","Composite synthetic engagement measure","DECIMAL",true,"web_behavior.csv + engagement.csv","customer_features","Internal","Product Analytics","Finite and bounded by source rules","Association only"],
["churn_label","Synthetic inactive-status outcome","BOOLEAN",false,"customer_features","churn_model_base","Restricted synthetic","Data Science","Boolean; class distribution monitored","Not a real customer outcome"],
["churn_probability","Logistic-regression probability","DECIMAL",false,"churn_model_base","mart_churn_risk","Restricted synthetic","Data Science","0..1; calibration and drift checks","Prioritization; not automated action"],
["predicted_12m_clv","Modeled twelve-month customer value","DECIMAL",false,"customer_features","mart_clv","Restricted synthetic","Data Science","Finite; distribution monitoring","Estimate, not realized value"],
["segment_name","Governed KMeans strategy label","STRING",false,"customer_features","mart_customer_segments","Restricted synthetic","Customer Strategy","Allowed segment names; stability validation","Descriptive segmentation"],
["absolute_difference","Treatment minus control conversion lift","DECIMAL",false,"ab_test_customer_assignments.csv","experiment_evaluation","Internal","Experimentation","Python/R tolerance reconciliation","Synthetic randomized experiment"],
["p_value","Two-proportion hypothesis-test p-value","DECIMAL",false,"experiment assignments","experiment_evaluation","Internal","Experimentation","0..1; Python/R reconciliation","Copied into AI packet; never LLM-calculated"],
];
const kpis=[
["Customer count","Distinct customers","COUNT DISTINCT customer_id","dim_customer","Customer analytics","Synthetic population"],
["Churn rate","Share with churn label","SUM(churn_label) / COUNT(customer_id)","mart_churn_risk","Retention strategy","Synthetic modeled label"],
["High/Critical risk customers","Count in governed high tiers","COUNT WHERE churn_risk_tier IN (High,Critical)","mart_churn_risk","Human review queue","Threshold-sensitive"],
["Predicted 12m CLV","Sum of modeled value","SUM(predicted_12m_clv)","mart_clv","Value prioritization","Estimate only"],
["Experiment absolute lift","Treatment minus control","treatment_rate - control_rate","experiment_evaluation","Experiment decision","Synthetic experiment"],
["Experiment relative lift","Absolute lift over control","absolute_lift / control_rate","experiment_evaluation","Experiment interpretation","Zero-safe denominator"],
["Forecast MAE","Mean absolute backtest error","MEAN(ABS(prediction-actual))","forecast_backtest_results","Model comparison","Short synthetic history"],
];
const models=[
["churn_logistic_regression","Binary classification","customer_features","churn_probability / tier","ROC-AUC; PR-AUC; Brier; ranking; calibration","Data Science","Held-out synthetic evaluation; not causal"],
["customer_segmentation_kmeans","Unsupervised clustering","customer_features","cluster and strategy segment","Silhouette; Davies-Bouldin; ARI; balance","Customer Strategy","K=5 chosen for interpretability, not claimed optimum"],
["clv_regression","Regression","customer_features","predicted_12m_clv","MAE/RMSE/R2 and drift","Data Science","Modeled synthetic value"],
["linear_seasonal_forecast","Time series regression","fact_orders","monthly forecast","Walk-forward MAE/RMSE/MAPE/sMAPE/bias/coverage","Finance Analytics","Residual intervals; short history"],
];
const ownership=[
["Synthetic raw customer sources","Analytics Engineering","Data Engineering","Restricted synthetic","Local project retention","Source contract validation"],
["Customer models and registry","Data Science","ML Engineering","Restricted synthetic","Versioned artifact retention","Validation, hashes, drift"],
["Experiment evidence","Experimentation Lead","Analytics Engineering","Internal synthetic","Audit evidence retention","SRM and Python/R reconciliation"],
["Customer insight packet and AI logs","Customer Strategy","AI/Analytics Engineering","Aggregate synthetic","Sanitized metadata retention","Schema, numeric fidelity, no prompts/secrets"],
];
const dictionarySources=[
["Customer master","data/raw/customers.csv","customer_id","Synthetic customer identifier","CSV string identifier","STRING","No","customer","Primary key","Restricted synthetic","On demand","Not null and unique"],
["Orders","data/raw/transactions.csv","order_id","Synthetic order identifier","CSV string identifier","STRING","No","order line","Primary key","Internal synthetic","On demand","Not null and unique"],
["Products","data/raw/products.csv","product_id","Synthetic product identifier","CSV string identifier","STRING","No","product","Primary key","Internal synthetic","On demand","Referential integrity"],
["Web behavior","data/raw/web_behavior.csv","session_id","Synthetic session identifier","CSV string identifier","STRING","No","session","Primary key","Restricted synthetic","On demand","Not null and unique"],
["Engagement","data/raw/engagement.csv","customer_id","Synthetic campaign interaction customer key","CSV join key","STRING","No","interaction","Foreign key","Restricted synthetic","On demand","Customer reference integrity"],
["Experiments","data/exports/ab_test_customer_assignments.csv","experiment_group","Governed synthetic assignment","Control/treatment label","STRING","No","customer assignment","Composite key","Internal synthetic","Experiment refresh","Allowed labels and SRM"],
];
const experimentMetrics=[
["Control N","Customers assigned to control","COUNT(control rows)","experiment_evaluation.csv","Experimentation","Positive integer","Experiment readout"],
["Treatment N","Customers assigned to treatment","COUNT(treatment rows)","experiment_evaluation.csv","Experimentation","Positive integer","Experiment readout"],
["Conversion rate","Converted customers over assigned customers","conversions / N","experiment_evaluation.csv","Experimentation","0..1","Readout and AI packet"],
["Absolute Lift","Treatment rate minus control rate","treatment_rate - control_rate","experiment_evaluation.csv","Experimentation","-1..1","Decision log"],
["Relative Lift","Absolute lift divided by control rate","absolute_lift / control_rate","experiment_evaluation.csv","Experimentation","Finite where baseline > 0","Decision log"],
["Confidence Interval","95% interval for treatment-control difference","pooled standard error interval","experiment_evaluation.csv","Experimentation","Lower <= estimate <= upper","Python/R reconciliation"],
["p-value","Two-sided two-proportion z-test p-value","2 * normal tail probability","experiment_evaluation.csv","Experimentation","0..1","Python/R reconciliation"],
["Effect Size","Cohen h difference in proportions","2asin(sqrt(pt))-2asin(sqrt(pc))","experiment_evaluation.csv","Experimentation","Finite","Experiment readout"],
["MDE","Detectable absolute effect at 80% modeled power","Normal approximation","experiment_evaluation.csv","Experimentation",">=0","Experiment planning"],
["Power","Modeled design target","80% target recorded with MDE","experiment registry","Experimentation","0..1","Experiment planning"],
["SRM","Chi-square assignment-balance check","Observed vs expected allocation","experiment_srm_validation.csv","Experimentation","PASS/FAIL","Validity gate"],
];
const aiFields=[
["customer_kpis","data/exports/kpi_summary.csv","Aggregate explanation","Aggregate synthetic","Warn when quality/freshness flags exist"],
["churn_summary","data/marts/mart_churn_risk.csv","Aggregate risk explanation","Aggregate restricted synthetic","Packet refresh"],
["experiment_results","data/exports/experiment_evaluation.csv","Copy deterministic statistical values only","Internal synthetic","Experiment refresh and SRM gate"],
["python_r_reconciliation","data/exports/python_r_statistical_reconciliation.csv","Report reconciliation status","Internal synthetic","Must be PASS for validated claims"],
["retention_scenarios","data/exports/retention_economics_scenarios.csv","Explain modeled scenarios","Internal synthetic","Always label estimates"],
["data_quality_warnings","data/exports/validation_results.csv","Surface warnings without suppression","Internal","Every workflow run"],
];
const featureRows=fields.filter(r=>["orders","net_revenue","recency_days","engagement_score","churn_label"].includes(r[0])).map(r=>[r[0],r[1],r[1],"churn model",r[4],"Customer-level aggregation",r[2],r[0]==="churn_label"?"0 or 1":">=0 or source-domain range",r[3]?"Median imputation in applicable validation":"Required",r[0]==="churn_label"?"Class mix monitored":"PSI/KS and missingness thresholds"]);
const wb=Workbook.create();
sheet(wb,"Sources","P3 Customer Intelligence Dictionary — Sources","Observed local schemas only; all customer and experiment records are synthetic.",["Source Domain","Table/File","Field","Business Definition","Technical Definition","Data Type","Nullable","Grain","Key","Sensitivity","Refresh","Quality Rule"],dictionarySources,"SourcesTable");
sheet(wb,"Customer 360","P3 Customer Intelligence Dictionary — Customer 360","Governed customer-level attributes and model outputs.",["Field","Business Definition","Data Type","Nullable","Source","Governed Output","Classification","Owner","Validation Rule","Known Limitation"],fields.filter(r=>!["absolute_difference","p_value"].includes(r[0])),"Customer360Table");
sheet(wb,"Experiment Metrics","P3 Customer Intelligence Dictionary — Experiment Metrics","Deterministic statistical definitions; values are never calculated by the LLM.",["Metric","Definition","Formula","Source","Owner / Persona","Expected Range","Reporting Output"],experimentMetrics,"ExperimentMetricsTable");
sheet(wb,"Business KPIs","P3 Customer Intelligence Dictionary — Business KPIs","Formulas point to deterministic project outputs.",["KPI","Definition","Formula","Source of Truth","Decision Use","Known Limitation"],kpis,"BusinessKPITable");
sheet(wb,"AI Evidence Fields","P3 Customer Intelligence Dictionary — AI Evidence","Aggregate governed evidence and allowed explanatory use.",["Evidence ID","Metric Source","Allowed AI Use","Privacy Classification","Staleness Rule"],aiFields,"AIEvidenceTable");
sheet(wb,"Model Features","P3 Customer Intelligence Dictionary — Model Features","Features actually used by the governed churn workflow.",["Feature","Business Meaning","Technical Meaning","Model","Source","Transformation","Data Type","Expected Range","Missing-Value Rule","Drift Rule"],featureRows,"ModelFeaturesTable");

const sources=[
["Customer master","Customer Analytics","CSV","customer","customer_id","On demand","5,000 synthetic rows","customer_id, signup_date, acquisition_channel, region_id","Restricted synthetic","Complete in executed sample","Generated with analysis snapshot","Low: governed generator","Low: tested domains","Customer 360 and model features","features, dimensions, marts","Source presence and contract checks"],
["Products","Merchandising Analytics","CSV","product","product_id","On demand","250 synthetic rows","product_id, category, base_price, margin_rate","Internal synthetic","Complete in executed sample","Generated with analysis snapshot","Low","Low","Product and profitability context","orders and product marts","Key/domain validation"],
["Orders","Finance Analytics","CSV","order line","order_id","On demand","25,037 synthetic rows","order_id, customer_id, product_id, order_date, revenue","Restricted synthetic","Complete in executed sample","Generated with analysis snapshot","Medium: multi-key joins","Medium: financial reconciliation","Customer behavior and economics","facts, features, CLV, forecasts","Keys, dates, reconciliation, anomaly checks"],
["Web behavior","Product Analytics","CSV","session","session_id","On demand","18,018 synthetic rows","session_id, customer_id, session_date, page_views","Restricted synthetic","Complete in executed sample","Generated with analysis snapshot","Medium: event schema","Medium: session outliers","Engagement features","customer features and churn","Contract/type/outlier checks"],
["Engagement","Lifecycle Analytics","CSV","customer campaign summary","customer_id","On demand","5,000 synthetic rows","customer_id, email_opens, clicks, campaign_interactions","Restricted synthetic","Complete in executed sample","Generated with analysis snapshot","Low","Medium: modeled interactions","Engagement features","customer features and churn","Customer reference and finite values"],
["Support activity","Customer Operations","CSV","support case","case_id","On demand","700 synthetic rows","case_id, customer_id, case_date, resolution_hours","Restricted synthetic","Complete in executed sample","Generated with analysis snapshot","Low","Medium: sparse cases","Support behavior features","customer features and monitoring","Key/date/range validation"],
["Experiment assignments","Experimentation","CSV","customer assignment","customer_id + experiment_id","Experiment refresh","5,000 synthetic assignments","customer_id, experiment_group, converted","Internal synthetic","Complete in executed sample","Generated per experiment run","Medium: assignment schema","High: SRM/outcome validity","A/B test inference","readout, decision log, AI packet","SRM, statistical checks, Python/R reconciliation"],
["KPI and reference metadata","Analytics Governance","Markdown/CSV/YAML","metric or registry record","metric/experiment ID","Release controlled","Repository-scale metadata","definition, formula, owner, source, status","Internal","Required governed definitions present","Repository revision","Medium: manual schema change","Medium: definition drift","Metric and evidence governance","reports, API, AI packet","Link, registry, reconciliation and repo checks"],
];
const controls=[
["Source availability","Required synthetic files exist and are non-empty","Workflow source_data_validation","Every run","Analytics Engineering"],
["Schema and quality","Column, key, range, reconciliation, anomaly checks","validation_results.csv","Every run","Data Engineering"],
["Model validity","Held-out, ranking, calibration, explainability, stability, drift","model reports and registry","Release and refresh","Data Science"],
["Experiment integrity","SRM, CI, p-value, practical threshold, Python/R tolerance","experiment and reconciliation outputs","Every experiment refresh","Experimentation"],
["AI governance","Aggregate-only evidence, strict response schema, safety/fidelity evals","AI evals and sanitized log","Every AI change","AI Governance"],
];
const swb=Workbook.create();
sheet(swb,"Source Assessment","P3 Source-System Assessment","Observed sample counts are synthetic portfolio volume, never production scale.",["Source","Owner Persona","Format","Grain","Primary Key","Refresh","Approx Volume","Required Fields","Sensitivity","Completeness","Freshness","Schema Risk","Quality Risk","Analytical Use","Downstream Dependency","Validation / Evidence"],sources,"SourceAssessmentTable");
sheet(swb,"Control Matrix","P3 Source Control Matrix","Controls are local portfolio evidence, not production certification.",["Control Area","Requirement","Evidence","Frequency","Owner"],controls,"ControlMatrixTable");

await fs.mkdir(preview,{recursive:true});
for(const [book,names,prefix] of [[wb,["Sources","Customer 360","Experiment Metrics","Business KPIs","AI Evidence Fields","Model Features"],"dictionary"],[swb,["Source Assessment","Control Matrix"],"sources"]])for(const name of names){const b=await book.render({sheetName:name,autoCrop:"all",scale:.8,format:"png"});await fs.writeFile(`${preview}/${prefix}_${name.replaceAll(" ","_")}.png`,new Uint8Array(await b.arrayBuffer()))}
for(const [book,label] of [[wb,"dictionary"],[swb,"sources"]]){const errors=await book.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},maxChars:3000});console.log(label,errors.ndjson??String(errors))}
await (await SpreadsheetFile.exportXlsx(wb)).save("governance/customer_intelligence_data_dictionary.xlsx");
await (await SpreadsheetFile.exportXlsx(swb)).save("business_analysis/data_source_assessment.xlsx");
console.log(JSON.stringify({dictionary_sheets:6,source_assessment_sheets:2,field_rows:fields.length,kpi_rows:kpis.length}));
