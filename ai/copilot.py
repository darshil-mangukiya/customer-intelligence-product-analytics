from __future__ import annotations

import json
import os
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from config.settings import CONFIG


RESPONSE_KEYS = [
    "answer", "key_findings", "supporting_metrics", "statistical_evidence", "segments",
    "financial_exposure", "recommendations", "evidence", "data_quality_warnings",
    "assumptions", "uncertainty", "follow_up_analysis",
]
PROMPT_VERSION = "customer-strategy-advisor-v2"
RESPONSE_SCHEMA_VERSION = "customer-strategy-response-v1"
EVIDENCE_SCHEMA_VERSION = "customer-insight-packet-v2"


class Provider(Protocol):
    def generate(self, question: str, evidence: dict[str, object]) -> dict[str, object]: ...


def load_packet(path: Path | None = None) -> dict[str, object]:
    packet_path = path or CONFIG.root / "artifacts" / "customer_intelligence" / "latest_customer_insight_packet.json"
    if not packet_path.exists():
        raise FileNotFoundError(packet_path)
    return json.loads(packet_path.read_text(encoding="utf-8"))


def get_customer_kpis(packet: dict[str, object]) -> object: return packet["customer_kpis"]
def get_segment_summary(packet: dict[str, object]) -> object: return packet["segment_summary"]
def get_segment_migrations(packet: dict[str, object]) -> object: return packet["segment_migrations"]
def get_churn_summary(packet: dict[str, object]) -> object: return packet["churn_summary"]
def get_churn_drivers(packet: dict[str, object]) -> object: return packet["churn_drivers"]
def get_clv_summary(packet: dict[str, object]) -> object: return packet["clv_summary"]
def get_cohort_summary(packet: dict[str, object]) -> object: return packet["cohort_summary"]
def get_experiment_result(packet: dict[str, object]) -> object: return packet["experiment_results"]
def get_experiment_validity(packet: dict[str, object]) -> object: return packet["experiment_validity"]
def get_experiment_methodology() -> object:
    return json.loads((CONFIG.root / "experimentation" / "experiment_registry.yml").read_text(encoding="utf-8"))
def get_retention_scenario(packet: dict[str, object]) -> object: return packet["retention_scenarios"]
def get_action_items(packet: dict[str, object]) -> object: return packet["priority_actions"]
def get_data_quality_status(packet: dict[str, object]) -> object: return packet["data_quality_warnings"]


def _empty_response(answer: str) -> dict[str, object]:
    return {
        "answer": answer, "key_findings": [], "supporting_metrics": {},
        "statistical_evidence": {}, "segments": [], "financial_exposure": {},
        "recommendations": [], "evidence": [], "data_quality_warnings": [],
        "assumptions": [], "uncertainty": [], "follow_up_analysis": [],
    }


def validate_response(response: dict[str, object]) -> dict[str, object]:
    missing = [key for key in RESPONSE_KEYS if key not in response]
    extra = [key for key in response if key not in RESPONSE_KEYS]
    if missing or extra:
        raise ValueError(f"malformed copilot response; missing={missing}, extra={extra}")
    if not isinstance(response["answer"], str):
        raise TypeError("answer must be a string")
    return response


class DisabledProvider:
    def generate(self, question: str, evidence: dict[str, object]) -> dict[str, object]:
        return _empty_response("AI is disabled. Use the deterministic insight packet and generated reports directly.")


