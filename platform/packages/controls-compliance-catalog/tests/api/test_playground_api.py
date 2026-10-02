"""Contract tests for the playground's HTTP seam (GH #76)."""

import json

from controls_compliance_catalog.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

SINGLE_CONTROL = {
    "id": "ac-2",
    "class": "SP800-53",
    "title": "Account Management",
    "parts": [
        {"id": "ac-2_smt", "name": "statement", "prose": "The organization manages information system accounts."}
    ],
}


def test_playground_page_is_served() -> None:
    response = client.get("/playground")

    assert response.status_code == 200
    assert "Control Conversion Playground" in response.text


def test_convert_endpoint_returns_trestle_markdown_for_valid_control() -> None:
    response = client.post("/playground/oscal-to-markdown", json={"oscal_json": json.dumps(SINGLE_CONTROL)})

    assert response.status_code == 200
    body = response.json()
    assert "Account Management" in body["markdown"]


def test_convert_endpoint_returns_422_with_clear_message_for_invalid_json() -> None:
    response = client.post("/playground/oscal-to-markdown", json={"oscal_json": "{ not valid json"})

    assert response.status_code == 422
    body = response.json()
    assert "valid JSON" in body["message"]


def test_candidate_endpoint_returns_candidate_markdown_for_valid_prose() -> None:
    response = client.post(
        "/playground/prose-to-markdown-candidate",
        json={"prose": "Account Management: the organization manages information system accounts."},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Account Management" in body["markdown"]


def test_candidate_endpoint_returns_422_with_clear_message_for_empty_prose() -> None:
    response = client.post("/playground/prose-to-markdown-candidate", json={"prose": "   "})

    assert response.status_code == 422
    body = response.json()
    assert "Cannot convert empty prose" in body["message"]
