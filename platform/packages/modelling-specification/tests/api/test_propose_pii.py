"""Contract tests for the PII/PHI flag-for-review round trip on
`POST /authoring/sessions/{id}/propose` + `POST .../propose/resolve-pii`
(ADR-0014 amendment, `conversational-authoring` context).

A detected match must pause `propose` -- never send the LLM either the original or
the auto-redacted text unasked -- until the architect resolves it via
`resolve-pii`. Mocks `litellm.completion` via the autouse `configured_fake_llm`
fixture (tests/conftest.py) -- never a live network (plan.md Testing).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from modelling_specification.app import app
from support.fake_llm import FakeCompletion

client = TestClient(app)

_PII_REQUEST = "Add an application function for Jane Doe (jane@example.com) to review."


def _new_session() -> str:
    session_id: str = client.post("/authoring/sessions").json()["session_id"]
    return session_id


def test_propose_with_pii_is_flagged_for_review_and_never_reaches_the_llm(
    configured_fake_llm: FakeCompletion,
) -> None:
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pii_review_required"
    assert body["pii_review_required"] is True
    assert body["delta_id"] is None
    assert body["elements"] == []
    assert body["relationships"] == []
    assert body["matches"]
    assert configured_fake_llm.calls == []


def test_resolve_pii_allow_proceeds_with_the_original_text(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "allow"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "validated"
    sent_content = configured_fake_llm.calls[0]["messages"][-1]["content"]
    assert "Jane Doe" in sent_content
    assert "jane@example.com" in sent_content


def test_resolve_pii_redact_proceeds_with_the_redacted_text(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "redact"})

    assert response.status_code == 200
    sent_content = configured_fake_llm.calls[0]["messages"][-1]["content"]
    assert "jane@example.com" not in sent_content


def test_resolve_pii_edit_with_a_clean_replacement_proceeds_with_it(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(
        f"/authoring/sessions/{session_id}/propose/resolve-pii",
        json={"resolution": "edit", "edited_text": "Add an application function for the reviewer to review."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "validated"
    sent_content = configured_fake_llm.calls[0]["messages"][-1]["content"]
    assert sent_content == "Add an application function for the reviewer to review."
    assert "Jane Doe" not in sent_content
    assert "jane@example.com" not in sent_content


def test_resolve_pii_edit_with_a_still_flagged_replacement_is_re_flagged_not_sent(
    configured_fake_llm: FakeCompletion,
) -> None:
    # The architect's own replacement text is never assumed clean -- it is
    # re-scrubbed under the same context, and a still-sensitive edit is re-flagged
    # exactly like a fresh `propose` call would be, never sent on unscrubbed.
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(
        f"/authoring/sessions/{session_id}/propose/resolve-pii",
        json={"resolution": "edit", "edited_text": "Still for Jane Doe (jane@example.com) to review."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pii_review_required"
    assert body["pii_review_required"] is True
    assert body["delta_id"] is None
    assert body["matches"]
    assert configured_fake_llm.calls == []

    # The re-flagged match can itself be resolved -- the pending state was
    # replaced, not left stale or doubled up.
    follow_up = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "allow"})
    assert follow_up.status_code == 200
    assert follow_up.json()["status"] == "validated"


def test_resolve_pii_edit_without_edited_text_returns_400(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "edit"})

    assert response.status_code == 400
    assert configured_fake_llm.calls == []


def test_resolve_pii_without_a_pending_match_returns_409(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "allow"})

    assert response.status_code == 409


def test_resolve_pii_against_an_unknown_session_returns_404(configured_fake_llm: FakeCompletion) -> None:
    response = client.post("/authoring/sessions/unknown-session/propose/resolve-pii", json={"resolution": "allow"})

    assert response.status_code == 404


def test_a_fresh_propose_call_supersedes_a_stale_pending_pii_review(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    # The architect ignores the flagged match and asks something else instead.
    second = client.post(
        f"/authoring/sessions/{session_id}/propose", json={"request": "add an application function fn-example"}
    ).json()
    assert second["status"] == "validated"

    # The superseded match can no longer be resolved.
    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "allow"})
    assert response.status_code == 409
