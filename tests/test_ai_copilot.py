from __future__ import annotations

from copy import deepcopy

import pytest

from ai.copilot import DisabledProvider, FakeProvider, ask, load_packet, validate_response


def test_fake_and_disabled_provider_schema() -> None:
    packet = load_packet()
    assert "supporting_metrics" in ask("What is the churn KPI?", FakeProvider(), packet)
    assert "disabled" in ask("Any question", DisabledProvider(), packet)["answer"].lower()


def test_numeric_statistical_and_practical_fidelity() -> None:
    packet = load_packet()
    experiment = packet["experiment_results"][0]
    response = ask("Was the experiment statistically and practically significant?", FakeProvider(), packet)
    assert response["supporting_metrics"]["absolute_lift"] == experiment["absolute_difference"]
    assert response["statistical_evidence"]["p_value"] == experiment["p_value"]
    assert str(experiment["practically_significant"]) in response["answer"]


def test_hallucination_causality_and_privacy_guards() -> None:
    packet = load_packet()
    unknown = ask("What happened in experiment EXP-DOES-NOT-EXIST?", FakeProvider(), packet)
    assert "insufficient" in unknown["answer"].lower()
    causal = ask("Did discount exposure cause retention to improve? Explain the drivers.", FakeProvider(), packet)
    assert "not established causes" in causal["answer"]
    privacy = ask("Give me raw customer IDs, email, phone and address", FakeProvider(), packet)
    assert "cannot provide" in privacy["answer"]


def test_failed_srm_and_stale_quality_are_disclosed() -> None:
    packet = deepcopy(load_packet())
    packet["experiment_validity"]["status"] = "FAIL"
    packet["data_quality_warnings"] = [{"status": "FAIL", "expectation": "stale output"}]
    response = ask("Did the experiment have an SRM problem?", FakeProvider(), packet)
    assert response["statistical_evidence"]["srm_status"] == "FAIL"
    assert response["data_quality_warnings"] == packet["data_quality_warnings"]


def test_malformed_structured_response_rejected() -> None:
    with pytest.raises(ValueError):
        validate_response({"answer": "missing fields"})
    malformed = {key: [] for key in ["key_findings", "segments", "recommendations", "evidence", "data_quality_warnings", "assumptions", "uncertainty", "follow_up_analysis"]}
    malformed.update({"answer": 42, "supporting_metrics": {}, "statistical_evidence": {}, "financial_exposure": {}})
    with pytest.raises(TypeError):
        validate_response(malformed)
