from __future__ import annotations

import math
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from churn_model.train_churn_model import CHURN_FEATURES
from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv, write_markdown


@dataclass(frozen=True)
class ChurnValidationResult:
    metrics: pd.DataFrame
    ranking: pd.DataFrame
    thresholds: pd.DataFrame
    calibration_bins: pd.DataFrame
    calibration_comparison: pd.DataFrame
    global_explainability: pd.DataFrame
    local_explainability: pd.DataFrame


def classification_metrics(y_true: pd.Series, probability: np.ndarray, threshold: float = 0.5) -> dict[str, float | int]:
    y = pd.Series(y_true).astype(int).to_numpy()
    probability = np.asarray(probability, dtype=float)
    if len(y) != len(probability) or len(y) == 0:
        raise ValueError("non-empty y_true and probability with equal length are required")
    if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
        raise ValueError("probabilities must be finite and between 0 and 1")
    predicted = (probability >= threshold).astype(int)
    two_classes = np.unique(y).size == 2
    return {
        "roc_auc": float(roc_auc_score(y, probability)) if two_classes else math.nan,
        "pr_auc": float(average_precision_score(y, probability)) if y.sum() else math.nan,
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "accuracy": float(accuracy_score(y, predicted)),
        "log_loss": float(log_loss(y, probability, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y, probability)),
        "threshold": threshold,
        "test_rows": int(len(y)),
        "positive_rate": float(y.mean()),
    }


def ranking_metrics(y_true: pd.Series, probability: np.ndarray, fractions: tuple[float, ...] = (0.05, 0.10, 0.20)) -> pd.DataFrame:
    frame = pd.DataFrame({"actual": pd.Series(y_true).astype(int).to_numpy(), "probability": probability}).sort_values("probability", ascending=False)
    total_positives = int(frame["actual"].sum())
    base_rate = float(frame["actual"].mean()) if len(frame) else 0.0
    rows = []
    for fraction in fractions:
        selected_n = max(1, math.ceil(len(frame) * fraction))
        selected = frame.head(selected_n)
        captured = int(selected["actual"].sum())
        precision = captured / selected_n
        recall = captured / total_positives if total_positives else 0.0
        rows.append({
            "population_fraction": fraction, "customers_selected": selected_n,
            "actual_churners_captured": captured, "recall_at_k": recall,
            "precision_at_k": precision, "lift_at_k": precision / base_rate if base_rate else 0.0,
        })
    return pd.DataFrame(rows)


