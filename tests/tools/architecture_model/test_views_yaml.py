"""Integrity checks on architecture/model/views.yaml and views-viewpoints.yaml.

Guards against a view that render_diagrams.py would silently skip, or a
viewpoint slug that build.py would only reject at build time.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "architecture/model"
VIEW_FILES = [MODEL_DIR / "views.yaml", MODEL_DIR / "views-viewpoints.yaml"]
PLATFORM = REPO_ROOT / "platform"
# `custom` is our own escape hatch for a deliberate cross-layer view (model-archimate
# skill's viewpoints.py) -- not an Archi viewpoint, never conformance-checked.
UNRESTRICTED = "custom"


def _views() -> list[dict[str, Any]]:
    return [v for f in VIEW_FILES for v in yaml.safe_load(f.read_text()) or []]


def _known_viewpoint_slugs() -> set[str]:
    # Root never imports a platform package in-process (ADR-0001) -- shell into the
    # platform venv's CLI the same way `.claude/skills/model-archimate/scripts/viewpoints.py`
    # does, stripping VIRTUAL_ENV so a nested `poetry run` picks platform/'s own venv.
    env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    result = subprocess.run(
        ["poetry", "run", "python", "-m", "modelling_specification.viewpoints", "list"],
        cwd=PLATFORM,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line.split()[0] for line in result.stdout.splitlines() if line.strip()}


def test_every_view_has_id_name_and_diagram() -> None:
    for v in _views():
        assert v.get("id"), v
        assert v.get("name"), v
        assert v.get("diagram"), f"{v.get('id')} has no `diagram:` key"


def test_diagram_slugs_are_unique() -> None:
    slugs = [v["diagram"] for v in _views()]
    assert len(slugs) == len(set(slugs)), "duplicate diagram slug across view files"


def test_viewpoint_slugs_are_known() -> None:
    valid = _known_viewpoint_slugs() | {UNRESTRICTED}
    for v in _views():
        slug = v.get("viewpoint")
        if slug is not None:
            assert slug in valid, f"{v['id']}: unknown viewpoint {slug!r}"


def test_vision_views_render_under_vision_dir() -> None:
    by_id = {v["id"]: v for v in _views()}
    for vid in ("view-stakeholder", "view-motivation", "view-strategy", "view-value-stream"):
        assert by_id[vid]["diagram"].startswith("vision/"), vid


def test_view_ids_are_unique_across_files() -> None:
    ids = [v["id"] for v in _views()]
    assert len(ids) == len(set(ids)), "duplicate view id across view files"
