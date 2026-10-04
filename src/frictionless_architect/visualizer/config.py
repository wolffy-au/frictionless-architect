"""Settings for the Neo4j schema visualiser."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class VisualizerSettings(BaseSettings):
    """Visualiser settings, read from ``FRICTIONLESS_ARCHITECT_*`` env vars or ``.env``.

    Attributes:
        neo4j_uri: Bolt URI; empty means "sample data only".
        neo4j_user: Neo4j user name.
        neo4j_password: Neo4j password.
        sample_data_dir: Directory holding ``sample-00/Test Model Full.xml`` and ``schema/``.
        cache_dir: Directory for the cached payload.
        warning_text: Warning raised when the sample model cannot be read.
        refresh_backoff_seconds: Seconds after a successful refresh during which
            ``POST /schema-payload/refresh`` answers 429 (failed refreshes are not delayed).
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
    sample_data_dir: Path = Path("sample-data")
    cache_dir: Path = Path(".cache/visualiser")
    warning_text: str = "Sample data unavailable"
    refresh_backoff_seconds: int = 300

    @property
    def sample_model_path(self) -> Path:
        """Path of the enriched sample model XML."""
        return self.sample_data_dir / "sample-00" / "Test Model Full.xml"

    @property
    def schema_diagram_xsd_path(self) -> Path:
        """Entry XSD for validating the sample: includes the View and Model schemas."""
        return self.sample_data_dir / "schema" / "archimate3_Diagram.xsd"

    @property
    def cache_path(self) -> Path:
        """Path of the cached payload file (``schema_payload.json``)."""
        return self.cache_dir / "schema_payload.json"


@lru_cache(maxsize=1)
def get_visualizer_settings() -> VisualizerSettings:
    """Return the process-wide settings instance (cached after first call)."""
    return VisualizerSettings()
