"""Unit tests for the visualiser Neo4j data loader."""

from __future__ import annotations

from typing import Any

import pytest
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable, SessionExpired

from frictionless_architect.visualizer.config import VisualizerSettings
from frictionless_architect.visualizer.data_loader import DataLoader, DataLoaderError


class DummyRow:
    def __init__(self, row: dict[str, Any]) -> None:
        self._row = row

    def data(self) -> dict[str, Any]:
        return self._row


class DummyTx:
    def run(self, query: str) -> list[DummyRow]:
        if "MATCH (e:Element)" in query:
            return [DummyRow({"identifier": "E1", "type": "Element"})]
        if "ARCHIMATE_RELATIONSHIP" in query:
            return [DummyRow({"identifier": "R1", "type": "Rel"})]
        return [DummyRow({"identifier": "V1", "name": "View"})]


class DummySession:
    def __enter__(self) -> DummySession:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def execute_read(self, func: Any) -> Any:
        return func(DummyTx())


class DummyDriver:
    def session(self) -> DummySession:
        return DummySession()


class ClosableDriver(DummyDriver):
    closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def fake_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "frictionless_architect.visualizer.data_loader.GraphDatabase.driver",
        lambda uri, auth: DummyDriver(),
    )


def test_data_loader_collect(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    settings = VisualizerSettings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path,
        sample_data_dir=tmp_path,
    )
    loader = DataLoader(settings)
    payload = loader.collect()
    assert payload["elements"][0]["identifier"] == "E1"
    assert payload["relationships"][0]["identifier"] == "R1"
    assert payload["views"][0]["identifier"] == "V1"


def _settings(tmp_path: Any, uri: str = "bolt://localhost:7687") -> VisualizerSettings:
    return VisualizerSettings(
        neo4j_uri=uri,
        neo4j_user="user",
        neo4j_password="pass",
        cache_dir=tmp_path,
        sample_data_dir=tmp_path,
    )


def test_collect_without_uri_returns_empty_and_opens_no_driver(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    def explode(*_: Any, **__: Any) -> None:
        raise AssertionError("driver must not be opened without a URI")

    monkeypatch.setattr("frictionless_architect.visualizer.data_loader.GraphDatabase.driver", explode)
    loader = DataLoader(_settings(tmp_path, uri=""))
    assert loader.collect() == {"elements": [], "relationships": [], "views": []}


def test_driver_is_opened_once_with_basic_auth_and_reused(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    opened: list[tuple[str, Any]] = []

    def fake_driver(uri: str, auth: Any) -> DummyDriver:
        opened.append((uri, auth))
        return DummyDriver()

    monkeypatch.setattr("frictionless_architect.visualizer.data_loader.GraphDatabase.driver", fake_driver)
    loader = DataLoader(_settings(tmp_path))
    loader.collect()
    loader.collect()
    assert len(opened) == 1
    uri, auth = opened[0]
    assert uri == "bolt://localhost:7687"
    assert (auth.principal, auth.credentials) == ("user", "pass")


def test_close_closes_the_driver_and_allows_reopening(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    drivers: list[ClosableDriver] = []

    def fake_driver(uri: str, auth: Any) -> ClosableDriver:
        drivers.append(ClosableDriver())
        return drivers[-1]

    monkeypatch.setattr("frictionless_architect.visualizer.data_loader.GraphDatabase.driver", fake_driver)
    loader = DataLoader(_settings(tmp_path))
    loader.close()  # no driver yet: a no-op
    loader.collect()
    loader.close()
    assert drivers[0].closed is True
    loader.collect()
    assert len(drivers) == 2


@pytest.mark.parametrize(
    "error",
    (
        Neo4jError("query failed"),
        ServiceUnavailable("Neo4j is down"),
        SessionExpired("connection dropped"),
        AuthError("bad credentials"),
    ),
    ids=("neo4j-error", "service-unavailable", "session-expired", "auth-error"),
)
def test_neo4j_failures_become_data_loader_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, error: Exception
) -> None:
    """Every Neo4j/driver failure must surface as ``DataLoaderError`` so the service degrades to cache/sample."""

    class FailingSession(DummySession):
        def execute_read(self, func: Any) -> Any:
            raise error

    class FailingDriver(DummyDriver):
        def session(self) -> DummySession:
            return FailingSession()

    monkeypatch.setattr(
        "frictionless_architect.visualizer.data_loader.GraphDatabase.driver", lambda uri, auth: FailingDriver()
    )
    with pytest.raises(DataLoaderError, match="Neo4j"):
        DataLoader(_settings(tmp_path)).collect()


def test_connection_failure_while_opening_the_driver_becomes_data_loader_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    def refuse(uri: str, auth: Any) -> None:
        raise ServiceUnavailable("Couldn't connect")

    monkeypatch.setattr("frictionless_architect.visualizer.data_loader.GraphDatabase.driver", refuse)
    with pytest.raises(DataLoaderError):
        DataLoader(_settings(tmp_path)).collect()
