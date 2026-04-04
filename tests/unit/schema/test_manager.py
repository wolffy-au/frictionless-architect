from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from neo4j import Driver, ManagedTransaction

from frictionless_architect.schema import manager as schema_module
from frictionless_architect.schema.manager import SchemaManager, sanitize_label


class DummyTransaction:
    def __init__(self):
        self.queries: list[tuple[object, dict[str, object]]] = []

    def run(self, query, **kwargs):
        self.queries.append((query, kwargs))
        return SimpleNamespace(
            single=lambda: {"sourceExists": True, "targetExists": True},
            data=lambda: [],
        )


class DummySession:
    def __init__(self, tx: DummyTransaction):
        self.tx = tx

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute_write(self, fn, *args, **kwargs):
        return fn(self.tx, *args, **kwargs)

    def execute_read(self, fn, *args, **kwargs):
        return fn(self.tx, *args, **kwargs)

    def run(self, query, **kwargs):
        return self.tx.run(query, **kwargs)


class DummyDriver:
    def __init__(self, session: DummySession):
        self._session = session

    def session(self):
        return self._session


@pytest.fixture
def manager():
    mgr = SchemaManager("bolt://example", "neo4j", "secret")
    old_driver = mgr.driver
    old_driver.close()
    mgr.driver = cast(Driver, DummyDriver(DummySession(DummyTransaction())))
    return mgr


def test_sanitize_label_handles_edges():
    assert sanitize_label("1 Foo-Bar") == "T_1_Foo_Bar"
    assert sanitize_label(None) == ""


def test_apply_constraints_records_all_queries(manager):
    manager.apply_constraints()
    tx = manager.driver._session.tx
    total = len(schema_module.CONSTRAINTS) + len(schema_module.INDEXES)
    assert len(tx.queries) == total


def test_ingest_payload_dispatches(monkeypatch, manager):
    calls = []

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

    payload = {
        "elements": [1, 2],
        "relationships": [1],
        "views": [1],
        "diagrams": [1, 2, 3],
    }
    manager.ingest_payload(payload)
    assert ("elements", 2) in calls
    assert ("relationships", 1) in calls
    assert ("views", 1) in calls
    assert ("diagrams", 3) in calls


def test_ingest_payload_executes_queries(manager):
    payload = {
        "elements": [{"identifier": "E1"}],
        "relationships": [
            {"identifier": "R1", "source": "E1", "target": "E1", "type": "AccessRelationship"}
        ],
        "views": [
            {
                "identifier": "V1",
                "elements": ["E1"],
                "relationships": ["R1"],
                "name": "view",
            }
        ],
        "diagrams": [
            {"identifier": "D1", "viewRef": "V1", "nodes": ["E1"], "connections": ["R1"]}
        ],
    }
    manager.ingest_payload(payload)
    tx = manager.driver._session.tx
    queries = [str(q[0]) for q in tx.queries]
    assert any("MERGE (node:Element" in q for q in queries)
    assert any("MERGE (source)-[rel:ARCHIMATE_RELATIONSHIP" in q for q in queries)
    assert any("MERGE (v:View" in q for q in queries)
    assert any("MERGE (d:Diagram" in q for q in queries)


def test_relationship_missing_nodes_raises():
    class MissingTransaction(DummyTransaction):
        def run(self, query, **kwargs):
            if "OPTIONAL MATCH" in query:
                return SimpleNamespace(single=lambda: {"sourceExists": False, "targetExists": True}, data=lambda: [])
            return super().run(query, **kwargs)

    mgr = SchemaManager("bolt://example", "neo4j", "secret")
    mgr.driver.close()
    mgr.driver = cast(Driver, DummyDriver(DummySession(MissingTransaction())))
    with pytest.raises(ValueError):
        mgr.ingest_payload(
            {
                "elements": [{"identifier": "E1"}],
                "relationships": [{"identifier": "R1", "source": "missing", "target": "E1"}],
                "views": [],
                "diagrams": [],
            }
        )


def test_static_find_helpers():
    class Row:
        def __init__(self, data):
            self._data = data

        def data(self):
            return self._data

    class Result:
        def __init__(self, rows):
            self._rows = rows

        def __iter__(self):
            return iter(self._rows)

    class ResultTransaction(DummyTransaction):
        def __init__(self, rows):
            super().__init__()
            self._rows = rows

        def run(self, query, **kwargs):
            return Result([Row(r) for r in self._rows])

    tx_missing = ResultTransaction([{"identifier": "R1", "missing": "source"}])
    tx_orphan = ResultTransaction([{"identifier": "V1", "kind": "elements"}])
    missing = SchemaManager._find_missing_relationship_targets(cast(ManagedTransaction, tx_missing))
    orphan = SchemaManager._find_orphan_views(cast(ManagedTransaction, tx_orphan))
    assert missing[0]["identifier"] == "R1"
    assert orphan[0]["kind"] == "elements"


def test_record_schema_version_and_audit(monkeypatch, manager):
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
