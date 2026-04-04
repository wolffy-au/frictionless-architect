"""API surface for the schema visualiser."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from xml.etree.ElementTree import ParseError

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from frictionless_architect.visualizer.cache import SchemaCache
from frictionless_architect.visualizer.config import VisualizerSettings, get_visualizer_settings
from frictionless_architect.visualizer.data_loader import DataLoader, DataLoaderError
from frictionless_architect.visualizer.sample_parser import SampleParser, SampleParseResult


class PayloadUnavailable(Exception):
    def __init__(self, message: str, warnings: list[str] | None = None) -> None:
        super().__init__(message)
        self.warnings = warnings or []


class RefreshInProgress(Exception):
    pass


class RefreshRequest(BaseModel):
    source: str | None = None


class SchemaPayloadService:
    def __init__(self, settings: "VisualizerSettings", parser: SampleParser, loader: DataLoader, cache: SchemaCache) -> None:
        self.settings = settings
        self.parser = parser
        self.loader = loader
        self.cache = cache
        self._build_lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[Any] | None = None
        self._last_refresh_started: datetime | None = None
        self._last_refresh_completed: datetime | None = None
        self._last_latency_ms: int | None = None
        self._neo4j_status = "disabled"
        self._sample_status = "missing"
        self._last_warning = ""

    async def get_payload(self, force_reload: bool = False) -> dict[str, Any]:
        cached = self.cache.load()
        if force_reload or cached is None:
            try:
                return await self._build_and_cache()
            except PayloadUnavailable as exc:
                if exc.warnings:
                    self._last_warning = exc.warnings[-1]
                if cached is not None:
                    return cached
                raise exc
        return cached

    async def request_refresh(self) -> int:
        if self._refresh_task and not self._refresh_task.done():
            raise RefreshInProgress()
        estimate = max(500, (self._last_latency_ms or 1200) * 2)
        self._refresh_task = asyncio.create_task(self._background_refresh())
        return estimate

    async def _build_and_cache(self) -> dict[str, Any]:
        async with self._build_lock:
            self._last_refresh_started = datetime.now(timezone.utc)
            payload, neo4j_status, sample_status, warnings, latency = await asyncio.to_thread(self._build_payload)
            self._last_latency_ms = latency
            self._neo4j_status = neo4j_status
            self._sample_status = sample_status
            self._last_warning = warnings[-1] if warnings else ""
            await asyncio.to_thread(self.cache.save, payload)
            self._last_refresh_completed = datetime.now(timezone.utc)
            return payload

    async def _background_refresh(self) -> None:
        try:
            await self._build_and_cache()
        except PayloadUnavailable:
            # preserve cache if build fails
            pass
        finally:
            self._refresh_task = None

    def get_status(self) -> dict[str, Any]:
        age = self.cache.age_seconds()
        status = {
            "cache_age_seconds": int(age) if age is not None else None,
            "neo4j_status": self._neo4j_status,
            "sample_file_status": self._sample_status,
            "last_warning": self._last_warning,
            "refresh_in_progress": bool(self._refresh_task and not self._refresh_task.done()),
        }
        if self._last_refresh_started:
            status["last_refresh_started"] = self._last_refresh_started.isoformat()
        if self._last_refresh_completed:
            status["last_refresh_completed"] = self._last_refresh_completed.isoformat()
        return status

    def _build_payload(self) -> tuple[dict[str, Any], str, str, list[str], int]:
        start = time.monotonic()
        warnings: list[str] = []
        seen: set[str] = set()

        def add_warning(text: str) -> None:
            if not text or text in seen:
                return
            seen.add(text)
            warnings.append(text)

        sample_status = "missing"
        try:
            sample_result = self.parser.parse()
            sample_status = "loaded"
        except (FileNotFoundError, ParseError):
            add_warning(self.settings.warning_text)
            sample_result = SampleParseResult.empty(self.settings.sample_model_path)

        schema_status = "disabled"
        schema_payload: dict[str, list[dict[str, Any]]] = {"elements": [], "relationships": [], "views": []}
        if self.settings.neo4j_uri:
            try:
                schema_payload = self.loader.collect()
                schema_status = "available"
            except DataLoaderError as exc:
                schema_status = "unavailable"
                add_warning(str(exc))
        else:
            schema_status = "disabled"

        if not schema_payload["elements"] and not sample_result.elements:
            raise PayloadUnavailable(
                "Schema data unavailable; no Neo4j connection or sample data.",
                warnings=list(warnings),
            )

        model_payload = sample_result.model or {
            "identifier": "schema",
            "name": "ArchiMate Schema",
        }
        model_payload["source_file"] = "archimate3_Model.xsd"

        relationship_ids: set[str] = {
            identifier
            for rel in schema_payload["relationships"]
            if (identifier := rel.get("identifier")) and isinstance(identifier, str)
        }
        elements = self._merge_elements(
            schema_payload["elements"],
            sample_result.elements,
            add_warning,
            relationship_ids,
        )
        relationships = self._merge_relationships(schema_payload["relationships"], sample_result.relationships, add_warning)
        views = [
            {**view, "source_file": "archimate3_View.xsd"}
            for view in sample_result.views
        ]

        payload: dict[str, Any] = {
            "model": model_payload,
            "elements": elements,
            "relationships": relationships,
            "views": views,
            "warnings": warnings,
        }
        payload["latency_ms"] = int((time.monotonic() - start) * 1000)
        return payload, schema_status, sample_status, warnings, payload["latency_ms"]

    def _merge_elements(
        self,
        schema_elements: list[dict[str, Any]],
        sample_elements: dict[str, dict[str, Any]],
        add_warning: Any,
        relationship_ids: set[str],
    ) -> list[dict[str, Any]]:
        model_file = "archimate3_Model.xsd"
        schema_map = {
            el.get("identifier"): el for el in schema_elements if el.get("identifier")
        }
        ids = sorted(
            identifier
            for identifier in set(schema_map) | set(sample_elements)
            if identifier is not None and identifier not in relationship_ids
        )
        result = []
        for identifier in ids:
            schema_entry = schema_map.get(identifier, {})
            sample_entry = sample_elements.get(identifier)
            node_type = schema_entry.get("type") or (sample_entry and sample_entry.get("type")) or "Element"
            name = schema_entry.get("name") or (sample_entry and sample_entry.get("name")) or identifier
            coverage = sample_entry is not None
            entry = {
                "identifier": identifier,
                "type": node_type,
                "name": name,
                "layer": schema_entry.get("layer"),
                "documentation": schema_entry.get("documentation"),
                "source_file": model_file,
                "properties": schema_entry.get("properties") or {},
                "sample_instances": [sample_entry] if sample_entry else [],
                "coverage": coverage,
            }
            if not coverage:
                add_warning(f"Missing sample entry for {node_type} {name}")
            result.append(entry)
        return result

    def _merge_relationships(
        self,
        schema_relationships: list[dict[str, Any]],
        sample_relationships: dict[str, dict[str, Any]],
        add_warning: Any,
    ) -> list[dict[str, Any]]:
        model_file = "archimate3_Model.xsd"
        schema_map = {
            rel.get("identifier"): rel for rel in schema_relationships if rel.get("identifier")
        }
        ids = sorted(
            identifier
            for identifier in set(schema_map) | set(sample_relationships)
            if identifier is not None
        )
        result = []
        for identifier in ids:
            schema_entry = schema_map.get(identifier, {})
            sample_entry = sample_relationships.get(identifier)
            rel_type = schema_entry.get("type") or (sample_entry and sample_entry.get("type")) or "Relationship"
            entry = {
                "identifier": identifier,
                "type": rel_type,
                "source": schema_entry.get("source") or (sample_entry and sample_entry.get("source")),
                "target": schema_entry.get("target") or (sample_entry and sample_entry.get("target")),
                "source_file": model_file,
                "properties": schema_entry.get("properties") or {},
                "sample_instances": [sample_entry] if sample_entry else [],
            }
            if not sample_entry:
                add_warning(f"Missing sample entry for {rel_type} {identifier}")
            result.append(entry)
        return result


@lru_cache(maxsize=1)
def get_schema_service() -> SchemaPayloadService:
    settings = get_visualizer_settings()
    parser = SampleParser(settings.sample_model_path)
    loader = DataLoader(settings)
    cache = SchemaCache(settings.cache_path)
    return SchemaPayloadService(settings, parser, loader, cache)


router = APIRouter()


@router.get("/schema-payload")
async def schema_payload(force_reload: bool = Query(False, alias="force_reload")) -> dict[str, Any]:
        service = get_schema_service()
        try:
            return await service.get_payload(force_reload)
        except PayloadUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/schema-payload/refresh", status_code=202)
async def schema_payload_refresh(request: RefreshRequest) -> dict[str, Any]:
    service = get_schema_service()
    try:
        estimated = await service.request_refresh()
    except RefreshInProgress as exc:
        raise HTTPException(status_code=409, detail="Refresh already running") from exc
    return {"status": "refresh_started", "estimated_completion_ms": estimated}


@router.get("/schema-payload/status")
async def schema_payload_status() -> dict[str, Any]:
    service = get_schema_service()
    return service.get_status()
