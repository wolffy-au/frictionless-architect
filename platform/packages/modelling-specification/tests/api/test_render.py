"""Contract tests for `GET /authoring/render` (FR-013/FR-016, contracts/api.md).

Runs against the real committed model -- `render_single_view` is read-only (see
`tests/unit/test_rendering.py`'s own real-model test), so no isolation is needed.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from modelling_specification.app import app

client = TestClient(app)


def test_render_by_object_id_returns_the_view_and_svg() -> None:
    response = client.get("/authoring/render", params={"object_id": "view-stakeholder"})

    assert response.status_code == 200
    body = response.json()
    assert body["view_id"] == "view-stakeholder"
    assert "</svg>" in body["svg"]


def test_render_svg_format_returns_svg_content_type_and_document() -> None:
    response = client.get(
        "/authoring/render",
        params={"object_id": "view-stakeholder", "format": "svg"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert response.headers["cache-control"] == "no-store"
    assert response.text.startswith("<svg")
    assert response.text.rstrip().endswith("</svg>")


def test_render_ambiguous_description_returns_300_with_candidates() -> None:
    response = client.get("/authoring/render", params={"description": "value stream"})

    assert response.status_code == 300
    assert "view-value-stream" in response.json()["ambiguous_candidates"]


def test_render_no_match_returns_404() -> None:
    response = client.get("/authoring/render", params={"object_id": "not-a-real-id-or-view"})

    assert response.status_code == 404


def test_views_lists_every_renderable_view_with_id_and_name() -> None:
    response = client.get("/authoring/views")
    assert response.status_code == 200
    views = response.json()
    assert {"id": "view-stakeholder", "name": "Stakeholder"} in views
    assert all(set(v) == {"id", "name"} for v in views)


def test_render_svg_reports_which_view_it_rendered() -> None:
    response = client.get("/authoring/render", params={"object_id": "view-stakeholder", "format": "svg"})
    assert response.headers["X-View-Id"] == "view-stakeholder"
