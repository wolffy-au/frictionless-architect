"""Behave hooks: per-scenario event loop, patch scope and skip handling."""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

SKIPPED_TAGS = {"wip", "needs-clarification"}


def before_scenario(context: Any, scenario: Any) -> None:
    """Skip not-yet-built or ambiguous scenarios; otherwise prepare a fresh harness."""
    if SKIPPED_TAGS & set(scenario.effective_tags):
        scenario.skip(reason="@wip / @needs-clarification: documented, not executable yet")
        return
    context.loop = asyncio.new_event_loop()
    context.monkeypatch = pytest.MonkeyPatch()
    context.tmp_dir = Path(tempfile.mkdtemp(prefix="behave-schema-"))
    context.client = None
    context.options = {}


def after_scenario(context: Any, scenario: Any) -> None:
    """Stop background retries, close the client and undo every patch."""
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
