"""Contract test for `POST /authoring/sessions` (contracts/api.md)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from modelling_specification.app import app

client = TestClient(app)


def test_create_session_returns_a_session_id() -> None:
    response = client.post("/authoring/sessions")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["session_id"], str)
    assert body["session_id"]


def test_each_call_issues_a_distinct_session_id() -> None:
    first = client.post("/authoring/sessions").json()["session_id"]
    second = client.post("/authoring/sessions").json()["session_id"]
    assert first != second


def test_llm_settings_router_is_mounted() -> None:
    response = client.get("/settings/llm")
    assert response.status_code == 200
