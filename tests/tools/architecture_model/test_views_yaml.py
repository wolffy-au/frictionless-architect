"""Integrity checks on architecture/model/views.yaml itself.

Guards against a view that render_diagrams.py would silently skip, or a
viewpoint slug that build.py would only reject at build time.
"""

from __future__ import annotations

from pathlib import Path

import viewpoints
import yaml

VIEWS = Path(__file__).resolve().parents[3] / "architecture/model/views.yaml"


def _views() -> list[dict]:
    return yaml.safe_load(VIEWS.read_text()) or []


def test_every_view_has_id_name_and_diagram() -> None:
    for v in _views():
        assert v.get("id"), v
        assert v.get("name"), v
        assert v.get("diagram"), f"{v.get('id')} has no `diagram:` key"


def test_diagram_slugs_are_unique() -> None:
    slugs = [v["diagram"] for v in _views()]
    assert len(slugs) == len(set(slugs)), "duplicate diagram slug in views.yaml"


def test_viewpoint_slugs_are_known() -> None:
    valid = set(viewpoints.known_slugs()) | {viewpoints.UNRESTRICTED}
    for v in _views():
        slug = v.get("viewpoint")
        if slug is not None:
            assert slug in valid, f"{v['id']}: unknown viewpoint {slug!r}"


def test_vision_views_render_under_vision_dir() -> None:
    by_id = {v["id"]: v for v in _views()}
    for vid in ("view-stakeholder", "view-motivation", "view-strategy", "view-value-stream"):
        assert by_id[vid]["diagram"].startswith("vision/"), vid
