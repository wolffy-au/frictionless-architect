"""Contract test for `GET /authoring/` (T067, R15): the split-screen UI page itself,
mirroring `controls_compliance_catalog`'s `test_playground_page_is_served`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from modelling_specification.app import app

client = TestClient(app)

_EXPECTED_IDS = ("chat-input", "send", "apply", "view-select", "render-banner", "render-status", "render-pane")


def test_authoring_page_is_served() -> None:
    response = client.get("/authoring/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for element_id in _EXPECTED_IDS:
        assert f'id="{element_id}"' in response.text, element_id


def test_authoring_page_links_to_the_llm_settings_page() -> None:
    assert 'href="/settings/llm"' in client.get("/authoring/").text


def test_authoring_page_has_no_state_control() -> None:
    assert "state-select" not in client.get("/authoring/").text


def test_authoring_page_inserts_the_server_rendered_message_html() -> None:
    # GH #185: the LLM's free-text "message" reply arrives pre-rendered as sanitised
    # HTML in `message_html` (router.py); the page inserts it directly rather than
    # building Markdown client-side or showing an unstyled pre-wrap block of raw syntax.
    page = client.get("/authoring/").text
    assert "body.message_html" in page
    assert 'whiteSpace = "pre-wrap"' not in page
