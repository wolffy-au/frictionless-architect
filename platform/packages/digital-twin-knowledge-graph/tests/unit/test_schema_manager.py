"""Unit tests for the Neo4j schema manager.

Ported from flat-`src/`'s `tests/unit/schema/test_manager.py` (FR-011) — same assertions,
re-targeted at `digital_twin_knowledge_graph.schema_manager.SchemaManager`
(`ingest_payload` renamed to `ingest`, data-model.md).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from digital_twin_knowledge_graph import schema_manager as schema_module
from digital_twin_knowledge_graph.schema_manager import SchemaManager, sanitize_label
from neo4j import Driver, ManagedTransaction


class DummyTransaction:
    def __init__(self) -> None:
        self.queries: list[tuple[object, dict[str, object]]] = []

    def run(self, query: object, **kwargs: Any) -> SimpleNamespace:
        self.queries.append((query, kwargs))
        return SimpleNamespace(
            single=lambda: {"sourceExists": True, "targetExists": True},
            data=lambda: [],
        )


class DummySession:
    def __init__(self, tx: DummyTransaction) -> None:
        self.tx = tx

    def __enter__(self) -> DummySession:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute_write(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        return fn(self.tx, *args, **kwargs)

    def execute_read(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        return fn(self.tx, *args, **kwargs)

    def run(self, query: object, **kwargs: Any) -> Any:
        return self.tx.run(query, **kwargs)


class DummyDriver:
    def __init__(self, session: DummySession) -> None:
        self._session = session
        self.closed = False

    def session(self) -> DummySession:
        return self._session

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def manager() -> SchemaManager:
    mgr = SchemaManager("bolt://example", "neo4j", "secret")
    old_driver = mgr.driver
    old_driver.close()
    mgr.driver = cast(Driver, DummyDriver(DummySession(DummyTransaction())))
    return mgr


def test_sanitize_label_handles_edges() -> None:
    assert sanitize_label("1 Foo-Bar") == "T_1_Foo_Bar"
    assert sanitize_label(None) == ""
    assert sanitize_label("   ") == ""


def test_close_closes_driver() -> None:
    mgr = SchemaManager("bolt://example", "neo4j", "secret")
    mgr.driver = cast(Driver, DummyDriver(DummySession(DummyTransaction())))
    mgr.close()
    assert cast(DummyDriver, mgr.driver).closed is True


def test_apply_constraints_records_all_queries(manager: SchemaManager) -> None:
    manager.apply_constraints()
    tx = cast(DummyDriver, manager.driver)._session.tx
    total = len(schema_module.CONSTRAINTS) + len(schema_module.INDEXES)
    assert len(tx.queries) == total


def test_ingest_dispatches(monkeypatch: pytest.MonkeyPatch, manager: SchemaManager) -> None:
    calls: list[tuple[str, int]] = []

    monkeypatch.setattr(
        SchemaManager,
        "_ingest_elements",
        staticmethod(lambda tx, elements: calls.append(("elements", len(elements)))),
    )
    monkeypatch.setattr(
        SchemaManager,
        "_ingest_relationships",
        staticmethod(lambda tx, relationships: calls.append(("relationships", len(relationships)))),
    )
    monkeypatch.setattr(
        SchemaManager,
        "_ingest_views",
        staticmethod(lambda tx, views: calls.append(("views", len(views)))),
    )
    monkeypatch.setattr(
        SchemaManager,
        "_ingest_diagrams",
        staticmethod(lambda tx, diagrams: calls.append(("diagrams", len(diagrams)))),
    )

    payload: dict[str, list[Any]] = {
        "elements": [1, 2],
        "relationships": [1],
        "views": [1],
        "diagrams": [1, 2, 3],
    }
    manager.ingest(payload)
    assert ("elements", 2) in calls
    assert ("relationships", 1) in calls
    assert ("views", 1) in calls
    assert ("diagrams", 3) in calls


def test_ingest_executes_queries(manager: SchemaManager) -> None:
    payload: dict[str, list[dict[str, Any]]] = {
        "elements": [{"identifier": "E1"}],
        "relationships": [{"identifier": "R1", "source": "E1", "target": "E1", "type": "AccessRelationship"}],
        "views": [
            {
                "identifier": "V1",
                "elements": ["E1"],
                "relationships": ["R1"],
                "name": "view",
            }
        ],
        "diagrams": [{"identifier": "D1", "viewRef": "V1", "nodes": ["E1"], "connections": ["R1"]}],
    }
    manager.ingest(payload)
    tx = cast(DummyDriver, manager.driver)._session.tx
    queries = [str(q[0]) for q in tx.queries]
    assert any("MERGE (node:Element" in q for q in queries)
    assert any("MERGE (source)-[rel:ARCHIMATE_RELATIONSHIP" in q for q in queries)
    assert any("MERGE (v:View" in q for q in queries)
    assert any("MERGE (d:Diagram" in q for q in queries)


def test_relationship_missing_nodes_raises() -> None:
    class MissingTransaction(DummyTransaction):
        def run(self, query: object, **kwargs: Any) -> SimpleNamespace:
            if "OPTIONAL MATCH" in str(query):
                return SimpleNamespace(single=lambda: {"sourceExists": False, "targetExists": True}, data=lambda: [])
            return super().run(query, **kwargs)

    mgr = SchemaManager("bolt://example", "neo4j", "secret")
    mgr.driver.close()
    mgr.driver = cast(Driver, DummyDriver(DummySession(MissingTransaction())))
    with pytest.raises(ValueError):
        mgr.ingest(
            {
                "elements": [{"identifier": "E1"}],
                "relationships": [{"identifier": "R1", "source": "missing", "target": "E1"}],
                "views": [],
                "diagrams": [],
            }
        )


def test_relationship_missing_target_raises(manager: SchemaManager) -> None:
    class MissingTargetTransaction(DummyTransaction):
        def run(self, query: object, **kwargs: Any) -> SimpleNamespace:
            if "OPTIONAL MATCH" in str(query):
                return SimpleNamespace(single=lambda: {"sourceExists": True, "targetExists": False}, data=lambda: [])
            return super().run(query, **kwargs)

    manager.driver = cast(Driver, DummyDriver(DummySession(MissingTargetTransaction())))
    with pytest.raises(ValueError, match="target"):
        manager.ingest(
            {
                "elements": [{"identifier": "E1"}],
                "relationships": [{"identifier": "R1", "source": "E1", "target": "missing"}],
            }
        )


def test_ingest_each_payload_section_alone(manager: SchemaManager) -> None:
    tx = cast(DummyDriver, manager.driver)._session.tx
    manager.ingest({})
    assert tx.queries == []

    manager.ingest({"relationships": [{"identifier": "R1", "source": "E1", "target": "E1"}]})
    manager.ingest({"views": [{"identifier": "V1"}]})
    manager.ingest({"diagrams": [{"identifier": "D1"}]})
    queries = [str(q[0]) for q in tx.queries]
    assert any("ARCHIMATE_RELATIONSHIP" in q for q in queries)
    assert any("MERGE (v:View" in q for q in queries)
    assert any("MERGE (d:Diagram" in q for q in queries)


def test_ingest_diagram_without_view_ref_skips_link(manager: SchemaManager) -> None:
    manager.ingest({"diagrams": [{"identifier": "D1", "nodes": ["E1"]}]})
    tx = cast(DummyDriver, manager.driver)._session.tx
    queries = [str(q[0]) for q in tx.queries]
    assert not any("REPRESENTS_VIEW" in q for q in queries)
    assert any("HAS_NODE" in q for q in queries)


def test_static_find_helpers() -> None:
    class Row:
        def __init__(self, data: dict[str, Any]) -> None:
            self._data = data

        def data(self) -> dict[str, Any]:
            return self._data

    class Result:
        def __init__(self, rows: list[Row]) -> None:
            self._rows = rows

        def __iter__(self) -> Any:
            return iter(self._rows)

    class ResultTransaction(DummyTransaction):
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            super().__init__()
            self._rows = rows

        def run(self, query: object, **kwargs: Any) -> Any:
            return Result([Row(r) for r in self._rows])

    tx_missing = ResultTransaction([{"identifier": "R1", "missing": "source"}])
    tx_orphan = ResultTransaction([{"identifier": "V1", "kind": "elements"}])
    missing = SchemaManager._find_missing_relationship_targets(cast(ManagedTransaction, tx_missing))
    orphan = SchemaManager._find_orphan_views(cast(ManagedTransaction, tx_orphan))
    assert missing[0]["identifier"] == "R1"
    assert orphan[0]["kind"] == "elements"


def test_record_schema_version_and_audit(monkeypatch: pytest.MonkeyPatch, manager: SchemaManager) -> None:
    monkeypatch.setattr(
        SchemaManager,
        "_find_missing_relationship_targets",
        staticmethod(lambda tx: [{"identifier": "rel", "missing": "source"}]),
    )
    monkeypatch.setattr(
        SchemaManager,
        "_find_orphan_views",
        staticmethod(lambda tx: [{"identifier": "view", "kind": "elements"}]),
    )

    manager.record_schema_version("v1")
    missing, orphan = manager.run_audit_checks()
    assert missing[0]["identifier"] == "rel"
    assert orphan[0]["identifier"] == "view"
