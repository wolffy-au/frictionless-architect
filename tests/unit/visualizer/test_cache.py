"""Tests for the visualiser payload cache utilities."""

from __future__ import annotations

from pathlib import Path

from frictionless_architect.visualizer.cache import SchemaCache


def test_schema_cache_load_and_save(tmp_path: Path) -> None:
    cache_path = tmp_path / "visualiser" / "schema_payload.json"
    cache = SchemaCache(cache_path)
    assert cache.load() is None
    cache.save({"model": {"identifier": "m"}})
    loaded = cache.load()
    assert loaded == {"model": {"identifier": "m"}}
