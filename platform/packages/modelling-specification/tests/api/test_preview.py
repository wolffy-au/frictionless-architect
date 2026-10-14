"""Contract tests for `GET /authoring/sessions/{id}/deltas/{id}/preview`: render a
pending delta in a view before anything is written."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from modelling_specification import model_io, rendering
from modelling_specification.app import app
from support.fake_llm import FakeCompletion

client = TestClient(app)
VIEW = "view-gh108-conversational-authoring"


def _propose(fake: FakeCompletion, content: str) -> tuple[str, str]:
    fake.content = content
    session_id: str = client.post("/authoring/sessions").json()["session_id"]
    delta_id: str = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "x"}).json()["delta_id"]
    return session_id, delta_id


def test_preview_renders_the_pending_delta_and_writes_nothing(configured_fake_llm: FakeCompletion) -> None:
    before = (model_io.HERE / "elements.yaml").read_text() + (model_io.HERE / "relationships.yaml").read_text()
    session_id, delta_id = _propose(
        configured_fake_llm,
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-preview-probe", "name": "Preview Probe"}],'
        ' "relationships": [{"type": "Assignment", "source": "sub-modelling", "target": "fn-preview-probe"}]}',
    )

    response = client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview", params={"view_id": VIEW})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.headers["X-View-Id"] == VIEW
    assert "Probe" in response.text
    after = (model_io.HERE / "elements.yaml").read_text() + (model_io.HERE / "relationships.yaml").read_text()
    assert before == after
    assert not Path(model_io.HERE / "frictionless-architect.xml").read_text().count("Preview Probe")


def test_preview_resolves_the_view_from_an_existing_element_it_touches(configured_fake_llm: FakeCompletion) -> None:
    session_id, delta_id = _propose(
        configured_fake_llm,
        '{"elements": [], "relationships": [{"type": "Association", "source": "role-sa", "target": "role-ea"}]}',
    )

    response = client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview")

    assert response.status_code == 300
    assert VIEW in response.json()["ambiguous_candidates"]


def test_preview_resolves_the_view_from_a_touched_element_when_it_is_unambiguous(
    configured_fake_llm: FakeCompletion, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modelling_specification.router.rendering.resolve_view_request",
        lambda object_id, description: {"resolved_view_id": VIEW, "ambiguous_candidates": []},
    )
    session_id, delta_id = _propose(
        configured_fake_llm,
        '{"elements": [], "relationships": [{"type": "Association", "source": "role-sa", "target": "role-ea"}]}',
    )

    response = client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview")

    assert response.status_code == 200
    assert response.headers["X-View-Id"] == VIEW


def test_preview_with_an_explicit_but_unknown_view_id_is_a_404(configured_fake_llm: FakeCompletion) -> None:
    session_id, delta_id = _propose(
        configured_fake_llm,
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-preview-unknown-view", "name": "X"}],'
        ' "relationships": []}',
    )

    response = client.get(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview", params={"view_id": "not-a-real-view"}
    )

    assert response.status_code == 404
    assert "not-a-real-view" in response.json()["detail"]


def test_preview_maps_a_view_not_found_error_to_404(
    configured_fake_llm: FakeCompletion, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modelling_specification.router.rendering.render_candidate_view",
        lambda view_id, elements, relationships: (_ for _ in ()).throw(rendering.ViewNotFoundError("gone")),
    )
    session_id, delta_id = _propose(
        configured_fake_llm,
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-preview-view-not-found", "name": "X"}],'
        ' "relationships": []}',
    )

    response = client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview", params={"view_id": VIEW})

    assert response.status_code == 404
    assert "gone" in response.json()["detail"]


def test_preview_maps_a_preview_error_to_409(
    configured_fake_llm: FakeCompletion, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modelling_specification.router.rendering.render_candidate_view",
        lambda view_id, elements, relationships: (_ for _ in ()).throw(rendering.PreviewError("cannot assemble")),
    )
    session_id, delta_id = _propose(
        configured_fake_llm,
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-preview-preview-error", "name": "X"}],'
        ' "relationships": []}',
    )

    response = client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview", params={"view_id": VIEW})

    assert response.status_code == 409
    assert "cannot assemble" in response.json()["detail"]


def test_preview_without_a_view_or_touched_element_asks_for_one(configured_fake_llm: FakeCompletion) -> None:
    session_id, delta_id = _propose(
        configured_fake_llm, '{"elements": [{"type": "ApplicationFunction", "name": "Lonely"}], "relationships": []}'
    )

    assert client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview").status_code == 404


def test_preview_of_an_unknown_delta_is_a_404() -> None:
    session_id = client.post("/authoring/sessions").json()["session_id"]
    assert client.get(f"/authoring/sessions/{session_id}/deltas/nope/preview").status_code == 404


def test_preview_of_an_empty_delta_is_a_409(configured_fake_llm: FakeCompletion) -> None:
    session_id, delta_id = _propose(configured_fake_llm, '{"elements": [], "relationships": []}')
    assert client.get(f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview").status_code == 409
