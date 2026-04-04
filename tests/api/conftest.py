"""Shared fixtures for the schema visualiser API tests."""

from __future__ import annotations

import importlib
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

import httpx
import pytest
from httpx import ASGITransport

from frictionless_architect.visualizer.api import SchemaPayloadService
from frictionless_architect.visualizer.sample_parser import SampleParser, SampleParseResult


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    patch_sample_parse: Callable[[SampleParser], SampleParseResult] | None = None,
    patch_service_class: Callable[[type], None] | None = None,
) -> httpx.AsyncClient:
    root = Path(__file__).resolve().parents[2]
    sample_data = root / "sample-data"
    cache_dir = tmp_path / "visualiser-cache"
    envs = {
        "FRICTIONLESS_ARCHITECT_NEO4J_URI": "",
        "FRICTIONLESS_ARCHITECT_CACHE_DIR": str(cache_dir),
        "FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR": str(sample_data),
    }
    for key, value in envs.items():
        monkeypatch.setenv(key, value)

    config_mod = importlib.import_module("frictionless_architect.visualizer.config")
    config_mod = importlib.reload(config_mod)

    sample_parser_mod = importlib.import_module("frictionless_architect.visualizer.sample_parser")
    sample_parser_mod = importlib.reload(sample_parser_mod)
    if patch_sample_parse:
        monkeypatch.setattr(sample_parser_mod.SampleParser, "parse", patch_sample_parse)

    api_mod = importlib.import_module("frictionless_architect.visualizer.api")
    api_mod = importlib.reload(api_mod)
    if patch_service_class:
        patch_service_class(api_mod.SchemaPayloadService)

    visualizer_mod = importlib.import_module("frictionless_architect.visualizer")
    visualizer_mod = importlib.reload(visualizer_mod)

    config_mod.get_visualizer_settings.cache_clear()
    api_mod.get_schema_service.cache_clear()

    transport = ASGITransport(app=visualizer_mod.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture
async def schema_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    sample_path = Path(__file__).resolve().parents[2] / "sample-data" / "sample-00" / "Test Model Full.xml"

    def real_parse(_: SampleParser) -> SampleParseResult:
        return SampleParser(sample_path).parse()

    async with _build_client(monkeypatch, tmp_path, patch_sample_parse=real_parse) as client:
        yield client


@pytest.fixture
async def schema_client_without_sample(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    def missing_parse(_: SampleParser) -> SampleParseResult:
        raise FileNotFoundError("missing sample")

    async with _build_client(monkeypatch, tmp_path, missing_parse) as client:
        yield client


@pytest.fixture
async def schema_client_with_slow_refresh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    def slow_build(cls: type[SchemaPayloadService]) -> None:
        original = cls._build_payload

        def wrapped(self: SchemaPayloadService, *args: Any, **kwargs: Any) -> Any:
            time.sleep(0.1)
            return original(self, *args, **kwargs)

        cls._build_payload = wrapped  # type: ignore[method-assign]

    async with _build_client(monkeypatch, tmp_path, patch_service_class=slow_build) as client:
        yield client
