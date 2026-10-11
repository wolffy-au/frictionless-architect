"""Step definitions for the conversational-authoring behave scenarios (US1/US2/US3)."""

from __future__ import annotations

import json

from behave import given, step, then, when
from behave.runner import Context


@given("a new authoring session")
def step_new_session(context: Context) -> None:
    context.session_id = context.client.post("/authoring/sessions").json()["session_id"]


@given('an architect describes a valid, unambiguous model change "{request}"')
def step_describe_change(context: Context, request: str) -> None:
    context.fake_llm.content = json.dumps(
        {"elements": [{"type": "ApplicationFunction", "name": request}], "relationships": []}
    )


@given('an architect describes a valid, unambiguous model change that extends "{existing_id}"')
def step_describe_change_extending(context: Context, existing_id: str) -> None:
    # A new relationship between two elements the model already has -- proves FR-012's
    # "affected element(s)" covers a relationship-only delta too (router.py's
    # `_first_affected_object_id`), not only a brand-new element.
    context.fake_llm.content = json.dumps(
        {"elements": [], "relationships": [{"type": "Association", "source": "role-sa", "target": existing_id}]}
    )
    # Stub view resolution/rendering: which real views an existing element resolves
    # to is a property of the live, independently-evolving model (out of this
    # scenario's control), not something this wiring test should depend on.
    from modelling_specification import rendering

    original_resolve = rendering.resolve_view_request
    original_render = rendering.render_single_view
    rendering.resolve_view_request = lambda object_id, description: {
        "resolved_view_id": "view-fake",
        "ambiguous_candidates": [],
    }
    rendering.render_single_view = lambda view_id: "<svg>fake</svg>"
    context.add_cleanup(setattr, rendering, "resolve_view_request", original_resolve)
    context.add_cleanup(setattr, rendering, "render_single_view", original_render)


@given("rendering is configured to happen automatically")
def step_auto_render_on(context: Context) -> None:
    context.client.put("/authoring/config", json={"auto_render": True})


@given("rendering is configured to happen on request")
def step_auto_render_off(context: Context) -> None:
    context.client.put("/authoring/config", json={"auto_render": False})


@step("the agent proposes the delta")
def step_propose(context: Context) -> None:
    context.propose_response = context.client.post(
        f"/authoring/sessions/{context.session_id}/propose", json={"request": "the architect's request"}
    )
    context.delta_id = context.propose_response.json()["delta_id"]


@then("it validates cleanly against the metamodel and configured conventions")
def step_validates_cleanly(context: Context) -> None:
    body = context.propose_response.json()
    assert body["status"] == "validated", body


@step("the architect applies the change")
def step_apply(context: Context) -> None:
    context.decide_response = context.client.post(
        f"/authoring/sessions/{context.session_id}/deltas/{context.delta_id}/decide",
        json={"action": "apply", "state_classification": "Transition"},
    )
    assert context.decide_response.status_code == 200, context.decide_response.text


@then("the change is written to the model")
def step_written(context: Context) -> None:
    assert context.decide_response.json()["status"] == "applied"


@then("the corresponding diagram renders immediately without the architect asking")
def step_renders_automatically(context: Context) -> None:
    body = context.decide_response.json()
    assert "render" in body, body
    assert "</svg>" in body["render"]["svg"]


@when("the architect asks to see the affected element")
def step_asks_to_see(context: Context) -> None:
    context.render_response = context.client.get("/authoring/render", params={"object_id": "view-fake"})


@then("the corresponding diagram renders immediately, reflecting the current state of the conversation")
def step_renders_on_request(context: Context) -> None:
    assert context.render_response.status_code == 200, context.render_response.text
    assert "</svg>" in context.render_response.json()["svg"]
