"""Unit tests for `authoring/delta.py`'s NL-to-delta proposal (FR-001, R4), over a fake
litellm (never a live network, plan.md Testing)."""

from __future__ import annotations

import pytest
from modelling_specification.authoring.delta import (
    DeltaProposalError,
    LlmMessage,
    assign_missing_ids,
    propose_delta,
    resolve_unknown_endpoints,
)
from support.fake_llm import FakeCompletion


def test_propose_delta_sends_the_request_and_returns_parsed_elements_and_relationships(
    configured_fake_llm: FakeCompletion,
) -> None:
    result = propose_delta("add an application function fn-example under sub-modelling")

    assert result["elements"] == [
        {"type": "ApplicationFunction", "name": "add an application function fn-example under sub-modelling"}
    ]
    assert result["relationships"] == []
    sent = configured_fake_llm.calls[0]
    assert sent["messages"][-1] == {
        "role": "user",
        "content": "add an application function fn-example under sub-modelling",
    }


def test_propose_delta_calls_the_configured_provider_and_model(configured_fake_llm: FakeCompletion) -> None:
    propose_delta("add a function")

    sent = configured_fake_llm.calls[0]
    assert sent["model"] == "ollama_chat/test-model"


def test_propose_delta_rejects_an_empty_request(configured_fake_llm: FakeCompletion) -> None:
    with pytest.raises(DeltaProposalError, match="Cannot propose a delta from an empty request"):
        propose_delta("   ")

    assert configured_fake_llm.calls == []


def test_propose_delta_wraps_a_provider_failure(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.error = ConnectionError("connection refused")

    with pytest.raises(DeltaProposalError, match=r"ollama_chat/test-model.*connection refused"):
        propose_delta("add a function")


def test_propose_delta_rejects_an_empty_response(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = "   "

    with pytest.raises(DeltaProposalError, match="empty response"):
        propose_delta("add a function")


def test_propose_delta_surfaces_a_plain_text_reply_as_a_message(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = "Which assessment do you mean?"

    with pytest.raises(LlmMessage) as caught:
        propose_delta("suggest a goal")

    assert caught.value.text == "Which assessment do you mean?"


def test_propose_delta_tells_the_llm_it_may_ask_or_suggest_in_plain_text(configured_fake_llm: FakeCompletion) -> None:
    propose_delta("add a function")

    assert "plain-text message" in configured_fake_llm.calls[0]["messages"][0]["content"]


def test_propose_delta_rejects_a_response_missing_elements_or_relationships(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = '{"elements": []}'

    with pytest.raises(DeltaProposalError, match="elements.*relationships"):
        propose_delta("add a function")


def test_propose_delta_strips_a_surrounding_markdown_fence(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = '```json\n{"elements": [], "relationships": []}\n```'

    result = propose_delta("add a function")

    assert result == {"elements": [], "relationships": []}


def test_assign_missing_ids_leaves_an_explicit_id_alone() -> None:
    result = assign_missing_ids([{"type": "ApplicationFunction", "id": "fn-explicit", "name": "X"}], set())

    assert result == [{"type": "ApplicationFunction", "id": "fn-explicit", "name": "X"}]


def test_assign_missing_ids_slugifies_type_and_name() -> None:
    result = assign_missing_ids([{"type": "ApplicationFunction", "name": "New Delta Fn!"}], set())

    assert result[0]["id"] == "applicationfunction-new-delta-fn"


def test_assign_missing_ids_deduplicates_against_existing_and_sibling_ids() -> None:
    result = assign_missing_ids(
        [
            {"type": "ApplicationFunction", "name": "X"},
            {"type": "ApplicationFunction", "name": "X"},
        ],
        {"applicationfunction-x"},
    )

    assert [e["id"] for e in result] == ["applicationfunction-x-2", "applicationfunction-x-3"]


def test_propose_delta_gives_the_llm_the_existing_element_catalogue(configured_fake_llm: FakeCompletion) -> None:
    propose_delta("link drift to the goal", [("assess-drift-debt", "Assessment", "Architectural drift")])

    system = configured_fake_llm.calls[0]["messages"][0]["content"]
    assert "assess-drift-debt | Assessment | Architectural drift" in system


_KNOWN = {
    "assess-drift-debt": "Architectural drift is accumulating as unmanaged risk",
    "goal-frictionless-architecture": "Frictionless Architecture & Governance at Machine Speed",
    "role-ea": "Enterprise Architect",
}


def test_resolve_unknown_endpoints_repoints_a_misspelt_id_and_reports_it() -> None:
    rels = [{"type": "Association", "source": "assess-drfit-debt", "target": "goal-frictionless-architecture"}]

    resolved, notes = resolve_unknown_endpoints(rels, _KNOWN)

    assert resolved[0]["source"] == "assess-drift-debt"
    assert resolved[0]["target"] == "goal-frictionless-architecture"
    assert len(notes) == 1
    assert "assess-drfit-debt" in notes[0]


def test_resolve_unknown_endpoints_leaves_a_weak_or_ambiguous_match_for_validation() -> None:
    rels = [{"type": "Association", "source": "something-unrelated", "target": "role-ea"}]

    resolved, notes = resolve_unknown_endpoints(rels, _KNOWN)

    assert resolved == rels
    assert notes == []
