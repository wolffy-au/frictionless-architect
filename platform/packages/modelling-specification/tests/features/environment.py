"""behave environment: run the real FastAPI app over a fake LLM.

Model *writes* (`decide` `apply`) are isolated to a per-scenario scratch copy of
`architecture/model/*.yaml`, so no scenario ever touches the committed model.
Rendering stays pointed at the real, read-only committed model/views --
`rendering.py` binds its own `OUT`/`VIEWS` constants at import time, independent of
any `model_io.OUT`/`HERE` reassignment here -- so a resolved view always renders a
real, valid SVG, just one that won't visually include a scenario's isolated-only
appended delta (acceptable: these scenarios test the propose/validate/apply/render
*wiring*, not pixel-perfect diagram content).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from behave.runner import Context
from fastapi.testclient import TestClient
from llm_provider_config import LlmSettings, Provider, ProviderSettings, save_settings
from modelling_specification import model_io
from modelling_specification import router as router_mod
from modelling_specification.app import app
from modelling_specification.authoring import delta as delta_mod
from modelling_specification.authoring import overrides
from modelling_specification.authoring.state import SessionStore

# behave doesn't put tests/ on sys.path the way pytest's conftest does; the shared fake lives there.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support.fake_llm import FakeCompletion  # noqa: E402


def before_all(context: Context) -> None:
    context.llm_config_dir = tempfile.TemporaryDirectory()
    config = save_settings(
        LlmSettings(default=ProviderSettings(provider=Provider.OLLAMA, model="test-model")),
        Path(context.llm_config_dir.name) / "llm.toml",
    )
    os.environ["LLM_PROVIDER_CONFIG_PATH"] = str(config)
    context.fake_llm = FakeCompletion()
    delta_mod.completion = context.fake_llm  # type: ignore[attr-defined]
    context.client = TestClient(app)


def before_scenario(context: Context, _scenario: object) -> None:
    context.fake_llm.content = None
    context.fake_llm.error = None
    context.fake_llm.calls = []
    router_mod._store = SessionStore()
    router_mod._config["auto_render"] = False

    context.model_tmpdir = tempfile.TemporaryDirectory()
    tmp_path = Path(context.model_tmpdir.name)
    for name in ("elements.yaml", "relationships.yaml", "views.yaml"):
        shutil.copy(model_io.HERE / name, tmp_path / name)
    context._orig_model_here = model_io.HERE
    context._orig_model_out = model_io.OUT
    model_io.HERE = tmp_path
    model_io.OUT = tmp_path / "frictionless-architect.xml"

    context.adr_tmpdir = tempfile.TemporaryDirectory()
    context._orig_adr_dir = overrides.ADR_DIR
    overrides.ADR_DIR = Path(context.adr_tmpdir.name)


def after_scenario(context: Context, _scenario: object) -> None:
    model_io.HERE = context._orig_model_here
    model_io.OUT = context._orig_model_out
    context.model_tmpdir.cleanup()
    overrides.ADR_DIR = context._orig_adr_dir
    context.adr_tmpdir.cleanup()


def after_all(context: Context) -> None:
    context.llm_config_dir.cleanup()
