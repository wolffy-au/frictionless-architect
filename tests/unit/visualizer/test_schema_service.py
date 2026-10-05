"""Unit tests that hit the visualiser payload service helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from frictionless_architect.visualizer.api import (
    PayloadUnavailable,
    RefreshBackoff,
    RefreshInProgress,
    SchemaPayloadService,
)
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
    assert service.get_status()["last_warning"] == settings.warning_text


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


@pytest.mark.asyncio
async def test_schema_payload_warns_on_foreign_sample_namespace(tmp_path: Path) -> None:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path / "cache",
        sample_data_dir=tmp_path,
    )
    sample_path = settings.sample_model_path
    sample_path.parent.mkdir(parents=True)
    sample_path.write_text('<model xmlns="http://www.opengroup.org/xsd/archimate/3.1/"/>', encoding="utf-8")
    parser = SampleParser(sample_path)
    loader = StubLoader(settings)
    cache = SchemaCache(settings.cache_path)
    service = SchemaPayloadService(settings, parser, loader, cache)
    payload = await service.get_payload(force_reload=True)
    assert any("archimate/3.1/" in warning for warning in payload["warnings"])
    assert service.get_status()["sample_file_status"] == "invalid"


def _backoff_service(tmp_path: Path, backoff_seconds: int = 300) -> SchemaPayloadService:
    settings = VisualizerSettings(
        cache_dir=tmp_path / "cache", sample_data_dir=tmp_path, refresh_backoff_seconds=backoff_seconds
    )
    return SchemaPayloadService(settings, StubParser(tmp_path), StubLoader(settings), SchemaCache(settings.cache_path))


@pytest.mark.asyncio
async def test_request_refresh_backs_off_after_successful_refresh(tmp_path: Path) -> None:
    service = _backoff_service(tmp_path)
    service._last_refresh_completed = datetime.now(timezone.utc) - timedelta(seconds=100)
    with pytest.raises(RefreshBackoff) as excinfo:
        await service.request_refresh()
    assert 199 <= excinfo.value.retry_after <= 200
    assert service._refresh_task is None


@pytest.mark.asyncio
async def test_request_refresh_allowed_when_backoff_elapsed(tmp_path: Path) -> None:
    service = _backoff_service(tmp_path)
    service._last_refresh_completed = datetime.now(timezone.utc) - timedelta(seconds=301)
    await service.request_refresh()
    assert service._refresh_task is not None
    await service._refresh_task


@pytest.mark.asyncio
async def test_request_refresh_not_delayed_when_no_refresh_has_succeeded(tmp_path: Path) -> None:
    """A failed build never sets the completion time, so it is retryable at once."""
    service = _backoff_service(tmp_path)
    assert service._last_refresh_completed is None
    await service.request_refresh()
    assert service._refresh_task is not None
    await service._refresh_task


class FlakyLoader(StubLoader):
    """Fails ``failures`` times, then recovers."""

    def __init__(self, settings: VisualizerSettings, failures: int) -> None:
        super().__init__(settings)
        self.failures = failures
        self.calls = 0

    def collect(self) -> dict[str, list[dict[str, str]]]:
        self.calls += 1
        if self.calls <= self.failures:
            raise DataLoaderError("neo4j down")
        return super().collect()


def _retry_service(tmp_path: Path, failures: int, interval: int = 300) -> tuple[SchemaPayloadService, FlakyLoader]:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        cache_dir=tmp_path / "cache",
        sample_data_dir=tmp_path,
        retry_interval_seconds=interval,
    )
    loader = FlakyLoader(settings, failures)
    return SchemaPayloadService(settings, StubParser(tmp_path), loader, SchemaCache(settings.cache_path)), loader


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record the retry delays and yield to the loop instead of really waiting."""
    delays: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)
        await real_sleep(0)

    monkeypatch.setattr("frictionless_architect.visualizer.api.asyncio.sleep", fake_sleep)
    return delays


@pytest.mark.asyncio
async def test_failed_load_retries_at_most_interval_apart_until_it_succeeds(
    tmp_path: Path, sleeps: list[float]
) -> None:
    service, loader = _retry_service(tmp_path, failures=3)
    await service.get_payload(force_reload=True)
    assert service.get_status()["neo4j_status"] == "unavailable"
    assert service.get_status()["retry_pending"] is True
    assert service._retry_task is not None
    await service._retry_task
    assert loader.calls == 4
    assert [d for d in sleeps if d] == [300, 300, 300]
    status = service.get_status()
    assert status["neo4j_status"] == "available"
    assert status["retry_pending"] is False


@pytest.mark.asyncio
async def test_unavailable_payload_with_nothing_cached_is_retried(tmp_path: Path, sleeps: list[float]) -> None:
    settings = VisualizerSettings(cache_dir=tmp_path / "cache", sample_data_dir=tmp_path, retry_interval_seconds=60)
    parser = EmptyParser(tmp_path)
    service = SchemaPayloadService(settings, parser, StubLoader(settings), SchemaCache(settings.cache_path))
    with pytest.raises(PayloadUnavailable):
        await service.get_payload()
    assert service._retry_task is not None
    for _ in range(5):
        await asyncio.sleep(0)
    await service.stop_retry()
    assert 60 in sleeps


@pytest.mark.asyncio
async def test_healthy_load_starts_no_retry(tmp_path: Path, sleeps: list[float]) -> None:
    service, _ = _retry_service(tmp_path, failures=0)
    await service.get_payload(force_reload=True)
    assert service._retry_task is None
    assert sleeps == []


@pytest.mark.asyncio
async def test_repeated_failures_keep_a_single_retry_task(tmp_path: Path, sleeps: list[float]) -> None:
    service, _ = _retry_service(tmp_path, failures=100)
    await service.get_payload(force_reload=True)
    first = service._retry_task
    await service.get_payload(force_reload=True)
    assert service._retry_task is first
    await service.stop_retry()
    assert service._retry_task is None


@pytest.mark.asyncio
async def test_stop_retry_is_safe_when_idle(tmp_path: Path) -> None:
    service, _ = _retry_service(tmp_path, failures=0)
    await service.stop_retry()


@pytest.mark.asyncio
async def test_retry_keeps_going_when_an_attempt_fails_outright(tmp_path: Path, sleeps: list[float]) -> None:
    """With nothing to serve, each attempt raises ``PayloadUnavailable``; the loop must carry on until data returns."""
    settings = VisualizerSettings(cache_dir=tmp_path / "cache", sample_data_dir=tmp_path, retry_interval_seconds=60)

    class RecoveringParser(EmptyParser):
        calls = 0

        def parse(self) -> SampleParseResult:
            type(self).calls += 1
            if type(self).calls <= 3:
                return super().parse()
            return StubParser(tmp_path).parse()

    service = SchemaPayloadService(
        settings, RecoveringParser(tmp_path), StubLoader(settings), SchemaCache(settings.cache_path)
    )
    with pytest.raises(PayloadUnavailable):
        await service.get_payload()
    assert service._retry_task is not None
    await service._retry_task
    assert RecoveringParser.calls == 4
    assert [d for d in sleeps if d] == [60, 60, 60]
    assert service.get_status()["retry_pending"] is False
