#!/usr/bin/env python3
"""Core schema management utilities for the ArchiMate graph."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, LiteralString, cast

from neo4j import GraphDatabase, ManagedTransaction, basic_auth

CONSTRAINTS = [
    "CREATE CONSTRAINT element_identifier IF NOT EXISTS FOR (e:Element) REQUIRE e.identifier IS UNIQUE",
    "CREATE CONSTRAINT relationship_identifier IF NOT EXISTS FOR (r:RelationshipFact) REQUIRE r.identifier IS UNIQUE",
    "CREATE CONSTRAINT view_identifier IF NOT EXISTS FOR (v:View) REQUIRE v.identifier IS UNIQUE",
    "CREATE CONSTRAINT diagram_identifier IF NOT EXISTS FOR (d:Diagram) REQUIRE d.identifier IS UNIQUE",
    "CREATE CONSTRAINT viewpoint_identifier IF NOT EXISTS FOR (vp:Viewpoint) REQUIRE vp.identifier IS UNIQUE",
    "CREATE CONSTRAINT schema_version_name IF NOT EXISTS FOR (sv:SchemaVersion) REQUIRE sv.name IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX element_type_index IF NOT EXISTS FOR (e:Element) ON (e.type)",
    "CREATE INDEX element_layer_index IF NOT EXISTS FOR (e:Element) ON (e.layer)",
    "CREATE INDEX relationship_type_index IF NOT EXISTS FOR (r:RelationshipFact) ON (r.type)",
    "CREATE INDEX view_name_index IF NOT EXISTS FOR (v:View) ON (v.name)",
    "CREATE INDEX diagram_name_index IF NOT EXISTS FOR (d:Diagram) ON (d.name)",
]

_LABEL_SANITIZER = re.compile(r"\W")


def _run_literal(tx: ManagedTransaction, statement: object, **parameters: Any) -> Any:
    return tx.run(cast(LiteralString, statement), **parameters)


def sanitize_label(value: str | None) -> str:
    """Sanitize a string so it can safely become a Neo4j label."""

    if not value:
        return ""

    cleaned = _LABEL_SANITIZER.sub("_", value.strip())
    if not cleaned:
        return ""

    if not cleaned[0].isalpha():
        cleaned = f"T_{cleaned}"

    return cleaned


class SchemaManager:
    """Controller for Neo4j constraints, ingestion, migrations, and audits."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        auth = basic_auth(user, password)
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self) -> None:
        self.driver.close()

    def apply_constraints(self) -> None:
        with self.driver.session() as session:
            for statement in CONSTRAINTS + INDEXES:
                session.execute_write(self._run_statement, statement)

    @staticmethod
    def _run_statement(tx: ManagedTransaction, statement: str) -> None:
        _run_literal(tx, statement)

    def ingest_payload(self, payload: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
        elements = payload.get("elements", [])
        relationships = payload.get("relationships", [])
        views = payload.get("views", [])
        diagrams = payload.get("diagrams", [])

        with self.driver.session() as session:
            if elements:
                session.execute_write(self._ingest_elements, elements)
            if relationships:
                session.execute_write(self._ingest_relationships, relationships)
            if views:
                session.execute_write(self._ingest_views, views)
            if diagrams:
                session.execute_write(self._ingest_diagrams, diagrams)

    @staticmethod
    def _ingest_elements(tx: ManagedTransaction, elements: Iterable[Mapping[str, Any]]) -> None:
        for element in elements:
            identifier = element["identifier"]
            element_type = element.get("type", "Element")
            label = sanitize_label(element_type)
            label_clause = f":{label}" if label else ""
            data_properties = element.get("properties", {}) or {}
            _run_literal(
                tx,
                f"""
MERGE (node:Element {{identifier:$identifier}})
SET node.type = $type, node.layer = $layer, node.name = $name, node.documentation = $documentation
{f"SET node{label_clause}" if label_clause else ""}
SET node += $additional
""",
                identifier=identifier,
                type=element_type,
                layer=element.get("layer"),
                name=element.get("name"),
                documentation=element.get("documentation"),
                additional=data_properties,
            )

    @staticmethod
    def _ingest_relationships(
        tx: ManagedTransaction, relationships: Iterable[Mapping[str, Any]]
    ) -> None:
        for relationship in relationships:
            identifier = relationship["identifier"]
            source_id = relationship["source"]
            target_id = relationship["target"]
            rel_type = relationship.get("type", "ArchimateRelationship")
            rel_properties = relationship.get("properties", {}) or {}

            existence = _run_literal(
                tx,
                """OPTIONAL MATCH (source:Element {identifier:$source})
OPTIONAL MATCH (target:Element {identifier:$target})
RETURN source IS NOT NULL AS sourceExists, target IS NOT NULL AS targetExists""",
                source=source_id,
                target=target_id,
            ).single()

            if not existence or not (existence["sourceExists"] and existence["targetExists"]):
                missing = []
                if not existence or not existence["sourceExists"]:
                    missing.append("source")
                if not existence or not existence["targetExists"]:
                    missing.append("target")
                raise ValueError(
                    f"Relationship {identifier} references missing {', '.join(missing)} node(s)."
                )

            _run_literal(
                tx,
                """MATCH (source:Element {identifier:$source})
MATCH (target:Element {identifier:$target})
MERGE (source)-[rel:ARCHIMATE_RELATIONSHIP {identifier:$identifier}]->(target)
SET rel.type = $type, rel += $properties""",
                source=source_id,
                target=target_id,
                identifier=identifier,
                type=rel_type,
                properties=rel_properties,
            )

            _run_literal(
                tx,
                """MERGE (meta:RelationshipFact {identifier:$identifier})
SET meta.type = $type, meta.source_id = $source, meta.target_id = $target, meta += $properties
WITH meta
MATCH (source:Element {identifier:$source}), (target:Element {identifier:$target})
MERGE (meta)-[:SOURCE_ELEMENT]->(source)
MERGE (meta)-[:TARGET_ELEMENT]->(target)""",
                identifier=identifier,
                type=rel_type,
                source=source_id,
                target=target_id,
                properties=rel_properties,
            )

    @staticmethod
    def _ingest_views(tx: ManagedTransaction, views: Iterable[Mapping[str, Any]]) -> None:
        for view in views:
            identifier = view["identifier"]
            view_props = view.get("properties", {}) or {}
            _run_literal(
                tx,
                """MERGE (v:View {identifier:$identifier})
SET v.name = $name, v.viewpoint = $viewpoint, v.viewpointRef = $viewpointRef
SET v += $properties""",
                identifier=identifier,
                name=view.get("name"),
                viewpoint=view.get("viewpoint"),
                viewpointRef=view.get("viewpointRef"),
                properties=view_props,
            )

            for element_id in view.get("elements", []):
                _run_literal(
                    tx,
                    """MATCH (v:View {identifier:$view_id})
MATCH (element:Element {identifier:$element_id})
MERGE (v)-[:INCLUDES]->(element)""",
                    view_id=identifier,
                    element_id=element_id,
                )

            for relationship_id in view.get("relationships", []):
                _run_literal(
                    tx,
                    """MATCH (v:View {identifier:$view_id})
MATCH (relationship:RelationshipFact {identifier:$relationship_id})
MERGE (v)-[:HAS_RELATIONSHIP]->(relationship)""",
                    view_id=identifier,
                    relationship_id=relationship_id,
                )

    @staticmethod
    def _ingest_diagrams(tx: ManagedTransaction, diagrams: Iterable[Mapping[str, Any]]) -> None:
        for diagram in diagrams:
            identifier = diagram["identifier"]
            diagram_props = diagram.get("properties", {}) or {}
            _run_literal(
                tx,
                """MERGE (d:Diagram {identifier:$identifier})
SET d.name = $name, d.viewRef = $view_ref, d.viewpoint = $viewpoint
SET d += $properties""",
                identifier=identifier,
                name=diagram.get("name"),
                view_ref=diagram.get("viewRef"),
                viewpoint=diagram.get("viewpoint"),
                properties=diagram_props,
            )

            if diagram.get("viewRef"):
                _run_literal(
                    tx,
                    """MATCH (d:Diagram {identifier:$diagram_id})
MATCH (v:View {identifier:$view_id})
MERGE (d)-[:REPRESENTS_VIEW]->(v)""",
                    diagram_id=identifier,
                    view_id=diagram["viewRef"],
                )

            for node_id in diagram.get("nodes", []):
                _run_literal(
                    tx,
                    """MATCH (d:Diagram {identifier:$diagram_id})
MATCH (element:Element {identifier:$node_id})
MERGE (d)-[:HAS_NODE]->(element)""",
                    diagram_id=identifier,
                    node_id=node_id,
                )

            for connection_id in diagram.get("connections", []):
                _run_literal(
                    tx,
                    """MATCH (d:Diagram {identifier:$diagram_id})
MATCH (relationship:RelationshipFact {identifier:$connection_id})
MERGE (d)-[:HAS_CONNECTION]->(relationship)""",
                    diagram_id=identifier,
                    connection_id=connection_id,
                )

    def record_schema_version(self, name: str) -> None:
        with self.driver.session() as session:
            session.execute_write(self._ensure_schema_version, name)

    @staticmethod
    def _ensure_schema_version(tx: ManagedTransaction, name: str) -> None:
        _run_literal(
            tx,
            """MERGE (sv:SchemaVersion {name:$name})
SET sv.applied_at = datetime($timestamp)""",
            name=name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def run_audit_checks(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        with self.driver.session() as session:
            missing_relations = session.execute_read(self._find_missing_relationship_targets)
            orphan_views = session.execute_read(self._find_orphan_views)
        return missing_relations, orphan_views

    @staticmethod
    def _find_missing_relationship_targets(tx: ManagedTransaction) -> list[dict[str, Any]]:
        result = _run_literal(
            tx,
            """MATCH (rel:RelationshipFact)
WITH rel, [(rel.source_id IS NULL) AS sourceMissing, (rel.target_id IS NULL) AS targetMissing]
WHERE sourceMissing OR targetMissing
RETURN rel.identifier AS identifier,
       CASE WHEN rel.source_id IS NULL THEN 'source' ELSE '' END + CASE WHEN rel.target_id IS NULL THEN ' target' ELSE '' END AS missing""",
        )
        return [row.data() for row in result]

    @staticmethod
    def _find_orphan_views(tx: ManagedTransaction) -> list[dict[str, Any]]:
        result = _run_literal(
            tx,
            """MATCH (v:View)
WITH v, size((v)-[:INCLUDES]->(:Element)) AS elements,
     size((v)-[:HAS_RELATIONSHIP]->(:RelationshipFact)) AS relationships
WHERE elements = 0 OR relationships = 0
RETURN v.identifier AS identifier,
       CASE WHEN elements = 0 THEN 'elements' ELSE 'relationships' END AS kind""",
        )
        return [row.data() for row in result]
