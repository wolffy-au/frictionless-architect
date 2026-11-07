"""Integrity checks on architecture/model/views.yaml and views-viewpoints.yaml.

Guards against a view that render_diagrams.py would silently skip. Viewpoint slugs
are checked by the modelling-specification package's own tests (test_viewpoints.py):
root never imports a platform package (ADR-0001), and this job has no platform venv.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "architecture/model"
VIEW_FILES = [MODEL_DIR / "views.yaml", MODEL_DIR / "views-viewpoints.yaml"]


def _views() -> list[dict[str, Any]]:
    return [v for f in VIEW_FILES for v in yaml.safe_load(f.read_text()) or []]


def test_every_view_has_id_name_and_diagram() -> None:
    for v in _views():
        assert v.get("id"), v
        assert v.get("name"), v
        assert v.get("diagram"), f"{v.get('id')} has no `diagram:` key"


def test_diagram_slugs_are_unique() -> None:
    slugs = [v["diagram"] for v in _views()]
    assert len(slugs) == len(set(slugs)), "duplicate diagram slug across view files"


def test_vision_views_render_under_vision_dir() -> None:
    by_id = {v["id"]: v for v in _views()}
    for vid in ("view-stakeholder", "view-motivation", "view-strategy", "view-value-stream"):
        assert by_id[vid]["diagram"].startswith("vision/"), vid


def test_view_ids_are_unique_across_files() -> None:
    ids = [v["id"] for v in _views()]
    assert len(ids) == len(set(ids)), "duplicate view id across view files"
