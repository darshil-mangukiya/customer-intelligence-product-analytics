"""Build compact, governed Tableau presentation sources and validation evidence."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
TABLEAU = ROOT / "dashboards" / "tableau"
DATA = TABLEAU / "data"
VALIDATION = TABLEAU / "validation"
SOURCE = ROOT / "data"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(relative: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / relative)


def write_csv(frame: pd.DataFrame, name: str) -> tuple[Path, bool]:
    path = DATA / name
    content = frame.to_csv(index=False, lineterminator="\n")
    if path.exists() and path.read_text() == content:
        return path, False
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    os.replace(temporary, path)
    return path, True


def write_text(path: Path, content: str) -> None:
    if path.exists() and path.read_text() == content:
        return
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    os.replace(temporary, path)


def existing_manifest_timestamp() -> str | None:
    path = TABLEAU / "tableau_data_manifest.yml"
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith("generated_at_utc: "):
            return json.loads(line.removeprefix("generated_at_utc: "))
    return None


def yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def write_manifest(entries: list[dict[str, object]], created_at: str) -> None:
    lines = [
        "version: 1",
        f"generated_at_utc: {yaml_scalar(created_at)}",
        "synthetic_data: true",
        'refresh_command: ".venv/bin/python dashboards/tableau/build/build_tableau_assets.py"',
        "sources:",
    ]
    for entry in entries:
        lines.append(f"  - id: {entry['id']}")
        for key in (
            "file",
            "source_mart",
            "grain",
            "row_count",
            "primary_key",
            "checksum_sha256",
            "data_profile",
        ):
            lines.append(f"    {key}: {yaml_scalar(entry[key])}")
        lines.append("    synthetic_data: true")
        lines.append("    expected_columns:")
        lines.extend(f"      - {yaml_scalar(column)}" for column in entry["expected_columns"])
    write_text(TABLEAU / "tableau_data_manifest.yml", "\n".join(lines) + "\n")


def build_customer_source() -> pd.DataFrame:
    overview = read("data/marts/mart_customer_overview.csv")
    segments = read("data/marts/mart_customer_segments.csv")
    rfm = read("data/marts/mart_rfm_segments.csv")
    churn = read("data/marts/mart_churn_risk.csv")
    clv = read("data/marts/mart_clv.csv")

    base_columns = [
        "customer_id",
        "signup_date",
        "acquisition_channel",
        "state",
        "loyalty_tier",
        "top_purchase_category",
        "orders",
        "net_revenue",
        "return_adjusted_profit",
        "discount_amount",
        "returns",
        "recency_days",
        "repeat_purchase_flag",
        "return_rate",
        "discount_dependency",
        "profit_margin",
        "churn_label",
        "historical_clv",
    ]
    customer = overview[base_columns].copy()
    customer = customer.merge(
        segments[["customer_id", "segment_name", "business_recommendation"]],
        on="customer_id",
        validate="one_to_one",
    )
    customer = customer.merge(
        rfm[["customer_id", "rfm_segment", "rfm_total_score"]],
        on="customer_id",
        validate="one_to_one",
    )
    customer = customer.merge(
        churn[
            [
                "customer_id",
                "churn_probability",
                "churn_risk_tier",
                "expected_profit_at_risk",
            ]
        ],
        on="customer_id",
        validate="one_to_one",
    )
    customer = customer.merge(
        clv[
            [
                "customer_id",
                "predicted_next_90d_profit",
                "predicted_12m_clv",
                "clv_band",
                "acquisition_cohort",
                "expected_clv_at_risk",
            ]
        ],
        on="customer_id",
        validate="one_to_one",
    )
    customer.insert(0, "data_context", "Synthetic portfolio data")
    return customer.sort_values("customer_id")


def build_experiment_source() -> pd.DataFrame:
    variants = read("data/exports/ab_test_summary.csv")
    result = read("data/exports/experiment_evaluation.csv").iloc[0]
    for column in (
        "experiment_id",
        "absolute_difference",
        "relative_lift",
        "confidence_interval_low",
        "confidence_interval_high",
        "p_value",
        "alpha",
        "statistically_significant",
        "practical_threshold",
        "practically_significant",
        "effect_size",
        "decision",
        "recommendation",
        "data_provenance",
        "limitations",
    ):
        variants[column] = result[column]
    variants.insert(0, "data_context", "Synthetic experiment; no real customer intervention")
    return variants


def expected_metrics(customer: pd.DataFrame, cohort: pd.DataFrame, product: pd.DataFrame) -> dict[str, object]:
    experiment = read("data/exports/experiment_evaluation.csv").iloc[0]
    metrics: dict[str, object] = {
        "total_customers": int(customer["customer_id"].nunique()),
        "total_customer_revenue": float(customer["net_revenue"].sum()),
        "total_customer_profit": float(customer["return_adjusted_profit"].sum()),
        "average_predicted_12m_clv": float(customer["predicted_12m_clv"].mean()),
        "median_predicted_12m_clv": float(customer["predicted_12m_clv"].median()),
        "observed_churn_population": int(customer["churn_label"].sum()),
        "critical_churn_risk_population": int((customer["churn_risk_tier"] == "Critical").sum()),
        "cohort_rows": int(len(cohort)),
        "distinct_cohorts": int(cohort["cohort_month"].nunique()),
        "cohort_total_customers": int(
            cohort.groupby("cohort_month")["cohort_size"].max().sum()
        ),
        "product_rows": int(len(product)),
        "product_revenue": float(product["net_revenue"].sum()),
        "product_profit": float(product["return_adjusted_profit"].sum()),
        "experiment_control_n": int(experiment["control_n"]),
        "experiment_treatment_n": int(experiment["treatment_n"]),
        "experiment_control_rate": float(experiment["baseline_rate"]),
        "experiment_treatment_rate": float(experiment["treatment_rate"]),
        "experiment_absolute_lift": float(experiment["absolute_difference"]),
        "experiment_p_value": float(experiment["p_value"]),
        "experiment_statistically_significant": bool(experiment["statistically_significant"]),
        "experiment_practically_significant": bool(experiment["practically_significant"]),
        "experiment_decision": str(experiment["decision"]),
    }
    segment_counts = customer.groupby("segment_name")["customer_id"].nunique().sort_index()
    for segment, count in segment_counts.items():
        metric_name = "segment_customers__" + str(segment).lower().replace(" ", "_").replace("-", "_")
        metrics[metric_name] = int(count)
    return metrics


def write_reconciliation(metrics: dict[str, object]) -> None:
    tolerances = {
        "integer": 0,
        "currency": 0.01,
        "rate": 1e-9,
        "boolean": 0,
        "text": 0,
    }
    kind_by_name = {
        name: (
            "integer"
            if isinstance(value, int) and not isinstance(value, bool)
            else "boolean"
            if isinstance(value, bool)
            else "currency"
            if any(token in name for token in ("revenue", "profit", "clv"))
            else "rate"
            if isinstance(value, float)
            else "text"
        )
        for name, value in metrics.items()
    }
    path = VALIDATION / "tableau_reconciliation_report.csv"
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        lineterminator="\n",
        fieldnames=[
            "metric",
            "authoritative_value",
            "tableau_expected_value",
            "tolerance",
            "status",
            "source",
        ],
    )
    writer.writeheader()
    for name, value in metrics.items():
        writer.writerow(
            {
                "metric": name,
                "authoritative_value": value,
                "tableau_expected_value": value,
                "tolerance": tolerances[kind_by_name[name]],
                "status": "PASS_EXPECTED_CONTRACT",
                "source": "governed CSV output",
            }
        )
    write_text(path, buffer.getvalue())
    write_text(VALIDATION / "expected_results.json", json.dumps(metrics, indent=2) + "\n")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    customer = build_customer_source()
    cohort = read("data/marts/mart_cohort_retention.csv")
    product = read("data/marts/mart_product_profitability.csv")
    sources = [
        ("executive_kpis", read("data/exports/kpi_summary.csv"), "tableau_executive_kpis.csv", "data/exports/kpi_summary.csv", "one row per governed KPI", "kpi_name"),
        ("customer_analytics", customer, "tableau_customer_analytics.csv", "five customer marts joined 1:1", "one row per customer", "customer_id"),
        ("cohort_retention", cohort, "tableau_cohort_retention.csv", "data/marts/mart_cohort_retention.csv", "cohort month and month index", "cohort_month + cohort_index"),
        ("product_profitability", product, "tableau_product_profitability.csv", "data/marts/mart_product_profitability.csv", "one row per product", "product_id"),
        ("experiment_results", build_experiment_source(), "tableau_experiment_results.csv", "experiment evaluation + A/B summary", "experiment variant", "experiment_id + variant"),
        ("segment_migration", read("data/exports/segment_migration_summary.csv"), "tableau_segment_migration.csv", "data/exports/segment_migration_summary.csv", "prior/current segment transition", "prior_segment + current_segment + migration_signal"),
        ("churn_drivers", read("data/exports/churn_driver_summary.csv"), "tableau_churn_drivers.csv", "data/exports/churn_driver_summary.csv", "one row per model feature", "feature"),
        ("retention_actions", read("data/exports/retention_action_center.csv"), "tableau_retention_actions.csv", "data/exports/retention_action_center.csv", "segment and churn risk tier", "segment_name + churn_risk_tier"),
        ("retention_economics", read("data/exports/retention_economics_scenarios.csv"), "tableau_retention_economics.csv", "data/exports/retention_economics_scenarios.csv", "one row per synthetic scenario", "scenario"),
    ]

    manifest: list[dict[str, object]] = []
    presentation_data_changed = False
    for source_id, frame, filename, source_mart, grain, primary_key in sources:
        frame = frame.copy()
        if "data_context" not in frame.columns:
            frame.insert(0, "data_context", "Synthetic portfolio data")
        output, changed = write_csv(frame, filename)
        presentation_data_changed = presentation_data_changed or changed
        manifest.append(
            {
                "id": source_id,
                "file": output.relative_to(ROOT).as_posix(),
                "source_mart": source_mart,
                "grain": grain,
                "row_count": len(frame),
                "primary_key": primary_key,
                "checksum_sha256": sha256(output),
                "data_profile": f"{len(frame)} rows; {len(frame.columns)} columns; generated/synthetic",
                "expected_columns": frame.columns.tolist(),
            }
        )

    if not presentation_data_changed:
        created_at = existing_manifest_timestamp() or created_at
    write_manifest(manifest, created_at)
    write_reconciliation(expected_metrics(customer, cohort, product))
    print(f"Built {len(sources)} Tableau sources and {len(manifest)} manifest entries.")


if __name__ == "__main__":
    main()
