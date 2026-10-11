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
    assert isinstance(body["delta_id"], str) and body["delta_id"]
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
