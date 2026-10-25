"""Contract tests for `POST /authoring/sessions/{id}/propose` (contracts/api.md, US1).

Mocks `litellm.completion` via the autouse `configured_fake_llm` fixture (tests/
conftest.py) -- never a live network (plan.md Testing).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from modelling_specification.app import app
from support.fake_llm import FakeCompletion

client = TestClient(app)


def _new_session() -> str:
    session_id: str = client.post("/authoring/sessions").json()["session_id"]
    return session_id


def test_propose_a_clean_delta_returns_validated_with_an_assigned_element_id(
    configured_fake_llm: FakeCompletion,
) -> None:
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "Propose Clean Test Function"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "validated"
    assert isinstance(body["delta_id"], str)
    assert body["delta_id"]
    (element,) = body["elements"]
    assert element["type"] == "ApplicationFunction"
    assert element["id"] == "applicationfunction-propose-clean-test-function"
    assert body["relationships"] == []


def test_propose_a_flagged_delta_returns_findings_and_does_not_write_the_model(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-flagged-test", "name": "Flagged"}],'
        ' "relationships": [{"type": "Composition", "source": "sub-modelling", "target": "fn-flagged-test"}]}'
    )
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "propose a bad shape"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "flagged"
    assert body["validation_result"]["clean"] is False
    assert any(f["check"] == "illegal_relationship" for f in body["validation_result"]["findings"])
    assert body["duplicates"] == []
    assert body["pattern_suggestions"] == []


def test_propose_returns_502_when_the_llm_call_fails(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.error = ConnectionError("connection refused")
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "add a function"})

    assert response.status_code == 502


def test_propose_against_an_unknown_session_returns_404(configured_fake_llm: FakeCompletion) -> None:
    response = client.post("/authoring/sessions/unknown-session/propose", json={"request": "add a function"})

    assert response.status_code == 404


def test_propose_repoints_a_misspelt_relationship_endpoint_and_reports_it(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = (
        '{"elements": [], "relationships": [{"type": "Association", "source": "role-sa", "target": "role-eaa"}]}'
    )
    session_id = _new_session()

    body = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "link"}).json()

    assert body["relationships"][0]["target"] == "role-ea"
    assert any("role-eaa" in n for n in body["notes"])


def test_propose_an_empty_delta_says_nothing_was_proposed(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = '{"elements": [], "relationships": []}'
    session_id = _new_session()

    body = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "rename role-ea"}).json()

    assert any("only add" in n for n in body["notes"])


def test_propose_reusing_an_existing_id_explains_that_edits_are_unsupported(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "BusinessRole", "id": "role-ea", "name": "Chief EA"}], "relationships": []}'
    )
    session_id = _new_session()

    body = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "rename role-ea"}).json()

    (finding,) = body["validation_result"]["findings"]
    assert "cannot edit" in finding["proposed_fix"]


def test_propose_again_amends_the_still_pending_delta_instead_of_starting_a_new_one(
    configured_fake_llm: FakeCompletion,
) -> None:
    # FR-015: a later request touching the pending delta amends/extends it rather
    # than starting an independent one.
    session_id = _new_session()
    first = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "Propose Amend Test One"}).json()
    assert first["status"] == "validated"

    second = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "Propose Amend Test Two"}).json()

    assert second["delta_id"] == first["delta_id"]
    names = {e["name"] for e in second["elements"]}
    assert names == {"Propose Amend Test One", "Propose Amend Test Two"}


def test_propose_an_element_with_an_unknown_type_is_a_build_error(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "NotARealArchimateType", "id": "fn-bad-type-test", "name": "Bad"}],'
        ' "relationships": []}'
    )
    session_id = _new_session()

    body = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "add a bogus type"}).json()

    assert body["status"] == "flagged"
    assert any(f["check"] == "build_error" for f in body["validation_result"]["findings"])


def test_propose_a_suggestion_request_returns_options_with_rationale_and_validation(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = (
        '{"options": ['
        '{"rationale": "fits an existing capability", "convention_refs": [],'
        ' "elements": [{"type": "ApplicationFunction", "name": "Suggested Option One"}], "relationships": []},'
        '{"rationale": "an alternative shape", "convention_refs": [],'
        ' "elements": [{"type": "ApplicationFunction", "name": "Suggested Option Two"}], "relationships": []}'
        "]}"
    )
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "what should I do about X?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "options"
    assert body["delta_id"] is None
    assert len(body["options"]) == 2
    first = body["options"][0]
    assert first["rationale"] == "fits an existing capability"
    assert first["elements"][0]["name"] == "Suggested Option One"
    assert first["elements"][0]["id"]
    assert first["validation_result"]["clean"] is True


def test_propose_select_turns_the_chosen_option_into_a_pending_delta(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = (
        '{"options": ['
        '{"rationale": "A", "convention_refs": [], "elements": [{"type": "ApplicationFunction", "name": "Select Test"}],'
        ' "relationships": []},'
        '{"rationale": "B", "convention_refs": [], "elements": [], "relationships": []}'
        "]}"
    )
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "what should I do about X?"})

    response = client.post(f"/authoring/sessions/{session_id}/propose/select", json={"option_index": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "validated"
    assert isinstance(body["delta_id"], str) and body["delta_id"]
    assert body["elements"][0]["name"] == "Select Test"


def test_propose_select_out_of_range_index_returns_409(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = '{"options": [{"elements": [], "relationships": []}]}'
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "what should I do about X?"})

    response = client.post(f"/authoring/sessions/{session_id}/propose/select", json={"option_index": 5})

    assert response.status_code == 409


def test_propose_select_without_a_pending_proposal_returns_409(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose/select", json={"option_index": 0})

    assert response.status_code == 409


def test_propose_select_against_an_unknown_session_returns_404(configured_fake_llm: FakeCompletion) -> None:
    response = client.post("/authoring/sessions/unknown-session/propose/select", json={"option_index": 0})

    assert response.status_code == 404


def test_propose_shows_a_plain_text_llm_reply_as_a_message_and_creates_no_delta(
    configured_fake_llm: FakeCompletion,
) -> None:
    configured_fake_llm.content = "A good goal would be 'Reconcile drift continuously'. Shall I add it?"
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "suggest a goal"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "message"
    assert "Reconcile drift continuously" in body["message"]
    assert body["delta_id"] is None
    assert body["elements"] == []
    assert body["relationships"] == []
