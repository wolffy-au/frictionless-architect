"""Loads schema metadata from Neo4j for the visualiser."""

from __future__ import annotations

from typing import Any

from neo4j import Driver, GraphDatabase, basic_auth
from neo4j.exceptions import Neo4jError

from frictionless_architect.visualizer.config import VisualizerSettings


class DataLoaderError(Exception):
    pass


class DataLoader:
    def __init__(self, settings: VisualizerSettings) -> None:
        self._settings = settings
        self._driver: Driver | None = None

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    def collect(self) -> dict[str, list[dict[str, Any]]]:
        if not self._settings.neo4j_uri:
            return {"elements": [], "relationships": [], "views": []}

        try:
            self._ensure_driver()
            assert self._driver is not None
            with self._driver.session() as session:
                elements = session.execute_read(self._fetch_elements)
                relationships = session.execute_read(self._fetch_relationships)
                views = session.execute_read(self._fetch_views)
        except Neo4jError as exc:
            raise DataLoaderError(f"Neo4j query failed: {exc}") from exc
        return {"elements": elements, "relationships": relationships, "views": views}

    def _ensure_driver(self) -> None:
        if self._driver:
            return
        auth = basic_auth(self._settings.neo4j_user, self._settings.neo4j_password)
        self._driver = GraphDatabase.driver(self._settings.neo4j_uri, auth=auth)

    @staticmethod
    def _fetch_elements(tx: Any) -> list[dict[str, Any]]:
        result = tx.run(
            """
            MATCH (e:Element)
            RETURN e.identifier AS identifier,
                   e.type AS type,
                   e.name AS name,
                   e.layer AS layer,
                   e.documentation AS documentation,
                   properties(e) AS properties
            """
        )
        return [row.data() for row in result]

    @staticmethod
    def _fetch_relationships(tx: Any) -> list[dict[str, Any]]:
        result = tx.run(
            """
            MATCH (r:RelationshipFact)
            RETURN r.identifier AS identifier,
                   r.type AS type,
                   r.source_id AS source,
                   r.target_id AS target,
                   properties(r) AS properties
            """
        )
        return [row.data() for row in result]

    @staticmethod
    def _fetch_views(tx: Any) -> list[dict[str, Any]]:
        result = tx.run(
            """
            MATCH (v:View)
            OPTIONAL MATCH (v)-[:REPRESENTS_VIEW]->(d:Diagram)
            RETURN v.identifier AS identifier,
                   v.name AS name,
                   v.viewpoint AS viewpoint,
                   v.viewpointRef AS viewpointRef,
                   properties(v) AS properties,
                   d.identifier AS diagram_id
            """
        )
        return [row.data() for row in result]
