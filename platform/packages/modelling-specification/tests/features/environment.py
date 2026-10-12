"""behave environment: run the real FastAPI app over a fake LLM.

Model *writes* (`decide` `apply`) are isolated to a per-scenario scratch copy of
`architecture/model/*.yaml`, so no scenario ever touches the committed model.
Rendering stays pointed at the real, read-only committed model/views --
`rendering.py` binds its own `OUT`/`VIEWS` constants at import time, independent of
any `model_io.OUT`/`HERE` reassignment here -- so a resolved view always renders a
real, valid SVG, just one that won't visually include a scenario's isolated-only
appended delta (acceptable: these scenarios test the propose/validate/apply/render
*wiring*, not pixel-perfect diagram content).

T068 (UI Phase): also runs a live `uvicorn` server (background thread, free port) and
a Playwright Chromium browser, alongside -- not instead of -- the `TestClient` above,
mirroring `controls_compliance_catalog`'s own `environment.py`. The server runs
in-process in this same thread's process, so the `model_io.HERE`/`OUT`/
`overrides.ADR_DIR` monkeypatches below still reach it; `ui_steps.py`'s scenarios
drive `context.page` against `context.base_url` instead of `context.client`.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from behave.runner import Context
from fastapi.testclient import TestClient
from llm_provider_config import LlmSettings, Provider, ProviderSettings, save_settings
from modelling_specification import model_io
from modelling_specification import router as router_mod
from modelling_specification.app import app
from modelling_specification.authoring import delta as delta_mod
from modelling_specification.authoring import overrides
from modelling_specification.authoring.state import SessionStore
from playwright.sync_api import sync_playwright

# behave doesn't put tests/ on sys.path the way pytest's conftest does; the shared fake lives there.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support.fake_llm import FakeCompletion  # noqa: E402


def _free_port_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    return sock


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

    sock = _free_port_socket()
    port = sock.getsockname()[1]
    uvicorn_config = uvicorn.Config(app, fd=sock.fileno(), log_level="warning")
    server = uvicorn.Server(uvicorn_config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    context.base_url = f"http://127.0.0.1:{port}"
    context.uvicorn_server = server
    context.uvicorn_thread = thread

    context.playwright = sync_playwright().start()
    context.browser = context.playwright.chromium.launch()


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

    context.browser_context = context.browser.new_context()
    context.page = context.browser_context.new_page()


def after_scenario(context: Context, _scenario: object) -> None:
    # A render the page fired just before the scenario ended may still be rebuilding
    # the scratch model below; let it finish before that model is removed.
    context.page.wait_for_load_state("networkidle")
    model_io.HERE = context._orig_model_here
    model_io.OUT = context._orig_model_out
    context.model_tmpdir.cleanup()
    overrides.ADR_DIR = context._orig_adr_dir
    context.adr_tmpdir.cleanup()

    context.page.close()
    context.browser_context.close()


def after_all(context: Context) -> None:
    context.llm_config_dir.cleanup()
    # before_all may have failed partway (e.g. Playwright's browser missing), leaving
    # later attributes unset; guard each teardown so the real failure isn't masked.
    if hasattr(context, "browser"):
        context.browser.close()
    if hasattr(context, "playwright"):
        context.playwright.stop()
    if hasattr(context, "uvicorn_server"):
        context.uvicorn_server.should_exit = True
        context.uvicorn_thread.join(timeout=5)
