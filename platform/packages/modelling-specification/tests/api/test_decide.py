"""Contract tests for `POST /authoring/sessions/{id}/deltas/{id}/decide` -- the
`apply` action on a clean delta (US1, contracts/api.md). Runs against `isolated_model`
(tests/api/conftest.py) so it never writes to the committed model.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from modelling_specification.app import app
from support.fake_llm import FakeCompletion

client = TestClient(app)


def _propose_clean_delta(request: str = "Decide Apply Test Function") -> tuple[str, str]:
    session_id = client.post("/authoring/sessions").json()["session_id"]
    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": request})
    return session_id, response.json()["delta_id"]


def test_decide_apply_writes_the_delta_and_marks_it_applied(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose_clean_delta()

    response = client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Transition"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["delta_id"] == delta_id
    assert body["status"] == "applied"
    assert body["state_classification"] == "Transition"
    assert body["override_decision_id"] is None
    elements_text = (isolated_model / "elements.yaml").read_text()
    assert "applicationfunction-decide-apply-test-function" in elements_text


def test_decide_against_an_unknown_delta_returns_409(configured_fake_llm: FakeCompletion, isolated_model: Path) -> None:
    session_id = client.post("/authoring/sessions").json()["session_id"]

    response = client.post(f"/authoring/sessions/{session_id}/deltas/unknown-delta/decide", json={"action": "apply"})

    assert response.status_code == 409


def test_decide_apply_twice_returns_409_the_second_time(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose_clean_delta()
    client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Transition"},
    )

    response = client.post(f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide", json={"action": "apply"})

    assert response.status_code == 409


def test_decide_apply_on_a_flagged_delta_returns_409(configured_fake_llm: FakeCompletion, isolated_model: Path) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-flagged-decide-test", "name": "Flagged"}],'
        ' "relationships": [{"type": "Composition", "source": "sub-modelling", "target": "fn-flagged-decide-test"}]}'
    )
    session_id = client.post("/authoring/sessions").json()["session_id"]
    delta_id = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "propose a bad shape"}).json()[
        "delta_id"
    ]

    response = client.post(f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide", json={"action": "apply"})

    assert response.status_code == 409


def test_decide_apply_inlines_a_render_when_auto_render_is_configured(
    configured_fake_llm: FakeCompletion, isolated_model: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modelling_specification.router.rendering.resolve_view_request",
        lambda object_id, description: {"resolved_view_id": "view-fake", "ambiguous_candidates": []},
    )
    monkeypatch.setattr(
        "modelling_specification.router.rendering.render_single_view", lambda view_id: "<svg>fake</svg>"
    )
    client.put("/authoring/config", json={"auto_render": True})
    try:
        session_id, delta_id = _propose_clean_delta("Auto Render Test Function")

        response = client.post(
            f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
            json={"action": "apply", "state_classification": "Transition"},
        )

        assert response.json()["render"] == {"view_id": "view-fake", "svg": "<svg>fake</svg>"}
    finally:
        client.put("/authoring/config", json={"auto_render": False})


def test_decide_apply_omits_render_when_auto_render_is_off(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, delta_id = _propose_clean_delta("No Auto Render Test Function")

    response = client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Transition"},
    )

    assert response.json()["status"] == "applied"
    assert "render" not in response.json()