class FakeProvider:
    """Deterministic provider used for local demonstrations and fidelity tests."""

    def generate(self, question: str, evidence: dict[str, object]) -> dict[str, object]:
        lowered = question.lower()
        if "ignore previous" in lowered or "override governance" in lowered or "write to" in lowered or "delete" in lowered:
            response = _empty_response("I cannot override governance controls, execute writes, or follow prompt-injection instructions.")
            response["recommendations"] = ["Use the governed read-only decision process and obtain human approval."]
            return response
        if any(term in lowered for term in ["email", "phone", "address", "raw customer", "customer id"]):
            response = _empty_response("I cannot provide customer-level identifiers or sensitive fields. Aggregate evidence is available.")
            response["recommendations"] = ["Use approved aggregate segment outputs for analysis."]
            return response
        experiment_id = str(evidence["experiment_results"][0]["experiment_id"]).lower()
        if "experiment" in lowered and "exp-" in lowered and experiment_id not in lowered:
            response = _empty_response("Insufficient governed evidence: that experiment ID was not found.")
            response["uncertainty"] = ["Only registered experiments in the approved insight packet can be discussed."]
            return response
        known_terms = ["churn", "clv", "segment", "cohort", "experiment", "retention", "srm", "reconciliation", "driver", "kpi"]
        if not any(term in lowered for term in known_terms):
            response = _empty_response("Insufficient governed evidence for that question.")
            response["uncertainty"] = ["The requested entity or metric was not found in the approved insight packet."]
            return response
        if evidence.get("python_r_reconciliation", {}).get("status") == "FAIL":
            response = _empty_response("Inconsistent governed statistical evidence requires review; I will not choose or invent a convenient value.")
            response["data_quality_warnings"] = evidence.get("data_quality_warnings", [])
            response["uncertainty"] = ["Python and R statistical evidence did not reconcile."]
            return response
        experiment = evidence["experiment_results"][0]
        response = _empty_response("The governed evidence supports an advisory review; no automated customer action is authorized.")
        response["evidence"] = list(evidence["source_evidence"])
        response["data_quality_warnings"] = evidence["data_quality_warnings"]
        response["assumptions"] = list(evidence["limitations"])
        response["uncertainty"] = ["All data and experiment outcomes are synthetic."]
        if "experiment" in lowered or "srm" in lowered or "significant" in lowered:
            validity = evidence["experiment_validity"]
            response["answer"] = (
                f"The synthetic retention experiment was statistically significant={experiment['statistically_significant']} "
                f"and practically significant={experiment['practically_significant']}. SRM status={validity['status']}."
            )
            response["supporting_metrics"] = {
                "control_rate": experiment["baseline_rate"], "treatment_rate": experiment["treatment_rate"],
                "absolute_lift": experiment["absolute_difference"], "relative_lift": experiment["relative_lift"],
            }
            response["statistical_evidence"] = {
                "p_value": experiment["p_value"], "confidence_interval_low": experiment["confidence_interval_low"],
                "confidence_interval_high": experiment["confidence_interval_high"], "effect_size": experiment["effect_size"],
                "srm_status": validity["status"],
            }
            response["recommendations"] = ["Keep a holdout and require human review before any real-world rollout."]
        elif "driver" in lowered or "cause" in lowered:
            drivers = evidence["churn_drivers"][:3]
            response["answer"] = "The strongest signals are associated factors, not established causes."
            response["key_findings"] = [row["business_interpretation"] for row in drivers]
            response["supporting_metrics"] = {row["metric_or_driver"]: row["importance_or_strength"] for row in drivers}
            response["recommendations"] = ["Validate proposed interventions prospectively with controlled experiments."]
        elif "clv" in lowered or "exposure" in lowered:
            response["answer"] = "CLV is a modeled customer-value estimate used for prioritization, not realized impact."
            response["supporting_metrics"] = dict(evidence["clv_summary"])
            response["financial_exposure"] = dict(evidence["revenue_or_clv_exposure"])
        elif "segment" in lowered:
            migrations = evidence["segment_migrations"][:5]
            response["answer"] = "Segment migration identifies customer groups whose RFM position changed between the historical cutoff and current snapshot."
            response["segments"] = migrations
            response["recommendations"] = ["Review deteriorating, high-value transitions before selecting an intervention."]
        else:
            response["supporting_metrics"] = dict(evidence["churn_summary"])
            response["recommendations"] = ["Use the retention action center for prioritized human review."]
        return validate_response(response)


