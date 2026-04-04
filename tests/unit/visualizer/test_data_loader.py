"""Unit tests for the visualiser Neo4j data loader."""

from __future__ import annotations

from typing import Any

import pytest

from frictionless_architect.visualizer.config import VisualizerSettings
from frictionless_architect.visualizer.data_loader import DataLoader


class DummyRow:
    def __init__(self, row: dict[str, Any]) -> None:
        self._row = row

    def data(self) -> dict[str, Any]:
        return self._row


class DummyTx:
    def run(self, query: str) -> list[DummyRow]:
        if "MATCH (e:Element)" in query:
            return [DummyRow({"identifier": "E1", "type": "Element"})]
        if "MATCH (r:RelationshipFact)" in query:
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
