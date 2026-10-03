"""behave environment: run the real FastAPI app and a Playwright browser for UI scenarios."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from behave.runner import Context
from controls_compliance_catalog import llm_client
from controls_compliance_catalog.app import app
from llm_provider_config import LlmSettings, Provider, ProviderSettings, save_settings
from playwright.sync_api import sync_playwright

# behave doesn't put tests/ on sys.path the way pytest's conftest does; the shared fake lives there.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support.fake_llm import FakeCompletion  # noqa: E402


def _free_port_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    return sock


def _use_fake_llm(context: Context) -> None:
    """The UI harness never calls a real provider: swap litellm's completion for a fake.

    The server runs in this process (a thread), so patching the module attribute reaches it.
    """
    context.llm_config_dir = tempfile.TemporaryDirectory()
    config = save_settings(
        LlmSettings(default=ProviderSettings(provider=Provider.OLLAMA, model="test-model")),
        Path(context.llm_config_dir.name) / "llm.toml",
    )
    os.environ["LLM_PROVIDER_CONFIG_PATH"] = str(config)
    llm_client.completion = FakeCompletion()  # type: ignore[attr-defined]


def before_all(context: Context) -> None:
    _use_fake_llm(context)
    sock = _free_port_socket()
    port = sock.getsockname()[1]
    config = uvicorn.Config(app, fd=sock.fileno(), log_level="warning")
    server = uvicorn.Server(config)
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
    context.browser_context = context.browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    context.page = context.browser_context.new_page()


def after_scenario(context: Context, _scenario: object) -> None:
    context.page.close()
    context.browser_context.close()


def after_all(context: Context) -> None:
    # before_all may have failed partway (e.g. Playwright's browser missing), leaving
    # later attributes unset; guard each teardown so the real failure isn't masked.
    if hasattr(context, "browser"):
        context.browser.close()
    if hasattr(context, "playwright"):
        context.playwright.stop()
    if hasattr(context, "uvicorn_server"):
        context.uvicorn_server.should_exit = True
        context.uvicorn_thread.join(timeout=5)
