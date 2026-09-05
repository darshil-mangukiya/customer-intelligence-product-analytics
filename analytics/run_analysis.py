from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from analytics.customer_driver_analysis import churn_driver_analysis, clv_driver_analysis
from analytics.statistical_analysis import (
    ALPHA,
    chi_square_test,
    correlation_test,
    descriptive_summary,
    fit_explanatory_ols,
    holm_adjusted_p_values,
    minimum_detectable_effect,
    two_proportion_test,
    welch_mean_test,
)
from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


def _strength(value: float, thresholds: tuple[float, float] = (0.2, 0.5)) -> str:
    value = abs(value)
    return "small" if value < thresholds[0] else "moderate" if value < thresholds[1] else "large"


def _row(question_id: str, question: str, hypothesis: str, population: str, metric: str, result, interpretation: str, action: str, kpi: str, limitations: str, observed_a: float | None = None, observed_b: float | None = None) -> dict[str, object]:
    significant = result.p_value < ALPHA
    return {
        "analysis_id": question_id,
        "business_question": question,
        "hypothesis": hypothesis,
        "population_sample": population,
        "metric": metric,
        "statistical_method": result.method,
        "assumptions": "Independent observations; representative synthetic generation; method-specific distribution/count assumptions checked.",
        "group_a_value": observed_a,
        "group_b_value": observed_b,
        "sample_size_a": result.n_a,
        "sample_size_b": result.n_b,
        "statistic": result.statistic,
        "p_value": result.p_value,
        "alpha": ALPHA,
        "statistically_significant": significant,
        "confidence_interval_low": result.ci_low,
        "confidence_interval_high": result.ci_high,
        "effect_size": result.effect_size,
        "effect_size_name": result.effect_size_name,
        "effect_magnitude": _strength(result.effect_size),
        "statistical_interpretation": f"The null hypothesis is {'rejected' if significant else 'not rejected'} at alpha={ALPHA:.2f}; effect magnitude is {_strength(result.effect_size)}.",
        "business_interpretation": interpretation,
        "recommended_action": action,
        "kpi_to_monitor": kpi,
        "limitations": (limitations + (f" {result.warning}" if result.warning else "")).strip(),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def evaluate_experiment(assignments: pd.DataFrame, practical_threshold: float = 0.02) -> pd.DataFrame:
    if not {"variant", "converted"}.issubset(assignments):
        raise KeyError("experiment assignments require variant and converted")
    variants = set(assignments["variant"].dropna())
    if variants != {"Control", "Retention Offer"}:
        raise ValueError("experiment must contain exactly Control and Retention Offer")
    control = assignments.loc[assignments["variant"].eq("Control"), "converted"].astype(int)
    treatment = assignments.loc[assignments["variant"].eq("Retention Offer"), "converted"].astype(int)
    result = two_proportion_test(int(control.sum()), len(control), int(treatment.sum()), len(treatment))
    base, treated = float(control.mean()), float(treatment.mean())
    lift = (treated-base)/base if base else np.nan
    mde = minimum_detectable_effect(len(control), len(treatment), base)
    statistically_significant = result.p_value < ALPHA
    practically_significant = abs(result.effect_size) >= practical_threshold
    if statistically_significant and practically_significant:
        decision = "Targeted rollout candidate with a continuing holdout"
    elif statistically_significant:
        decision = "Statistically detectable but below the practical threshold; do not scale broadly"
    else:
        decision = "Inconclusive; continue or redesign before rollout"
    return pd.DataFrame([{
        "experiment_id": "synthetic_retention_offer_v1", "control_label": "Control", "treatment_label": "Retention Offer",
        "control_n": len(control), "treatment_n": len(treatment), "control_conversions": int(control.sum()), "treatment_conversions": int(treatment.sum()),
        "baseline_rate": base, "treatment_rate": treated, "absolute_difference": result.effect_size, "relative_lift": lift,
        "confidence_interval_low": result.ci_low, "confidence_interval_high": result.ci_high, "z_statistic": result.statistic, "p_value": result.p_value,
        "alpha": ALPHA, "statistically_significant": statistically_significant, "practical_threshold": practical_threshold, "practically_significant": practically_significant,
        "effect_size": result.effect_size, "effect_size_name": result.effect_size_name, "minimum_detectable_effect_80pct_power": mde,
        "power_interpretation": "Observed absolute lift exceeds the approximate MDE." if abs(result.effect_size) >= mde else "The design may be underpowered for an effect this small.",
        "decision": decision, "recommendation": decision, "data_provenance": "Deterministic synthetic assignment and outcomes; no real customer experiment occurred.",
        "limitations": "Results apply to the generated experiment population.", "generated_at": datetime.now(UTC).isoformat(),
    }])


def run_analysis(project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    customers = pd.read_csv(project_config.processed_dir / "customer_features.csv")
    transactions = pd.read_csv(project_config.processed_dir / "transactions_enriched.csv", usecols=["category", "return_flag"])
    segments = pd.read_csv(project_config.mart_dir / "mart_customer_segments.csv", usecols=["customer_id", "segment_name"])
    clv = pd.read_csv(project_config.mart_dir / "mart_clv.csv", usecols=["customer_id", "predicted_12m_clv"])
    assignments = pd.read_csv(project_config.export_dir / "ab_test_customer_assignments.csv")
    analysis = customers.merge(segments, on="customer_id", how="left").merge(clv, on="customer_id", how="left")
    descriptive = descriptive_summary(
        analysis,
        ["orders", "historical_clv", "predicted_12m_clv", "engagement_score", "repeat_purchase_flag", "return_rate"],
        group_by="churn_label",
    )

    rows: list[dict[str, object]] = []
    median_discount = analysis["discount_dependency"].median()
    low = analysis.loc[analysis["discount_dependency"].le(median_discount), "repeat_purchase_flag"]
    high = analysis.loc[analysis["discount_dependency"].gt(median_discount), "repeat_purchase_flag"]
    result = two_proportion_test(int(low.sum()), len(low), int(high.sum()), len(high))
    rows.append(_row("Q01", "Does higher discount exposure correspond to different repeat-purchase behavior?", "Repeat-purchase rates are equal above and below median discount dependency.", "Synthetic customers split at median discount dependency", "repeat-purchase rate", result, "Higher-discount and lower-discount customers show an observed repeat-rate difference; the effect size determines whether it is decision-relevant.", "Test discount policy with randomized holdouts before changing targeting.", "repeat-purchase rate", "Median split loses information and the observational comparison is not causal.", low.mean(), high.mean()))

    table = pd.crosstab(analysis["segment_name"], analysis["churn_label"])
    result = chi_square_test(table)
    rows.append(_row("Q02", "Is churn status associated with customer segment?", "Customer segment and churn status are independent.", "Synthetic customers assigned to behavioral segments", "churn status", result, "Segment membership contains a churn-risk association signal, but does not itself cause churn.", "Prioritize segment-specific diagnostics and controlled retention tests.", "churn rate by segment", "Segments are model-derived and the chi-square result does not isolate individual drivers."))

    result = correlation_test(analysis["engagement_score"], analysis["predicted_12m_clv"], "spearman")
    rows.append(_row("Q03", "Is engagement meaningfully related to predicted CLV?", "Engagement score and predicted CLV have no monotonic association.", "Synthetic customers with engagement and CLV scores", "engagement score vs predicted CLV", result, "The rank relationship quantifies whether more engaged customers tend to have higher modeled value.", "Use engagement as a prioritization signal, then validate incremental value in an experiment.", "predicted CLV and engagement rate", "Predicted CLV is modeled and correlation is not causation."))

    table = pd.crosstab(transactions["category"], transactions["return_flag"])
    result = chi_square_test(table)
    rows.append(_row("Q04", "Do return outcomes differ across product categories?", "Product category and return flag are independent.", "Synthetic enriched order lines", "return flag", result, "Category is associated with return behavior to the degree indicated by Cramer's V.", "Investigate high-return categories for fit, quality, and expectation gaps.", "return rate by category", "Order-line observations from the same customer may not be fully independent."))

    table = pd.crosstab(analysis["acquisition_channel"], analysis["churn_label"])
    result = chi_square_test(table)
    rows.append(_row("Q05", "Do acquisition channels produce different retention outcomes?", "Acquisition channel and churn status are independent.", "Synthetic acquired customers", "retention/churn status", result, "Acquisition mix is associated with downstream retention, conditional on the synthetic design.", "Compare channel quality on retained CLV, not acquisition volume alone.", "retention rate by acquisition channel", "Channel selection is observational and may reflect customer mix."))

    threshold = analysis["predicted_12m_clv"].quantile(0.75)
    rest = analysis.loc[analysis["predicted_12m_clv"].lt(threshold), "orders"]
    high_value = analysis.loc[analysis["predicted_12m_clv"].ge(threshold), "orders"]
    result = welch_mean_test(rest, high_value)
    rows.append(_row("Q06", "Do high-value customers purchase more frequently?", "Mean order count is equal for top-quartile CLV and other customers.", "Synthetic customers split at the 75th percentile of predicted CLV", "order count", result, "Top-quartile modeled-value customers show a measurable difference in order frequency.", "Design loyalty journeys around repeat behavior while preserving margin.", "orders per customer and CLV", "CLV and orders are mechanically related, so this is descriptive rather than independent validation.", rest.mean(), high_value.mean()))

    result = correlation_test(analysis["return_rate"], analysis["historical_clv"], "spearman")
    rows.append(_row("Q07", "Is return behavior associated with historical customer value?", "Return rate and historical CLV have no monotonic association.", "Synthetic customers", "return rate vs historical CLV", result, "The rank association indicates whether returns co-move with realized customer value.", "Use return-aware value metrics and review avoidable return patterns.", "return-adjusted CLV and return rate", "Bivariate association may be confounded by order volume and category mix."))

    tests = pd.DataFrame(rows)
    tests["holm_adjusted_p_value"] = holm_adjusted_p_values(tests["p_value"])
    tests["significant_after_holm"] = tests["holm_adjusted_p_value"].lt(ALPHA)
    experiment = evaluate_experiment(assignments)
    churn_drivers = churn_driver_analysis(customers)
    clv_drivers = clv_driver_analysis(customers)
    predictors = ["orders", "avg_order_value", "engagement_score", "recency_days", "return_rate", "discount_dependency", "sessions", "support_cases", "customer_age_days"]
    regression, diagnostics = fit_explanatory_ols(analysis, "predicted_12m_clv", predictors)
    regression["model_target"] = "log1p(predicted_12m_clv)"
    regression["interpretation"] = regression.apply(lambda r: f"A one-standard-deviation increase in {r['predictor']} is associated with a {r['standardized_coefficient']:.3f} change in log modeled CLV, holding other numeric predictors constant.", axis=1)
    regression["limitations"] = "Explanatory association using synthetic, observational features; coefficients are not causal."
    for name, value in diagnostics.items():
        regression[f"model_{name}"] = value

    generated_at = datetime.now(UTC).isoformat()
    for frame in [churn_drivers, clv_drivers, regression]:
        frame["generated_at"] = generated_at

    for frame in [tests, experiment, churn_drivers, clv_drivers, regression]:
        frame.replace([np.inf, -np.inf], np.nan, inplace=True)
    outputs = {"descriptive_statistics": descriptive, "statistical_test_results": tests, "experiment_evaluation": experiment, "churn_driver_analysis": churn_drivers, "clv_driver_analysis": clv_drivers, "regression_analysis": regression}
    for name, frame in outputs.items():
        write_csv(frame, project_config.export_dir / f"{name}.csv")
    _write_reports(outputs, project_config)
    return outputs


def _fmt(value: object, percent: bool = False) -> str:
    try:
        number = float(value)
        if not np.isfinite(number):
            return "not applicable"
        return f"{number:.2%}" if percent else f"{number:.4f}"
    except (TypeError, ValueError):
        return str(value)


def _write_reports(outputs: dict[str, pd.DataFrame], project_config: ProjectConfig) -> None:
    tests, experiment = outputs["statistical_test_results"], outputs["experiment_evaluation"].iloc[0]
    descriptive = outputs["descriptive_statistics"]
    regression, churn, clv = outputs["regression_analysis"], outputs["churn_driver_analysis"], outputs["clv_driver_analysis"]
    technical = ["# Statistical Analysis Report", "", "## 1. Objective", "Evaluate customer and product questions with formal tests, uncertainty, effect sizes, and business interpretation.", "", "## 2. Dataset / Population", "Deterministic synthetic customer, transaction, segment, churn, CLV, cohort, product, and experiment outputs. No real customers or live experiment are represented.", "", "### Descriptive snapshot by churn status", "| Churn Label | Metric | N | Mean | Median | Standard Deviation | 25th Percentile | 75th Percentile |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in descriptive.to_dict("records"):
        technical.append(f"| {row['group']} | {row['metric']} | {row['sample_size']:,} | {_fmt(row['mean'])} | {_fmt(row['median'])} | {_fmt(row['standard_deviation'])} | {_fmt(row['quantile_25'])} | {_fmt(row['quantile_75'])} |")
    technical.extend(["", "## 3. Methodology", f"Two-sided tests use alpha={ALPHA:.2f}. Analyses report 95% confidence intervals and effect sizes. The seven planned questions use Holm family-wise error adjustment; raw p-values are interpreted with adjusted results, effect magnitude, and business context.", "", "## 4. Analytical Questions"])
    for row in tests.to_dict("records"):
        technical.extend(["", f"### {row['analysis_id']}: {row['business_question']}", f"- Hypothesis: {row['hypothesis']}", f"- Population / sample: {row['population_sample']}", f"- Metric and method: {row['metric']}; {row['statistical_method']}", f"- Result: statistic {_fmt(row['statistic'])}; raw p-value {_fmt(row['p_value'])}; Holm-adjusted p-value {_fmt(row['holm_adjusted_p_value'])}; 95% CI [{_fmt(row['confidence_interval_low'])}, {_fmt(row['confidence_interval_high'])}]", f"- Effect size: {_fmt(row['effect_size'])} ({row['effect_size_name']}, {row['effect_magnitude']})", f"- Statistical interpretation: {row['statistical_interpretation']} Holm-adjusted significance: {row['significant_after_holm']}.", f"- Business interpretation: {row['business_interpretation']}", f"- Recommended action: {row['recommended_action']}", f"- KPI to monitor: {row['kpi_to_monitor']}", f"- Assumptions: {row['assumptions']}", f"- Limitations: {row['limitations']}"])
    technical.extend(["", "## 5. Statistical Tests", "Welch tests address unequal variances; two-proportion z-tests compare binary rates; Pearson chi-square tests assess categorical association.", "", "## 6. Confidence Intervals", "Intervals quantify estimation uncertainty. An interval that excludes zero supports a detectable difference, but not necessarily a useful one.", "", "## 7. Effect Sizes", "Cohen's d, risk difference, Cramer's V, and correlation coefficients communicate practical magnitude.", "", "## 8. Correlation Findings"])
    for row in tests.loc[tests["statistical_method"].str.contains("correlation")].to_dict("records"):
        technical.append(f"- {row['business_question']} Effect={_fmt(row['effect_size'])}; {row['business_interpretation']}")
    technical.extend(["", "## 9. Regression Findings", f"The robust-uncertainty OLS model explains adjusted R-squared {_fmt(regression['model_adjusted_r_squared'].iloc[0])}. It models log predicted CLV for interpretation, not causal attribution."])
    for row in regression.head(6).to_dict("records"):
        technical.append(f"- {row['predictor']}: standardized coefficient {_fmt(row['standardized_coefficient'])}, p={_fmt(row['p_value'])}, 95% CI [{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}].")
    technical.extend(["", "## 10. Experiment Analysis", f"Control {_fmt(experiment['baseline_rate'], True)} vs treatment {_fmt(experiment['treatment_rate'], True)}; absolute lift {_fmt(experiment['absolute_difference'], True)}, relative lift {_fmt(experiment['relative_lift'], True)}, 95% CI [{_fmt(experiment['confidence_interval_low'], True)}, {_fmt(experiment['confidence_interval_high'], True)}], p={_fmt(experiment['p_value'])}.", f"Decision: {experiment['decision']}", "", "## 11. Customer Driver Findings", "Churn rankings use standardized multivariable logistic coefficients plus group effect sizes. CLV rankings use Spearman association; neither method establishes causality.", f"- Leading churn-associated signals: {', '.join(churn.head(5)['metric_or_driver'])}.", f"- Leading CLV-associated signals: {', '.join(clv.head(5)['metric_or_driver'])}.", "", "## 12. Business Interpretation", "Results prioritize where to investigate and experiment; statistical detection is kept separate from operational value.", "", "## 13. Recommendations", "Use segment holdouts, monitor repeat purchase and return-adjusted CLV, and revisit sample-size assumptions before rollout.", "", "## 14. Assumptions", "Independent observations are approximated; numeric tests require finite, non-constant values; chi-square expected counts are checked.", "", "## 15. Limitations", "All data and experiment outcomes are synthetic. Associations, model importance, and regression coefficients are not causal and require real-world validation.", "", "## 16. Reproducibility Information", "Run `make analytics`. Synthetic generation and assignment use deterministic seed 42 / stable hashes; generated timestamps are audit metadata."])
    write_markdown(technical, project_config.report_dir / "statistical_analysis_report.md")

    strongest = tests.sort_values("effect_size", key=lambda s: s.abs(), ascending=False).iloc[0]
    executive = [
        "# Executive Customer Strategy Brief", "", "## Executive Summary",
        f"Seven planned analyses and one retention experiment were evaluated. The largest standardized effect was **{strongest['business_question']}** ({strongest['effect_size_name']}={_fmt(strongest['effect_size'])}).",
        "", "## Risk Signals",
        f"The highest-ranked churn-associated signals are {', '.join(churn.head(3)['metric_or_driver'])}. Rank High/Critical risk customers by expected profit at risk and review these signals before selecting an intervention.",
        "", "## Customer Value",
        f"The strongest CLV-associated behaviors are {', '.join(clv.head(3)['metric_or_driver'])}. Loyalty and repeat-purchase tests should retain return-adjusted margin guardrails.",
        "", "## Experiment Results",
        f"The experiment estimated absolute lift of {_fmt(experiment['absolute_difference'], True)} (95% CI {_fmt(experiment['confidence_interval_low'], True)} to {_fmt(experiment['confidence_interval_high'], True)}; p={_fmt(experiment['p_value'])}). Statistical significance: {experiment['statistically_significant']}; practical significance at a 2-point threshold: {experiment['practically_significant']}. Recommendation: {experiment['recommendation']}.",
        "", "## Recommended Actions",
        "| Priority | Customer Group | Observed Signal | Evidence | Recommended Action | Expected KPI | Limitation |",
        "|---:|---|---|---|---|---|---|",
        f"| 1 | High/Critical risk | Leading driver: {churn.iloc[0]['metric_or_driver']} | Standardized logistic association | Diagnose and test a targeted intervention with holdout | Churn rate | Association, not causation |",
        f"| 2 | High modeled CLV | Leading value signal: {clv.iloc[0]['metric_or_driver']} | Spearman rho {_fmt(clv.iloc[0]['effect_size'])} | Design loyalty test with margin guardrail | Return-adjusted CLV | Modeled value |",
        f"| 3 | Experiment-eligible risk pool | Treatment-control difference | 95% CI and p-value reported above | {experiment['recommendation']} | Conversion and profit proxy | Generated experiment population |",
        "", "## KPIs to Monitor",
        "Churn rate; retention rate; repeat-purchase rate; predicted and historical CLV; engagement rate; return rate; experiment conversion; return-adjusted profit proxy.",
        "", "## Analytical Limits",
        "Results apply to the generated project dataset. Observational associations are not causal, and scenario economics are estimates. External use requires representative data and prospective validation.",
    ]
    write_markdown(executive, project_config.report_dir / "executive_customer_strategy.md")


def main() -> None:
    run_analysis()


if __name__ == "__main__":
    main()