@dataclass
class OpenAIProvider:
    api_key: str
    model: str
    endpoint: str = "https://api.openai.com/v1/responses"

    @classmethod
    def from_environment(cls) -> "OpenAIProvider":
        key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL")
        if not key or not model:
            raise RuntimeError("OPENAI_API_KEY and OPENAI_MODEL are required for real provider execution")
        return cls(key, model)

    def generate(self, question: str, evidence: dict[str, object]) -> dict[str, object]:
        schema = {
            "type": "object", "additionalProperties": False,
            "required": RESPONSE_KEYS,
            "properties": {
                "answer": {"type": "string"},
                "key_findings": {"type": "array", "items": {"type": "string"}},
                "supporting_metrics": {"type": "object", "additionalProperties": True},
                "statistical_evidence": {"type": "object", "additionalProperties": True},
                "segments": {"type": "array", "items": {}},
                "financial_exposure": {"type": "object", "additionalProperties": True},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "data_quality_warnings": {"type": "array", "items": {}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "uncertainty": {"type": "array", "items": {"type": "string"}},
                "follow_up_analysis": {"type": "array", "items": {"type": "string"}},
            },
        }
        instructions = (
            "You are an advisory customer strategy analyst. Use only supplied aggregate evidence. "
            "Never calculate or invent metrics, imply observational causality, reveal identifiers, or authorize actions. "
            f"Copy supporting numbers exactly and disclose synthetic-data and quality limitations. Prompt version={PROMPT_VERSION}."
        )
        payload = {
            "model": self.model, "instructions": instructions,
            "input": json.dumps({"question": question, "governed_evidence": evidence}),
            "store": False,
            "text": {"format": {"type": "json_schema", "name": "customer_strategy_response", "strict": True, "schema": schema}},
        }
        request = urllib.request.Request(
            self.endpoint, data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode())
        output_text = body.get("output_text")
        if not output_text:
            texts = [content.get("text") for item in body.get("output", []) for content in item.get("content", []) if content.get("type") == "output_text"]
            output_text = "".join(texts)
        return validate_response(json.loads(output_text))


def ask(question: str, provider: Provider, packet: dict[str, object] | None = None) -> dict[str, object]:
    return validate_response(provider.generate(question, packet or load_packet()))


def ask_reliable(
    question: str,
    provider: Provider,
    packet: dict[str, object] | None = None,
    fallback: Provider | None = None,
    attempts: int = 2,
) -> dict[str, object]:
    """Bounded retry with a deterministic fallback and sanitized observability."""
    evidence = packet or load_packet()
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    response: dict[str, object] | None = None
    error_type = ""
    fallback_used = False
    for _ in range(max(1, attempts)):
        try:
            response = ask(question, provider, evidence)
            break
        except (OSError, TimeoutError, ValueError, TypeError, json.JSONDecodeError) as exc:
            error_type = type(exc).__name__
    if response is None:
        fallback_used = True
        response = ask(question, fallback or DisabledProvider(), evidence)
    log = {
        "request_id": request_id, "timestamp_utc": datetime.now(UTC).isoformat(),
        "provider": type(provider).__name__, "model": getattr(provider, "model", "deterministic"),
        "prompt_version": PROMPT_VERSION, "response_schema_version": RESPONSE_SCHEMA_VERSION,
        "evidence_schema_version": evidence.get("evidence_schema_version", EVIDENCE_SCHEMA_VERSION),
        "evidence_ids": evidence.get("source_evidence", []), "schema_validation": "PASS",
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "token_counts": None, "fallback_used": fallback_used, "error_type": error_type,
        "human_review_required": True,
    }
    path = CONFIG.root / "artifacts" / "ai" / "ai_execution_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log, allow_nan=False) + "\n")
    except PermissionError:
        # Managed review sandboxes may make generated evidence read-only after
        # creation. Runtime behavior remains available; no unsafe alternate log.
        pass
    return response
