"""Unit tests for `authoring/delta.py`'s NL-to-delta proposal (FR-001, R4), over a fake
litellm (never a live network, plan.md Testing)."""

from __future__ import annotations

import pytest
from llm_provider_config import MissingCredentialError, NotConfiguredError
from modelling_specification.authoring import delta
from modelling_specification.authoring.delta import (
    DeltaProposalError,
    LlmMessage,
    assign_missing_ids,
    assign_missing_view_ids,
    propose_delta,
    resolve_unknown_element_edits,
    resolve_unknown_element_removals,
    resolve_unknown_endpoints,
    resolve_unknown_members,
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


def test_propose_delta_wraps_a_not_configured_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_not_configured(component_id: str) -> None:
        raise NotConfiguredError(f"no provider configured for {component_id}")

    monkeypatch.setattr(delta, "resolve_call", raise_not_configured)

    with pytest.raises(DeltaProposalError, match="no provider configured"):
        propose_delta("add a function")


def test_propose_delta_wraps_a_missing_credential_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_missing_credential(component_id: str) -> None:
        raise MissingCredentialError("no API key for ollama")

    monkeypatch.setattr(delta, "resolve_call", raise_missing_credential)

    with pytest.raises(DeltaProposalError, match="no API key for ollama"):
        propose_delta("add a function")


def test_propose_delta_wraps_a_provider_failure(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.error = ConnectionError("connection refused")

    with pytest.raises(DeltaProposalError, match=r"ollama_chat/test-model.*server log") as excinfo:
        propose_delta("add a function")
    assert "connection refused" not in str(excinfo.value)


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

    assert result == {
        "elements": [],
        "relationships": [],
        "views": [],
        "view_membership_edits": [],
        "element_edits": [],
        "element_removals": [],
        "relationship_removals": [],
    }


def test_propose_delta_returns_structured_options_when_the_llm_suggests_several(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = (
        '{"options": ['
        '{"rationale": "closes the drift gap per conv-interposed-neo4j-volume",'
        ' "convention_refs": ["conv-interposed-neo4j-volume"],'
        ' "elements": [{"type": "Requirement", "name": "Close drift gap"}], "relationships": []},'
        '{"rationale": "alternative: realize via an existing capability",'
        ' "convention_refs": [], "elements": [], "relationships": []}'
        "]}"
    )

    result = propose_delta("what should I do about architectural drift?")

    assert "options" in result
    assert len(result["options"]) == 2
    first = result["options"][0]
    assert first["rationale"] == "closes the drift gap per conv-interposed-neo4j-volume"
    assert first["convention_refs"] == ["conv-interposed-neo4j-volume"]
    assert first["elements"] == [{"type": "Requirement", "name": "Close drift gap"}]


def test_propose_delta_defaults_a_missing_rationale_and_convention_refs(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = '{"options": [{"elements": [], "relationships": []}]}'

    result = propose_delta("suggest something")

    assert result["options"][0] == {"rationale": "", "convention_refs": [], "elements": [], "relationships": []}


def test_propose_delta_rejects_an_option_missing_elements_or_relationships(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = '{"options": [{"elements": []}]}'

    with pytest.raises(DeltaProposalError, match="elements.*relationships"):
        propose_delta("suggest something")


def test_propose_delta_passes_the_convention_rules_to_the_llm(configured_fake_llm: FakeCompletion) -> None:
    rules = [{"id": "conv-example", "kind": "naming", "scope": ["*"]}]

    propose_delta("suggest something", rules=rules)

    system = configured_fake_llm.calls[0]["messages"][0]["content"]
    assert "conv-example | naming | scope=['*']" in system


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


def test_propose_delta_gives_the_llm_the_existing_relationship_graph(configured_fake_llm: FakeCompletion) -> None:
    propose_delta(
        "what connects to role-sa?",
        relationships=[("Realization", "fn-solution-modelling", "cap-reusable-architecture", "")],
    )

    system = configured_fake_llm.calls[0]["messages"][0]["content"]
    assert "Existing relationships:" in system
    assert "Realization | fn-solution-modelling | cap-reusable-architecture | " in system


def test_propose_delta_parses_a_proposed_view(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = (
        '{"elements": [], "relationships": [],'
        ' "views": [{"name": "Context Sweep", "context": ["modelling-specification"],'
        ' "include_types": ["ApplicationFunction"]}]}'
    )

    result = propose_delta("add a view scoped to context modelling-specification")

    assert result["views"] == [
        {"name": "Context Sweep", "context": ["modelling-specification"], "include_types": ["ApplicationFunction"]}
    ]


def test_propose_delta_defaults_views_to_empty_when_the_llm_omits_the_key(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = '{"elements": [], "relationships": []}'

    result = propose_delta("add a function")

    assert result["views"] == []


def test_assign_missing_view_ids_leaves_an_explicit_id_and_diagram_alone() -> None:
    result = assign_missing_view_ids([{"name": "X", "id": "view-explicit", "diagram": "layered/explicit"}], set())

    assert result == [{"name": "X", "id": "view-explicit", "diagram": "layered/explicit"}]


def test_assign_missing_view_ids_slugifies_the_name_and_derives_a_diagram_path() -> None:
    result = assign_missing_view_ids([{"name": "Context Sweep!"}], set())

    assert result[0]["id"] == "view-context-sweep"
    assert result[0]["diagram"] == "context-sweep"


def test_assign_missing_view_ids_deduplicates_against_existing_ids() -> None:
    result = assign_missing_view_ids([{"name": "X"}], {"view-x"})

    assert result[0]["id"] == "view-x-2"


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


def test_propose_delta_parses_a_view_membership_edit(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = (
        '{"elements": [], "relationships": [],'
        ' "view_membership_edits": [{"view_id": "view-capability", "add": ["role-ea"], "remove": []}]}'
    )

    result = propose_delta("add role-ea to the capability map")

    assert result["view_membership_edits"] == [{"view_id": "view-capability", "add": ["role-ea"], "remove": []}]


def test_propose_delta_defaults_view_membership_edits_to_empty_when_the_llm_omits_the_key(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = '{"elements": [], "relationships": []}'

    result = propose_delta("add a function")

    assert result["view_membership_edits"] == []


def test_resolve_unknown_members_repoints_a_misspelt_id_and_reports_it() -> None:
    edits = [{"view_id": "view-capability", "add": ["assess-drfit-debt"], "remove": ["role-ea"]}]

    resolved, notes = resolve_unknown_members(edits, _KNOWN)

    assert resolved[0]["add"] == ["assess-drift-debt"]
    assert resolved[0]["remove"] == ["role-ea"]
    assert len(notes) == 1
    assert "assess-drfit-debt" in notes[0]


def test_resolve_unknown_members_leaves_a_weak_or_ambiguous_match_for_validation() -> None:
    edits = [{"view_id": "view-capability", "add": ["something-unrelated"], "remove": []}]

    resolved, notes = resolve_unknown_members(edits, _KNOWN)

    assert resolved == edits
    assert notes == []


def test_propose_delta_parses_element_edits_removals_and_relationship_removals(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = (
        '{"elements": [], "relationships": [],'
        ' "element_edits": [{"id": "role-ea", "name": "Enterprise Architect (Renamed)"}],'
        ' "element_removals": ["assess-drift-debt"],'
        ' "relationship_removals": [{"type": "Association", "source": "assess-drift-debt",'
        ' "target": "goal-frictionless-architecture"}]}'
    )

    result = propose_delta("rename role-ea and remove assess-drift-debt")

    assert result["element_edits"] == [{"id": "role-ea", "name": "Enterprise Architect (Renamed)"}]
    assert result["element_removals"] == ["assess-drift-debt"]
    assert result["relationship_removals"] == [
        {"type": "Association", "source": "assess-drift-debt", "target": "goal-frictionless-architecture"}
    ]


def test_propose_delta_defaults_the_new_edit_removal_keys_to_empty_when_the_llm_omits_them(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = '{"elements": [], "relationships": []}'

    result = propose_delta("add a function")

    assert result["element_edits"] == []
    assert result["element_removals"] == []
    assert result["relationship_removals"] == []


def test_resolve_unknown_element_edits_repoints_a_misspelt_id_and_reports_it() -> None:
    edits = [{"id": "assess-drfit-debt", "name": "New Name"}]

    resolved, notes = resolve_unknown_element_edits(edits, _KNOWN)

    assert resolved[0]["id"] == "assess-drift-debt"
    assert resolved[0]["name"] == "New Name"
    assert len(notes) == 1
    assert "assess-drfit-debt" in notes[0]


def test_resolve_unknown_element_edits_leaves_a_weak_or_ambiguous_match_for_validation() -> None:
    edits = [{"id": "something-unrelated", "name": "X"}]

    resolved, notes = resolve_unknown_element_edits(edits, _KNOWN)

    assert resolved == edits
    assert notes == []


def test_resolve_unknown_element_removals_repoints_a_misspelt_id_and_reports_it() -> None:
    removals = ["assess-drfit-debt"]

    resolved, notes = resolve_unknown_element_removals(removals, _KNOWN)

    assert resolved == ["assess-drift-debt"]
    assert len(notes) == 1
    assert "assess-drfit-debt" in notes[0]


def test_resolve_unknown_element_removals_leaves_a_weak_or_ambiguous_match_for_validation() -> None:
    removals = ["something-unrelated"]

    resolved, notes = resolve_unknown_element_removals(removals, _KNOWN)

    assert resolved == removals
    assert notes == []
