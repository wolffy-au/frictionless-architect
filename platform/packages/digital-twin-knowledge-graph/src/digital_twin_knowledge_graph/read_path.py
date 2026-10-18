"""Knowledge graph read path (`if-twin-read-path`), ported from flat-`src/`'s
`frictionless_architect.visualizer.data_loader` (`DataLoader` -> `KnowledgeGraphReadPath`,
`DataLoaderError` -> `ReadPathError`, research.md R5 — behaviorally identical, FR-011).
"""

from __future__ import annotations

from typing import Any

from neo4j import Driver, GraphDatabase, basic_auth
from neo4j.exceptions import DriverError, Neo4jError

from digital_twin_knowledge_graph.config import GraphSettings


class ReadPathError(Exception):
    """Raised when Neo4j cannot be reached or a query for schema metadata fails."""


class KnowledgeGraphReadPath:
    """Read-only reader of elements, relationships and views from Neo4j.

    Returns plain data only — no `neo4j` driver, session or record type ever crosses this
    class's public boundary (FR-002).
    """

    def __init__(self, settings: GraphSettings) -> None:
        """Create a read path; the driver is opened lazily on first ``collect``.

        Args:
            settings: Connection settings supplying the Neo4j URI and credentials.
        """
        self._settings = settings
        self._driver: Driver | None = None

    def close(self) -> None:
        """Close the Neo4j driver if one was opened."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def collect(self) -> dict[str, list[dict[str, Any]]]:
        """Fetch all elements, relationships and views.

        Returns:
            A mapping with ``elements``, ``relationships`` and ``views`` lists; all
            empty when no Neo4j URI is configured (FR-003).

        Raises:
            ReadPathError: If Neo4j is unreachable (``ServiceUnavailable``, ``SessionExpired``,
                other driver errors) or a query fails (``Neo4jError``, including ``AuthError``).
        """
        if not self._settings.neo4j_uri:
            return {"elements": [], "relationships": [], "views": []}

        try:
            with self._ensure_driver().session() as session:
                elements = session.execute_read(self._fetch_elements)
                relationships = session.execute_read(self._fetch_relationships)
                views = session.execute_read(self._fetch_views)
        except (Neo4jError, DriverError) as exc:
            raise ReadPathError(f"Neo4j query failed: {exc}") from exc
        return {"elements": elements, "relationships": relationships, "views": views}

    def _ensure_driver(self) -> Driver:
        if self._driver is None:
            auth = basic_auth(self._settings.neo4j_user, self._settings.neo4j_password)
            self._driver = GraphDatabase.driver(self._settings.neo4j_uri, auth=auth)
        return self._driver

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
            MATCH (source:Element)-[r:ARCHIMATE_RELATIONSHIP]->(target:Element)
            RETURN r.identifier AS identifier,
                   r.type AS type,
                   source.identifier AS source,
                   target.identifier AS target,
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
