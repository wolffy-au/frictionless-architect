"""Contract test for `GET /authoring/` (T067, R15): the split-screen UI page itself,
mirroring `controls_compliance_catalog`'s `test_playground_page_is_served`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from modelling_specification.app import app

client = TestClient(app)

_EXPECTED_IDS = ("chat-input", "send", "state-select", "apply", "render-pane")


def test_authoring_page_is_served() -> None:
    response = client.get("/authoring/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for element_id in _EXPECTED_IDS:
        assert f'id="{element_id}"' in response.text, element_id
