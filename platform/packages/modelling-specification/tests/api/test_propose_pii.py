"""Contract tests for the PII/PHI flag-for-review round trip on
`POST /authoring/sessions/{id}/propose` + `POST .../propose/resolve-pii`
(ADR-0014 amendment, `conversational-authoring` context).

A detected match must pause `propose` -- never send the LLM either the original or
the auto-redacted text unasked -- until the architect resolves it via
`resolve-pii`. Mocks `litellm.completion` via the autouse `configured_fake_llm`
fixture (tests/conftest.py) -- never a live network (plan.md Testing).
"""

from __future__ import annotations

import sys

import pytest
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
    # A real detection -- the response must not claim detection failed.
    assert body["detection_failed"] is False


def test_propose_with_a_detector_engine_error_flags_detection_as_failed(
    configured_fake_llm: FakeCompletion, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The flagged-for-review response for the synthetic engine-error match
    # (research.md R6) must tell the architect detection failed, not imply a real
    # PII/PHI match was found.
    def _raise(_text: str) -> None:
        raise RuntimeError("detector engine unavailable")

    monkeypatch.setattr(sys.modules["pii_gateway.scrub"], "analyze", _raise)
    session_id = _new_session()

    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pii_review_required"
    assert body["detection_failed"] is True
    assert configured_fake_llm.calls == []


def test_resolve_pii_allow_after_a_detector_engine_error_is_rejected_and_pending_survives(
    configured_fake_llm: FakeCompletion, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Decided (2026-11-05): ALLOW after an engine error is rejected outright --
    # nothing inspected this text, so there is no real match for the architect to
    # judge and allow. The rejection must not clear the pending confirmation: the
    # architect can still redact or edit, and must not reach the LLM via allow.
    def _raise(_text: str) -> None:
        raise RuntimeError("detector engine unavailable")

    monkeypatch.setattr(sys.modules["pii_gateway.scrub"], "analyze", _raise)
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "allow"})

    assert 400 <= response.status_code < 500
    assert configured_fake_llm.calls == []
    detail = response.json()["detail"].lower()
    assert "detect" in detail or "engine" in detail

    # The pending confirmation is still there -- redact can still resolve it.
    follow_up = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "redact"})
    assert follow_up.status_code == 200
    sent_content = configured_fake_llm.calls[0]["messages"][-1]["content"]
    assert "Jane Doe" not in sent_content
    assert "jane@example.com" not in sent_content


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


def test_resolve_pii_redact_strips_the_whole_text_after_a_detector_engine_error(
    configured_fake_llm: FakeCompletion, monkeypatch: pytest.MonkeyPatch
) -> None:
    # pii-gateway's fail-closed synthetic match for a detector-engine error is a
    # zero-length span (research.md R6) -- `scrub_or_require_review`/`resolve_pii`
    # must not let any of the original request text leak through on REDACT just
    # because the span itself covered nothing.
    def _raise(_text: str) -> None:
        raise RuntimeError("detector engine unavailable")

    monkeypatch.setattr(sys.modules["pii_gateway.scrub"], "analyze", _raise)

    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "redact"})

    assert response.status_code == 200
    sent_content = configured_fake_llm.calls[0]["messages"][-1]["content"]
    assert "Jane Doe" not in sent_content
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


def test_resolve_pii_allow_with_a_plain_text_llm_reply_returns_a_message(configured_fake_llm: FakeCompletion) -> None:
    # Resolving a flagged match can still land on a plain-text LLM reply (not
    # options), same as a clean `propose` call would -- same "message" shape,
    # no delta created.
    configured_fake_llm.content = "I'm not sure what you mean -- could you rephrase that?"
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "allow"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "message"
    assert "rephrase" in body["message"]
    assert body["delta_id"] is None
    assert body["elements"] == []
    assert body["relationships"] == []


def test_resolve_pii_allow_returns_502_when_the_llm_call_fails(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.error = ConnectionError("connection refused")
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    response = client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "allow"})

    assert response.status_code == 502
    assert "connection refused" not in response.text
    assert "server log" in response.json()["detail"]


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


def test_a_flagged_request_stays_out_of_later_turns_until_resolved(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "add an application function fn-example"})

    assert "jane@example.com" not in str(configured_fake_llm.calls[-1]["messages"])


def test_only_the_redacted_text_reaches_later_turns(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})
    client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "redact"})

    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": "add an application function fn-example"})

    later_turn = configured_fake_llm.calls[-1]["messages"]
    assert len(later_turn) == 4
    assert "jane@example.com" not in str(later_turn)


def test_a_resolved_request_gets_the_same_grounding_as_any_other(configured_fake_llm: FakeCompletion) -> None:
    session_id = _new_session()
    client.post(f"/authoring/sessions/{session_id}/propose", json={"request": _PII_REQUEST})

    client.post(f"/authoring/sessions/{session_id}/propose/resolve-pii", json={"resolution": "redact"})

    system = configured_fake_llm.calls[-1]["messages"][0]["content"]
    for block in ("Existing elements:", "Existing contexts:", "Existing views:", "Existing relationships:"):
        assert block in system
