"""Settings router contract: GET /state, PUT /contexts/{context_id} (contracts/scrub.md)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pii_gateway import scrub
from pii_gateway.router import create_settings_router

_CONTEXTS = ["spec-generator", "governance-eval", "conversational-authoring"]


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(create_settings_router(_CONTEXTS))
    return TestClient(app)


def test_get_state_returns_active_categories_and_failure_mode_per_context() -> None:
    response = _client().get("/settings/pii-gateway/state")

    assert response.status_code == 200
    body = response.json()
    contexts = {c["context"]: c for c in body["contexts"]}
    assert set(contexts) == set(_CONTEXTS)
    assert contexts["conversational-authoring"]["failure_mode"] == "flagged_for_review"
    assert contexts["spec-generator"]["failure_mode"] == "redacted_and_proceeded"


def test_put_context_updates_config_and_next_scrub_call_applies_it() -> None:
    client = _client()

    response = client.put(
        "/settings/pii-gateway/contexts/spec-generator",
        json={"active_categories": ["US_SSN"], "failure_mode": "flagged_for_review"},
    )
    assert response.status_code == 200

    result = scrub("My SSN is 234-56-7890.", context="spec-generator")
    assert result.action == "flagged_for_review"


def test_turning_off_a_category_stops_it_being_flagged() -> None:
    client = _client()

    response = client.put(
        "/settings/pii-gateway/contexts/spec-generator",
        json={"active_categories": ["EMAIL_ADDRESS"], "failure_mode": "redacted_and_proceeded"},
    )
    assert response.status_code == 200

    result = scrub("Contact Jane Doe about the proposal.", context="spec-generator")

    # PERSON is no longer active for this context, and the only PII present was a name.
    assert all(match.category != "PERSON" for match in result.matches)


def test_settings_page_serves_html() -> None:
    response = _client().get("/settings/pii-gateway")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/settings/pii-gateway" in response.text


def test_unknown_context_returns_404() -> None:
    client = _client()

    response = client.put(
        "/settings/pii-gateway/contexts/does-not-exist",
        json={"active_categories": [], "failure_mode": "redacted_and_proceeded"},
    )

    assert response.status_code == 404
