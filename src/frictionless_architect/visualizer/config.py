"""Settings for the Neo4j schema visualiser."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class VisualizerSettings(BaseSettings):
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
        return self.sample_data_dir / "sample-00" / "Test Model Full.xml"

    @property
    def cache_path(self) -> Path:
        return self.cache_dir / "schema_payload.json"


@lru_cache(maxsize=1)
def get_visualizer_settings() -> VisualizerSettings:
    return VisualizerSettings()
