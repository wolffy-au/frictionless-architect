"""Connection settings for the knowledge graph read path and schema manager."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphSettings(BaseSettings):
    """Neo4j connection settings, read from ``FRICTIONLESS_ARCHITECT_*`` env vars or ``.env``.

    The same env prefix flat-`src/`'s ``VisualizerSettings`` already uses, so one Neo4j
    connection is configured once, not twice, during this package's interim period
    alongside flat-`src/`.

    Attributes:
        neo4j_uri: Bolt URI; empty means "no connection configured".
        neo4j_user: Neo4j user name.
        neo4j_password: Neo4j password.
    """

    model_config = SettingsConfigDict(
        env_prefix="FRICTIONLESS_ARCHITECT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""
