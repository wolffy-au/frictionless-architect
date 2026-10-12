"""Contract tests for US3 state classification (FR-009/FR-010, contracts/api.md)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from modelling_specification.app import app
from support.fake_llm import FakeCompletion

client = TestClient(app)


def _propose(request: str = "State Classification Test Function") -> tuple[str, str]:
    session_id = client.post("/authoring/sessions").json()["session_id"]
    delta_id = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": request}).json()["delta_id"]
    return session_id, delta_id


def test_apply_without_state_classification_applies_with_no_state(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose()

    response = client.post(f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide", json={"action": "apply"})

    assert response.status_code == 200
    assert response.json()["state_classification"] is None


def test_apply_with_an_unrecognised_state_returns_422(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose()

    response = client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Someday"},
    )

    assert response.status_code == 422
    assert response.json() == {"needs": "state_classification"}


def test_apply_with_state_classification_applies_and_records_it(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose()

    response = client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Transition"},
    )

    assert response.status_code == 200
    assert response.json()["state_classification"] == "Transition"


def test_apply_with_an_invalid_state_classification_value_is_also_422(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose()

    response = client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Nonsense"},
    )

    assert response.status_code == 422


def test_get_state_after_apply_returns_the_recorded_classification(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose()
    client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Target"},
    )

    response = client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/state")

    assert response.status_code == 200
    body = response.json()
    assert body["value"] == "Target"
    assert body["applies_to"]


def test_get_state_for_an_unapplied_delta_is_404(configured_fake_llm: FakeCompletion, isolated_model: Path) -> None:
    session_id, delta_id = _propose()

    response = client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/state")

    assert response.status_code == 404
