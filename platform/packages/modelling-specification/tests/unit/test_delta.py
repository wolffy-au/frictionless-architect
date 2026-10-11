"""Unit tests for `authoring/delta.py`'s NL-to-delta proposal (FR-001, R4), over a fake
litellm (never a live network, plan.md Testing)."""

from __future__ import annotations

import pytest
from modelling_specification.authoring.delta import DeltaProposalError, assign_missing_ids, propose_delta
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


def test_propose_delta_rejects_unparseable_json(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = "not json at all"

    with pytest.raises(DeltaProposalError, match="unparseable"):
        propose_delta("add a function")


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