def threshold_analysis(
    y_true: pd.Series,
    probability: np.ndarray,
    customer_value: pd.Series,
    thresholds: list[float],
    capacity_share: float = 0.20,
) -> pd.DataFrame:
    y = pd.Series(y_true).astype(int).to_numpy()
    p = np.asarray(probability, dtype=float)
    value = pd.to_numeric(customer_value, errors="coerce").fillna(0).clip(lower=0).to_numpy()
    rows = []
    for threshold in sorted(set(round(float(item), 6) for item in thresholds)):
        pred = (p >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        selected = pred.astype(bool)
        rows.append({
            "threshold": threshold, "selected_customers": int(selected.sum()), "selected_customer_share": float(selected.mean()),
            "precision": float(precision_score(y, pred, zero_division=0)), "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)), "true_positives": int(tp), "true_negatives": int(tn),
            "false_positives": int(fp), "false_negatives": int(fn),
            "selected_value_exposure": float(value[selected].sum()),
            "actual_churner_value_captured": float(value[selected & (y == 1)].sum()),
            "capacity_gap": abs(float(selected.mean()) - capacity_share),
            "modeled_false_positive_cost": float(fp * 6.0),
            "modeled_false_negative_value": float(value[(~selected) & (y == 1)].sum()),
        })
    output = pd.DataFrame(rows)
    output["recommended_under_modeled_capacity"] = False
    eligible = output.loc[output["selected_customers"].gt(0) & output["capacity_gap"].le(0.05)]
    if not eligible.empty:
        recommended_index = eligible.sort_values(["capacity_gap", "recall", "precision"], ascending=[True, False, False]).index[0]
        output.loc[recommended_index, "recommended_under_modeled_capacity"] = True
    return output


def calibration_bins(y_true: pd.Series, probability: np.ndarray, method: str, bins: int = 10) -> pd.DataFrame:
    frame = pd.DataFrame({"actual": pd.Series(y_true).astype(int).to_numpy(), "probability": probability})
    edges = np.linspace(0, 1, bins + 1)
    frame["bin"] = pd.cut(frame["probability"], edges, include_lowest=True, duplicates="drop")
    output = frame.groupby("bin", observed=False).agg(
        customers=("actual", "size"), mean_predicted_probability=("probability", "mean"), observed_churn_rate=("actual", "mean")
    ).reset_index()
    output = output.loc[output["customers"].gt(0)].reset_index(drop=True)
    output["method"] = method
    output["absolute_calibration_error"] = (output["mean_predicted_probability"] - output["observed_churn_rate"]).abs()
    output["weighted_calibration_error"] = output["absolute_calibration_error"] * output["customers"] / len(frame)
    output["probability_bin"] = output["bin"].astype(str)
    return output.drop(columns="bin")


def _linear_contributions(model, X: pd.DataFrame, customer_ids: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    scaler = model.named_steps["scaler"]
    classifier = model.named_steps["model"]
    scaled = scaler.transform(X)
    background = scaled.mean(axis=0)
    coefficient = classifier.coef_[0]
    contributions = (scaled - background) * coefficient
    base_log_odds = float(classifier.intercept_[0] + np.dot(background, coefficient))
    global_output = pd.DataFrame({
        "feature": CHURN_FEATURES,
        "mean_absolute_log_odds_contribution": np.abs(contributions).mean(axis=0),
        "mean_signed_log_odds_contribution": contributions.mean(axis=0),
        "coefficient": coefficient,
    }).sort_values("mean_absolute_log_odds_contribution", ascending=False)
    global_output["direction_context"] = np.where(global_output["coefficient"].ge(0), "Higher standardized values increase predicted log-odds", "Higher standardized values reduce predicted log-odds")
    probability = model.predict_proba(X)[:, 1]
    chosen = sorted(set([int(np.argmin(probability)), int(np.argsort(probability)[len(probability) // 2]), int(np.argmax(probability))]))
    rows = []
    for example_number, index in enumerate(chosen, start=1):
        final_log_odds = base_log_odds + float(contributions[index].sum())
        reconstructed_probability = 1 / (1 + math.exp(-final_log_odds))
        order = np.argsort(np.abs(contributions[index]))[::-1][:8]
        for rank, feature_index in enumerate(order, start=1):
            value = float(contributions[index, feature_index])
            rows.append({
                "example_id": f"SYNTHETIC_EXAMPLE_{example_number}", "synthetic_customer_id": str(customer_ids.iloc[index]),
                "feature": CHURN_FEATURES[feature_index], "feature_value": float(X.iloc[index, feature_index]),
                "log_odds_contribution": value, "contribution_direction": "higher predicted risk" if value > 0 else "lower predicted risk",
                "contribution_rank": rank, "base_log_odds": base_log_odds, "final_log_odds": final_log_odds,
                "model_probability": float(probability[index]), "reconstructed_probability": reconstructed_probability,
                "absolute_reconciliation_error": abs(float(probability[index]) - reconstructed_probability),
            })
    return global_output, pd.DataFrame(rows)


def run_churn_validation(project_config: ProjectConfig = CONFIG) -> ChurnValidationResult:
    base = pd.read_csv(project_config.processed_dir / "churn_model_base.csv")
    customer = pd.read_csv(project_config.processed_dir / "customer_features.csv", usecols=["customer_id", "historical_clv", "net_revenue"])
    X = base[CHURN_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = base["churn_label"].astype(int)
    X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(
        X, y, base["customer_id"], test_size=0.25, random_state=42, stratify=y
    )
    model = joblib.load(project_config.model_dir / "churn_model.joblib")
    raw_probability = model.predict_proba(X_test)[:, 1]
    raw_metrics = classification_metrics(y_test, raw_probability)
    metrics = pd.DataFrame([{"model": "current_logistic_regression", "probability_type": "raw", **raw_metrics}])
    matrix = confusion_matrix(y_test, raw_probability >= 0.5, labels=[0, 1])
    confusion = pd.DataFrame(matrix, index=["actual_retained", "actual_churned"], columns=["predicted_retained", "predicted_churned"]).reset_index(names="actual_class")
    ranking = ranking_metrics(y_test, raw_probability)

    quantile_thresholds = [float(np.quantile(raw_probability, q)) for q in (0.80, 0.90, 0.95)]
    test_value = id_test.to_frame().merge(customer, on="customer_id", how="left")["historical_clv"]
    thresholds = threshold_analysis(y_test, raw_probability, test_value, [0.30, 0.40, 0.50, 0.60, 0.70, *quantile_thresholds])

    calibration_rows = []
    calibration_bins_frames = [calibration_bins(y_test, raw_probability, "raw")]
    candidates = {"raw": raw_probability}
    for method in ("sigmoid", "isotonic"):
        calibrated_model = CalibratedClassifierCV(estimator=clone(model), method=method, cv=5)
        calibrated_model.fit(X_train, y_train)
        candidates[method] = calibrated_model.predict_proba(X_test)[:, 1]
    raw_auc = float(raw_metrics["roc_auc"])
    for method, probability in candidates.items():
        brier = float(brier_score_loss(y_test, probability))
        auc = float(roc_auc_score(y_test, probability))
        bins = calibration_bins(y_test, probability, method)
        calibration_bins_frames.append(bins) if method != "raw" else None
        calibration_rows.append({
            "method": method, "brier_score": brier, "roc_auc": auc,
            "expected_calibration_error": float(bins["weighted_calibration_error"].sum()),
            "brier_improvement_vs_raw": float(raw_metrics["brier_score"]) - brier,
            "roc_auc_change_vs_raw": auc - raw_auc,
        })
    calibration_comparison = pd.DataFrame(calibration_rows)
    eligible = calibration_comparison.loc[(calibration_comparison["method"].ne("raw")) & (calibration_comparison["brier_improvement_vs_raw"].gt(0.005)) & (calibration_comparison["roc_auc_change_vs_raw"].ge(-0.01))]
    retained = eligible.sort_values("brier_score").head(1)["method"].tolist()
    retained_methods = retained or ["raw"]
    calibration_comparison["retained_for_operational_use"] = calibration_comparison["method"].isin(retained_methods)
    calibration_comparison["decision_reason"] = calibration_comparison.apply(
        lambda row: (
            "Material Brier improvement (>0.005) without ROC-AUC degradation beyond 0.01."
            if row["method"] in retained
            else "Raw probability retained because no calibration candidate met the predefined material-improvement rule."
            if row["method"] == "raw" and not retained
            else "Not retained: did not meet the predefined reliability-improvement and ranking-preservation rule."
        ),
        axis=1,
    )
    calibration_output = pd.concat(calibration_bins_frames, ignore_index=True)

    global_explainability, local_explainability = _linear_contributions(model, X_test.reset_index(drop=True), id_test.reset_index(drop=True))
    distribution = pd.DataFrame({"probability": raw_probability})
    distribution["score_bin"] = pd.cut(distribution["probability"], np.linspace(0, 1, 11), include_lowest=True).astype(str)
    distribution = distribution.groupby("score_bin", as_index=False).agg(customers=("probability", "size"), mean_probability=("probability", "mean"))
    class_distribution = pd.DataFrame({"class": ["retained", "churned"], "customers": [(y_test == 0).sum(), (y_test == 1).sum()]})
    class_distribution["customer_share"] = class_distribution["customers"] / len(y_test)

    outputs = {
        "churn_model_metrics.csv": metrics,
        "churn_confusion_matrix.csv": confusion,
        "churn_ranking_metrics.csv": ranking,
        "churn_threshold_analysis.csv": thresholds,
        "churn_calibration_bins.csv": calibration_output,
        "churn_calibration_comparison.csv": calibration_comparison,
        "churn_prediction_distribution.csv": distribution,
        "churn_class_distribution.csv": class_distribution,
        "churn_model_global_explainability.csv": global_explainability,
        "churn_model_local_explainability.csv": local_explainability,
    }
    for name, frame in outputs.items():
        write_csv(frame, project_config.export_dir / name)
    _write_reports(metrics.iloc[0], ranking, thresholds, calibration_comparison, global_explainability, local_explainability, project_config)
    return ChurnValidationResult(metrics, ranking, thresholds, calibration_output, calibration_comparison, global_explainability, local_explainability)


def _write_reports(metrics: pd.Series, ranking: pd.DataFrame, thresholds: pd.DataFrame, calibration: pd.DataFrame, global_exp: pd.DataFrame, local_exp: pd.DataFrame, project_config: ProjectConfig) -> None:
    top10 = ranking.loc[ranking["population_fraction"].eq(0.10)].iloc[0]
    recommended_rows = thresholds.loc[thresholds["recommended_under_modeled_capacity"]]
    retained = calibration.loc[calibration["retained_for_operational_use"]]
    calibration_decision = retained.iloc[0]["method"] if len(retained) else "none"
    evaluation = [
        "# Churn Model Evaluation", "", "The existing logistic-regression algorithm was preserved and evaluated on its deterministic 25% held-out set.", "",
        "## Predictive Metrics", "",
        f"- ROC-AUC: {metrics['roc_auc']:.4f}", f"- PR-AUC: {metrics['pr_auc']:.4f}", f"- Precision: {metrics['precision']:.4f}",
        f"- Recall: {metrics['recall']:.4f}", f"- F1: {metrics['f1']:.4f}", f"- Accuracy: {metrics['accuracy']:.4f}",
        f"- Log loss: {metrics['log_loss']:.4f}", f"- Brier score: {metrics['brier_score']:.4f}", "",
        "## Ranking Use", "", f"The top 10% of risk scores captured {top10['recall_at_k']:.1%} of held-out churners with lift {top10['lift_at_k']:.2f} over the held-out base rate.", "",
        "## Modeled Operating Point", "",
        (f"Under a modeled 20% intervention-capacity assumption, threshold {recommended_rows.iloc[0]['threshold']:.4f} selects {recommended_rows.iloc[0]['selected_customer_share']:.1%} of customers with precision {recommended_rows.iloc[0]['precision']:.1%} and recall {recommended_rows.iloc[0]['recall']:.1%}." if not recommended_rows.empty else "No fixed probability threshold in the tested range produces a non-empty selection within five percentage points of the modeled 20% capacity. Use explicit top-K ranking for capacity planning; no universal threshold is recommended."),
        "This is an analytical operating point, not a production-approved threshold. False-positive cost uses a synthetic $6 contact assumption; false-negative exposure uses held-out historical CLV.", "",
        "## Limitations", "", "All records and outcomes are synthetic. Strong discrimination reflects the controlled generator and does not establish future production performance.",
    ]
    write_markdown(evaluation, project_config.report_dir / "churn_model_evaluation.md")
    calibration_report = [
        "# Churn Probability Calibration", "", f"Raw Brier score: {metrics['brier_score']:.4f}.",
        f"Calibration retained: **{calibration_decision}**.", "",
        "Sigmoid and isotonic calibration were evaluated with five-fold calibration on the training partition and compared on the untouched held-out partition. A method is retained only for Brier improvement above 0.005 without ROC-AUC degradation below -0.01.", "",
        "No current production artifact is replaced automatically. Calibration affects probability reliability, not whether observational features cause churn.",
    ]
    write_markdown(calibration_report, project_config.report_dir / "churn_probability_calibration.md")
    top_features = ", ".join(global_exp.head(6)["feature"])
    max_error = local_exp["absolute_reconciliation_error"].max()
    explainability = [
        "# Churn Model Explainability", "", "## Method", "",
        "SHAP is not installed in the current local dependency set. For the existing standardized logistic regression, P3 uses an exact additive log-odds decomposition: each standardized feature deviation multiplied by its fitted coefficient. This is lightweight, model-specific, and reconciles exactly to the model probability.", "",
        f"Leading mean absolute predictive contributions: {top_features}.",
        f"Local example maximum probability reconciliation error: {max_error:.3e}.", "",
        "## Statistical Drivers Versus Predictive Contributions", "",
        "Statistical driver analysis describes population-level associations and uncertainty. Predictive contribution analysis explains why this fitted model produced a score for a record. They may disagree and neither establishes causality.", "",
        "Use ‘factors contributing to the model prediction’ and ‘features associated with higher predicted churn risk’; never interpret these outputs as causes of churn.",
    ]
    write_markdown(explainability, project_config.report_dir / "churn_model_explainability.md")


if __name__ == "__main__":
    run_churn_validation()
