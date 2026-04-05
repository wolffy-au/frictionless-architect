"""Unit tests that hit the visualiser payload service helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from frictionless_architect.visualizer.api import PayloadUnavailable, RefreshInProgress, SchemaPayloadService
from frictionless_architect.visualizer.cache import SchemaCache
from frictionless_architect.visualizer.config import VisualizerSettings
from frictionless_architect.visualizer.data_loader import DataLoader, DataLoaderError
from frictionless_architect.visualizer.sample_parser import SampleParser, SampleParseResult


class StubParser(SampleParser):
    def __init__(self, base_path: Path) -> None:
        super().__init__(base_path / "Test Model Full.xml")
        self._base_path = base_path

    def parse(self) -> SampleParseResult:
        return SampleParseResult(
            model={"identifier": "model", "name": "Model"},
            elements={
                "E1": {"identifier": "E1", "type": "Element", "name": "Sample Element"},
            },
            relationships={
                "R1": {
                    "identifier": "R1",
                    "type": "Rel",
                    "source": "E1",
                    "target": "E1",
                },
            },
            views=[
                {
                    "identifier": "V1",
                    "name": "View",
                    "nodes": [
                        {
                            "identifier": "node-1",
                            "elementRef": "E1",
                            "bounds": {"x": 10, "y": 20, "w": 30, "h": 40},
                            "label": "Sample Node",
                        }
                    ],
                    "connections": [
                        {
                            "identifier": "conn-1",
                            "relationshipRef": "R1",
                            "source": "E1",
                            "target": "E1",
                        }
                    ],
                }
            ],
            file_path=self._base_path / "Test Model Full.xml",
        )


class StubLoader(DataLoader):
    def __init__(self, settings: VisualizerSettings) -> None:
        super().__init__(settings)

    def collect(self) -> dict[str, list[dict[str, str]]]:
        return {
            "elements": [
                {"identifier": "E1", "type": "Element", "name": "Schema Element"},
            ],
            "relationships": [
                {
                    "identifier": "R1",
                    "type": "Rel",
                    "source": "E1",
                    "target": "E1",
                }
            ],
            "views": [],
        }


class ErrorLoader(StubLoader):
    def collect(self) -> dict[str, list[dict[str, str]]]:
        raise DataLoaderError("boom")


class EmptyParser(SampleParser):
    def __init__(self, base_path: Path) -> None:
        super().__init__(base_path / "Test Model Full.xml")

    def parse(self) -> SampleParseResult:
        return SampleParseResult.empty(self.sample_file)


class PartialLoader(StubLoader):
    def collect(self) -> dict[str, list[dict[str, str]]]:
        return {
            "elements": [
                {"identifier": "E2", "type": "Element", "name": "Schema Only"},
            ],
            "relationships": [
                {
                    "identifier": "R2",
                    "type": "Rel",
                    "source": "E2",
                    "target": "E2",
                }
            ],
            "views": [],
        }


class BackgroundFailingService(SchemaPayloadService):
    async def _build_and_cache(self) -> dict[str, Any]:
        raise PayloadUnavailable("boom", warnings=["boom"])


@pytest.mark.parametrize("loader_cls", (StubLoader, ErrorLoader))
def test_schema_payload_service_merges(tmp_path: Path, loader_cls: type[StubLoader]) -> None:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path / "cache",
        sample_data_dir=tmp_path,
    )
    parser = StubParser(tmp_path)
    loader = loader_cls(settings)
    cache = SchemaCache(settings.cache_path)
    service = SchemaPayloadService(settings, parser, loader, cache)
    payload = asyncio.run(service.get_payload(force_reload=True))
    # ensure model + view metadata survive merging
    assert payload["model"]["name"] == "Model"
    assert any(elem["identifier"] == "E1" for elem in payload["elements"])
    assert any(elem["sample_instances"] for elem in payload["elements"])
    # views should be present when parser produces them
    assert payload["views"][0]["identifier"] == "V1"

    status = service.get_status()
    if loader_cls is StubLoader:
        assert status["neo4j_status"] == "available"
    else:
        assert status["neo4j_status"] == "unavailable"


@pytest.mark.asyncio
async def test_returns_cached_payload_when_build_unavailable(tmp_path: Path) -> None:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path / "cache",
        sample_data_dir=tmp_path,
    )
    cache = SchemaCache(settings.cache_path)
    cache.save({"model": {"identifier": "cached"}})

    class FailingParser(SampleParser):
        def __init__(self) -> None:
            super().__init__(tmp_path / "missing.xml")

        def parse(self) -> SampleParseResult:
            raise FileNotFoundError("missing")

    class EmptyLoader(StubLoader):
        def collect(self) -> dict[str, list[dict[str, str]]]:
            return {"elements": [], "relationships": [], "views": []}

    parser = FailingParser()
    loader = EmptyLoader(settings)
    service = SchemaPayloadService(settings, parser, loader, cache)
    payload = await service.get_payload(force_reload=True)
    assert payload == {"model": {"identifier": "cached"}}
    warning_text = service.get_status()["last_warning"]
    assert warning_text.startswith(settings.warning_text)


@pytest.mark.asyncio
async def test_schema_payload_warns_for_missing_samples(tmp_path: Path) -> None:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path / "cache",
        sample_data_dir=tmp_path,
    )
    parser = EmptyParser(tmp_path)
    loader = PartialLoader(settings)
    cache = SchemaCache(settings.cache_path)
    service = SchemaPayloadService(settings, parser, loader, cache)
    payload = await service.get_payload(force_reload=True)
    assert any("Missing sample entry" in warning for warning in payload["warnings"])


@pytest.mark.asyncio
async def test_request_refresh_raises_when_already_running(tmp_path: Path) -> None:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path / "cache",
        sample_data_dir=tmp_path,
    )
    parser = StubParser(tmp_path)
    loader = StubLoader(settings)
    cache = SchemaCache(settings.cache_path)
    service = SchemaPayloadService(settings, parser, loader, cache)
    service._refresh_task = asyncio.create_task(asyncio.sleep(0.1))
    with pytest.raises(RefreshInProgress):
        await service.request_refresh()
    assert service._refresh_task is not None
    service._refresh_task.cancel()


@pytest.mark.asyncio
async def test_background_refresh_handles_unavailable(tmp_path: Path) -> None:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path / "cache",
        sample_data_dir=tmp_path,
    )
    parser = StubParser(tmp_path)
    loader = StubLoader(settings)
    cache = SchemaCache(settings.cache_path)
    service = BackgroundFailingService(settings, parser, loader, cache)

    service._refresh_task = asyncio.ensure_future(asyncio.sleep(0))
    await service._background_refresh()
    assert service._refresh_task is None
