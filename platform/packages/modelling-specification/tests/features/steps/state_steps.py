"""Step definitions for the US3 (state classification) behave scenarios."""

from __future__ import annotations

from behave import then, when
from behave.runner import Context


@when('the architect applies the change as state "{state}"')
def step_apply_with_state(context: Context, state: str) -> None:
    context.decide_response = context.client.post(
        f"/authoring/sessions/{context.session_id}/deltas/{context.delta_id}/decide",
        json={"action": "apply", "state_classification": state},
    )
    assert context.decide_response.status_code == 200, context.decide_response.text


@when("the architect applies the change without specifying its state")
def step_apply_without_state(context: Context) -> None:
    context.decide_response = context.client.post(
        f"/authoring/sessions/{context.session_id}/deltas/{context.delta_id}/decide", json={"action": "apply"}
    )


@then('asking the agent what state the change belongs to answers "{state}"')
def step_query_state(context: Context, state: str) -> None:
    response = context.client.get(f"/authoring/sessions/{context.session_id}/deltas/{context.delta_id}/state")
    assert response.status_code == 200, response.text
    assert response.json()["value"] == state
