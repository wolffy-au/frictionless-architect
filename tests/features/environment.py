"""Behave hooks: per-scenario event loop, patch scope, skip handling, and the
@ui live-server + Playwright harness (FR-003, FR-008)."""

from __future__ import annotations

import asyncio
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from behave.model_core import Status  # type: ignore[import-untyped]

_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

SKIPPED_TAGS = {"wip", "needs-clarification"}
UI_TAG = "ui"

# Lazily populated on the first @ui scenario so non-UI runs never pay for a
# browser/server launch; torn down in after_all if it was ever started.
_ui_harness: dict[str, Any] = {}


def _ensure_ui_harness() -> None:
    if _ui_harness:
        return
    import uvicorn
    from playwright.sync_api import sync_playwright

    from frictionless_architect.app import app

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    config = uvicorn.Config(app, fd=sock.fileno(), log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch()

    _ui_harness.update(
        base_url=f"http://127.0.0.1:{port}",
        server=server,
        thread=thread,
        playwright=playwright,
        browser=browser,
    )


def _teardown_ui_harness() -> None:
    if not _ui_harness:
        return
    _ui_harness["browser"].close()
    _ui_harness["playwright"].stop()
    _ui_harness["server"].should_exit = True
    _ui_harness["thread"].join(timeout=5)
    _ui_harness.clear()


def _retry_failed_ui_scenario_once(context: Any, scenario: Any) -> None:
    """FR-008: a failed @ui scenario gets exactly one automatic retry.

    Re-invokes Scenario.run() directly rather than looping behave's CLI,
    since that's the only way to redrive a single scenario's hooks/steps
    from inside this same process. The `_retried` flag stops it recursing
    past one retry when the retry itself fails again.
    """
    if scenario.status != Status.failed or getattr(scenario, "_retried", False):
        return
    scenario._retried = True
    scenario.reset()
    scenario.run(context._runner)  # noqa: SLF001


def before_scenario(context: Any, scenario: Any) -> None:
    """Skip not-yet-built or ambiguous scenarios; otherwise prepare a fresh harness."""
    if SKIPPED_TAGS & set(scenario.effective_tags):
        scenario.skip(reason="@wip / @needs-clarification: documented, not executable yet")
        return
    if UI_TAG in scenario.effective_tags:
        _ensure_ui_harness()
        context.base_url = _ui_harness["base_url"]
        context.browser_context = _ui_harness["browser"].new_context()
        context.page = context.browser_context.new_page()
        return
    context.loop = asyncio.new_event_loop()
    context.monkeypatch = pytest.MonkeyPatch()
    context.tmp_dir = Path(tempfile.mkdtemp(prefix="behave-schema-"))
    context.client = None
    context.options = {}


def after_scenario(context: Any, scenario: Any) -> None:
    """Stop background retries, close the client and undo every patch."""
    if UI_TAG in scenario.effective_tags:
        context.page.close()
        context.browser_context.close()
        _retry_failed_ui_scenario_once(context, scenario)
        return
    loop = getattr(context, "loop", None)
    if loop is None:
        return
    from frictionless_architect.visualizer import api as api_mod
    from frictionless_architect.visualizer import config as config_mod

    try:
        if context.client is not None:
            loop.run_until_complete(api_mod.get_schema_service().stop_retry())
            loop.run_until_complete(context.client.aclose())
    finally:
        loop.close()
        context.monkeypatch.undo()
        config_mod.get_visualizer_settings.cache_clear()
        api_mod.get_schema_service.cache_clear()
        shutil.rmtree(context.tmp_dir, ignore_errors=True)


def after_all(context: Any) -> None:
    _teardown_ui_harness()
