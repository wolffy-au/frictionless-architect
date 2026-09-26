"""Shared fixtures for the schema visualiser API tests."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

import httpx
import pytest
from httpx import ASGITransport

from frictionless_architect import app as app_mod
from frictionless_architect.visualizer import api as api_mod
from frictionless_architect.visualizer import config as config_mod
from frictionless_architect.visualizer import sample_parser as sample_parser_mod
from frictionless_architect.visualizer.api import SchemaPayloadService
from frictionless_architect.visualizer.sample_parser import SampleParser, SampleParseResult

REPO_SAMPLE_DATA = Path(__file__).resolve().parents[2] / "sample-data"


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    patch_sample_parse: Callable[[SampleParser], SampleParseResult] | None = None,
    patch_service_class: Callable[[type, pytest.MonkeyPatch], None] | None = None,
    sample_data: Path = REPO_SAMPLE_DATA,
) -> httpx.AsyncClient:
    cache_dir = tmp_path / "visualiser-cache"
    envs = {
        "FRICTIONLESS_ARCHITECT_NEO4J_URI": "",
        "FRICTIONLESS_ARCHITECT_CACHE_DIR": str(cache_dir),
        "FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR": str(sample_data),
    }
    for key, value in envs.items():
        monkeypatch.setenv(key, value)

    if patch_sample_parse:
        monkeypatch.setattr(sample_parser_mod.SampleParser, "parse", patch_sample_parse)

    if patch_service_class:
        patch_service_class(api_mod.SchemaPayloadService, monkeypatch)

    config_mod.get_visualizer_settings.cache_clear()
    api_mod.get_schema_service.cache_clear()

    transport = ASGITransport(app=app_mod.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture
async def schema_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    sample_path = REPO_SAMPLE_DATA / "sample-00" / "Test Model Full.xml"
    original_parse = SampleParser.parse

    def real_parse(_: SampleParser) -> SampleParseResult:
        return original_parse(SampleParser(sample_path))

    async with _build_client(monkeypatch, tmp_path, patch_sample_parse=real_parse) as client:
        yield client


@pytest.fixture
async def schema_client_without_sample(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncGenerator[httpx.AsyncClient, None]:
    def missing_parse(_: SampleParser) -> SampleParseResult:
        raise FileNotFoundError("missing sample")

    async with _build_client(monkeypatch, tmp_path, missing_parse) as client:
        yield client


@pytest.fixture
async def schema_client_with_slow_refresh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncGenerator[httpx.AsyncClient, None]:
    def slow_build(cls: type[SchemaPayloadService], mp: pytest.MonkeyPatch) -> None:
        original = cls._build_payload

        def wrapped(self: SchemaPayloadService, *args: Any, **kwargs: Any) -> Any:
            time.sleep(0.1)
            return original(self, *args, **kwargs)

        mp.setattr(cls, "_build_payload", wrapped)

    async with _build_client(monkeypatch, tmp_path, patch_service_class=slow_build) as client:
        yield client


@pytest.fixture
async def schema_client_with_xsd_violation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Serve a copy of the real sample with one element the XSD does not allow."""
    sample_data = tmp_path / "sample-data"
    shutil.copytree(REPO_SAMPLE_DATA / "schema", sample_data / "schema")
    sample = sample_data / "sample-00" / "Test Model Full.xml"
    sample.parent.mkdir(parents=True)
    original = (REPO_SAMPLE_DATA / "sample-00" / "Test Model Full.xml").read_text(encoding="utf-8")
    sample.write_text(original.replace("<elements>", "<bogus/>\n  <elements>", 1), encoding="utf-8")

    async with _build_client(monkeypatch, tmp_path, sample_data=sample_data) as client:
        yield client
