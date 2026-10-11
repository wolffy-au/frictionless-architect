"""Step definitions for the US2 (reject/duplicate/pattern/override) behave scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from behave import given, step, then
from behave.runner import Context


@given("an architect describes a change that violates the metamodel")
def step_describe_metamodel_violation(context: Context) -> None:
    context.fake_llm.content = json.dumps(
        {
            "elements": [{"type": "ApplicationFunction", "id": "fn-behave-metamodel-violation", "name": "X"}],
            "relationships": [
                {"type": "Composition", "source": "sub-modelling", "target": "fn-behave-metamodel-violation"}
            ],
        }
    )


@given("an architect describes a change that resembles an existing element")
def step_describe_duplicate(context: Context) -> None:
    context.fake_llm.content = json.dumps(
        {
            "elements": [
                {
                    "type": "ApplicationComponent",
                    "id": "sub-modelling-behave-dup",
                    "name": "Modelling & Specification",
                }
            ],
            "relationships": [],
        }
    )


@given("an established intermediary-element pattern for a relationship shape")
def step_establish_pattern(context: Context) -> None:
    from modelling_specification.validation import conventions

    rule: dict[str, Any] = {
        "id": "conv-interposed-behave-test",
        "kind": "interposed-pattern",
        "scope": ["*"],
        "params": {
            "source_type": "ApplicationComponent",
            "relationship_type": "Serving",
            "target_type": "BusinessRole",
            "intermediary_types": ["ApplicationService"],
        },
        "enabled": True,
    }
    original = conventions.load_rules
    conventions.load_rules = lambda path=None: [rule]
    context.add_cleanup(setattr, conventions, "load_rules", original)


@given("an architect describes a direct relationship matching that shape")
def step_describe_direct_relationship(context: Context) -> None:
    context.fake_llm.content = json.dumps(
        {"elements": [], "relationships": [{"type": "Serving", "source": "sub-modelling", "target": "role-ea"}]}
    )


@given("an architect describes a change that violates a configured convention")
def step_describe_convention_violation(context: Context) -> None:
    context.fake_llm.content = json.dumps(
        {
            "elements": [{"type": "Capability", "id": "cap-behave-override-test", "name": "Override Test Capability"}],
            "relationships": [
                {"type": "Realization", "source": "cap-behave-override-test", "target": "req-auto-spec-generation"}
            ],
        }
    )


@then("the agent rejects the change with a specific, actionable explanation")
def step_rejected_with_explanation(context: Context) -> None:
    body = context.propose_response.json()
    assert body["status"] == "flagged", body
    assert body["validation_result"]["clean"] is False
    finding = body["validation_result"]["findings"][0]
    assert finding["detail"]
    assert finding["proposed_fix"]


@then("no change is written to the model")
def step_nothing_written(context: Context) -> None:
    elements_path = Path(context.model_tmpdir.name) / "elements.yaml"
    text = elements_path.read_text()
    for element in context.propose_response.json().get("elements", []):
        if element.get("id"):
            assert element["id"] not in text


@then("the agent surfaces the duplicate candidate")
def step_surfaces_duplicate(context: Context) -> None:
    body = context.propose_response.json()
    assert body["status"] == "flagged", body
    assert body["duplicates"], body


@step("the architect rejects the duplicate")
def step_reject_duplicate(context: Context) -> None:
    context.decide_response = context.client.post(
        f"/authoring/sessions/{context.session_id}/deltas/{context.delta_id}/decide",
        json={"action": "reject", "duplicate_decision": "reject"},
    )
    assert context.decide_response.status_code == 200, context.decide_response.text


@then("the agent flags the pattern shortcut and explains the established pattern")
def step_flags_pattern(context: Context) -> None:
    body = context.propose_response.json()
    assert body["pattern_suggestions"], body
    assert body["pattern_suggestions"][0]["established_pattern"]["intermediary_types"]


@step("the architect keeps the direct form anyway")
def step_keep_direct(context: Context) -> None:
    context.decide_response = context.client.post(
        f"/authoring/sessions/{context.session_id}/deltas/{context.delta_id}/decide",
        json={"action": "keep-direct", "state_classification": "Transition"},
    )
    assert context.decide_response.status_code == 200, context.decide_response.text


@step("the architect overrides the objection with a rationale")
def step_override_with_rationale(context: Context) -> None:
    context.decide_response = context.client.post(
        f"/authoring/sessions/{context.session_id}/deltas/{context.delta_id}/decide",
        json={
            "action": "override",
            "rationale": "legacy naming predates the convention",
            "state_classification": "Transition",
        },
    )
    assert context.decide_response.status_code == 200, context.decide_response.text


@then("the override is recorded as a traceable decision")
def step_override_recorded(context: Context) -> None:
    body = context.decide_response.json()
    assert body["override_decision_id"] is not None
    adr_files = list(Path(context.adr_tmpdir.name).glob("*.md"))
    assert len(adr_files) == 1
    text = adr_files[0].read_text()
    assert "Status:** Proposed" in text
    assert "legacy naming predates the convention" in text
