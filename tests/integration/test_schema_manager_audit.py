"""Regression tests for SchemaManager.run_audit_checks against a live Neo4j server.

These queries were broken by Cypher syntax errors that the unit-level tests in
tests/unit/schema/test_manager.py could not catch, because those tests replace
the transaction with a dummy that never parses the query string. Only a real
Neo4j engine rejects invalid Cypher, so these audit queries need to run
against one.

ADR-0028 dropped the RelationshipFact node in favour of storing relationships
as bare edges, with View/Diagram referencing them via relationshipIds /
connectionIds identifier lists. These tests were updated accordingly: the
"missing" check now looks for a list entry with no matching edge, rather than
an edge with a missing endpoint (which can no longer happen).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from neo4j.exceptions import ServiceUnavailable

from frictionless_architect.schema.manager import SchemaManager

ROOT = Path(__file__).resolve().parents[2]


def _connection_kwargs() -> dict[str, str] | None:
    env = {**dotenv_values(ROOT / ".env"), **os.environ}
    uri = env.get("NEO4J_URI")
    user = env.get("NEO4J_USER")
    password = env.get("NEO4J_PASSWORD")
    if not (uri and user and password):
        return None
    return {"uri": uri, "user": user, "password": password}


@pytest.fixture
def manager():
    kwargs = _connection_kwargs()
    if kwargs is None:
        pytest.skip("NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD not configured")

    mgr = SchemaManager(kwargs["uri"], kwargs["user"], kwargs["password"])
    try:
        mgr.driver.verify_connectivity()
    except ServiceUnavailable:
        mgr.close()
        pytest.skip("Neo4j server is not reachable")

    yield mgr
    mgr.close()


def test_find_missing_relationship_targets_is_valid_cypher(manager):
    """Regression: WITH rel, [(...) AS x, (...) AS y] is not valid list syntax."""
    missing, _ = manager.run_audit_checks()
    assert isinstance(missing, list)


def test_find_orphan_views_is_valid_cypher(manager):
    """Regression: size((v)-[:REL]->()) on a pattern expression was rejected."""
    _, orphan = manager.run_audit_checks()
    assert isinstance(orphan, list)


def test_find_missing_relationship_targets_detects_dangling_view_reference(manager):
    with manager.driver.session() as session:
        session.run(
            "MERGE (v:View {identifier: $identifier}) "
            "SET v.name = 'Dangling ref test view', v.relationshipIds = ['does-not-exist']",
            identifier="test-dangling-view",
        )
    try:
        missing, _ = manager.run_audit_checks()
        matches = [row for row in missing if row["identifier"] == "test-dangling-view"]
        assert matches
        assert matches[0]["kind"] == "view"
        assert matches[0]["missing"] == "does-not-exist"
    finally:
        with manager.driver.session() as session:
            session.run(
                "MATCH (v:View {identifier: $identifier}) DETACH DELETE v",
                identifier="test-dangling-view",
            )


def test_find_missing_relationship_targets_detects_dangling_diagram_reference(manager):
    with manager.driver.session() as session:
        session.run(
            "MERGE (d:Diagram {identifier: $identifier}) "
            "SET d.name = 'Dangling ref test diagram', d.connectionIds = ['does-not-exist']",
            identifier="test-dangling-diagram",
        )
    try:
        missing, _ = manager.run_audit_checks()
        matches = [row for row in missing if row["identifier"] == "test-dangling-diagram"]
        assert matches
        assert matches[0]["kind"] == "diagram"
    finally:
        with manager.driver.session() as session:
            session.run(
                "MATCH (d:Diagram {identifier: $identifier}) DETACH DELETE d",
                identifier="test-dangling-diagram",
            )


def test_find_orphan_views_detects_view_with_no_elements(manager):
    with manager.driver.session() as session:
        session.run(
            "MERGE (v:View {identifier: $identifier}) SET v.name = 'Orphan test view'",
            identifier="test-orphan-view",
        )
    try:
        _, orphan = manager.run_audit_checks()
        identifiers = {row["identifier"] for row in orphan}
        assert "test-orphan-view" in identifiers
    finally:
        with manager.driver.session() as session:
            session.run(
                "MATCH (v:View {identifier: $identifier}) DETACH DELETE v",
                identifier="test-orphan-view",
            )
