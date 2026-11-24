"""Behave hooks: per-scenario event loop, patch scope, skip handling, and the
@ui live-server + Playwright harness (FR-003, FR-008)."""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import behave.model  # type: ignore[import-untyped]
import pytest

_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

SKIPPED_TAGS = {"wip", "needs-clarification"}
UI_TAG = "ui"

# Lazily populated on the first @ui scenario so non-UI runs never pay for a
# browser/server launch; torn down in after_all if it was ever started.
_ui_harness: dict[str, Any] = {}
_ui_environment: dict[str, str | None] = {}
_ui_cache_dir: Path | None = None


def _configure_ui_environment() -> None:
    global _ui_cache_dir
    from frictionless_architect.visualizer import api
    from frictionless_architect.visualizer import config as visualizer_config

    root = Path(__file__).resolve().parents[2]
    _ui_environment.update(
        {
            key: os.environ.get(key)
            for key in (
                "FRICTIONLESS_ARCHITECT_NEO4J_URI",
                "FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR",
                "FRICTIONLESS_ARCHITECT_CACHE_DIR",
            )
        }
    )
    _ui_cache_dir = Path(tempfile.mkdtemp(prefix="behave-ui-cache-"))
    os.environ.update(
        {
            "FRICTIONLESS_ARCHITECT_NEO4J_URI": "",
            "FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR": str(root / "sample-data"),
            "FRICTIONLESS_ARCHITECT_CACHE_DIR": str(_ui_cache_dir),
        }
    )
    visualizer_config.get_visualizer_settings.cache_clear()
    api.get_schema_service.cache_clear()


def _start_ui_server(app: Any) -> str:
    import uvicorn

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    config = uvicorn.Config(app, fd=sock.fileno(), log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    _ui_harness.update(server=server, thread=thread)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError(
                "@ui harness: uvicorn did not report started within 10s (server thread may have raised during startup)"
            )
        time.sleep(0.05)

    return f"http://127.0.0.1:{port}"


def _start_ui_browser() -> None:
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    _ui_harness["playwright"] = playwright
    _ui_harness["browser"] = playwright.chromium.launch()


def _ensure_ui_harness() -> None:
    if _ui_harness:
        return
    _configure_ui_environment()
    from frictionless_architect.app import app

    _ui_harness["base_url"] = _start_ui_server(app)
    _start_ui_browser()


def _attempt_ui_cleanup(action: Callable[[], object], errors: list[Exception]) -> None:
    try:
        action()
    except Exception as exc:  # noqa: BLE001 - teardown must collect every failure, whatever its type
        errors.append(exc)


def _stop_ui_server() -> None:
    _ui_harness["server"].should_exit = True
    _ui_harness["thread"].join(timeout=5)


def _close_ui_resources(errors: list[Exception]) -> None:
    if "browser" in _ui_harness:
        _attempt_ui_cleanup(_ui_harness["browser"].close, errors)
    if "playwright" in _ui_harness:
        _attempt_ui_cleanup(_ui_harness["playwright"].stop, errors)
    if "server" in _ui_harness:
        _attempt_ui_cleanup(_stop_ui_server, errors)


def _clear_ui_caches(errors: list[Exception]) -> None:
    try:
        from frictionless_architect.visualizer import api
        from frictionless_architect.visualizer import config as visualizer_config

        _attempt_ui_cleanup(api.get_schema_service.cache_clear, errors)
        _attempt_ui_cleanup(visualizer_config.get_visualizer_settings.cache_clear, errors)
    except Exception as exc:  # noqa: BLE001 - teardown must collect every failure, whatever its type
        errors.append(exc)


def _restore_ui_environment(errors: list[Exception]) -> None:
    global _ui_cache_dir
    for key, value in _ui_environment.items():
        try:
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        except Exception as exc:  # noqa: BLE001 - teardown must collect every failure, whatever its type
            errors.append(exc)
    _ui_environment.clear()
    if _ui_cache_dir is not None:
        cache_dir = _ui_cache_dir
        _attempt_ui_cleanup(lambda: shutil.rmtree(cache_dir), errors)
    _ui_cache_dir = None


def _teardown_ui_harness() -> None:
    if not _ui_harness and not _ui_environment and _ui_cache_dir is None:
        return
    errors: list[Exception] = []
    _close_ui_resources(errors)
    try:
        _clear_ui_caches(errors)
    finally:
        _restore_ui_environment(errors)
        _ui_harness.clear()

    if errors:
        raise ExceptionGroup("UI harness cleanup failed", errors)


_original_scenario_run = behave.model.Scenario.run


def _run_with_ui_retry(self: Any, runner: Any) -> bool:
    """FR-008: a failed @ui scenario gets exactly one automatic retry.

    Patches ``Scenario.run`` itself rather than retrying from inside
    ``after_scenario``: ``Feature.run``/``Runner.run_model`` decide the
    suite's pass/fail (and therefore the process exit code) from this
    method's *return value*, which is computed before the `after_scenario`
    hook runs. Retrying only inside that hook would update
    ``scenario.status`` (fixing the printed summary) while leaving the
    outer call still returning the original failure — the gate would still
    exit non-zero even though the retry passed. Looping here instead means
    the return value reflects the retry's real outcome. The `_ui_retried`
    flag stops it recursing past one retry when the retry itself fails
    again.
    """
    failed: bool = _original_scenario_run(self, runner)
    if failed and UI_TAG in self.effective_tags and not getattr(self, "_ui_retried", False):
        self._ui_retried = True
        self.reset()
        failed = _original_scenario_run(self, runner)
    return failed


behave.model.Scenario.run = _run_with_ui_retry


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
    """Close the client/browser context and undo every patch."""
    if UI_TAG in scenario.effective_tags:
        context.page.close()
        context.browser_context.close()
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
