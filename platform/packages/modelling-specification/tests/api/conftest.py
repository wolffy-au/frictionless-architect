"""Fixtures shared by the `tests/api/` contract tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from modelling_specification import model_io
from modelling_specification.authoring import overrides


@pytest.fixture
def isolated_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Copy the real `architecture/model/*.yaml` into a scratch dir and point
    `model_io` at it, so an apply-path test exercises `append_delta`/
    `write_and_validate` for real without ever writing to the committed model.
    `gh-roadmap`/vendored layers still load from their real location (R2's
    `MODEL_LAYERS` is fixed at import time), merging in unchanged alongside this
    copy exactly as they do for the real files. Also isolates `overrides.ADR_DIR` to
    the same scratch dir, so an `override` decide action never drafts a real ADR."""
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    for name in ("elements.yaml", "relationships.yaml", "views.yaml"):
        shutil.copy(model_io.HERE / name, model_dir / name)
    monkeypatch.setattr(model_io, "HERE", model_dir)
    monkeypatch.setattr(model_io, "OUT", model_dir / "frictionless-architect.xml")
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    monkeypatch.setattr(overrides, "ADR_DIR", adr_dir)
    return model_dir
