"""API surface for the schema visualiser."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Any
from xml.etree.ElementTree import ParseError

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from frictionless_architect.visualizer.cache import SchemaCache
from frictionless_architect.visualizer.config import VisualizerSettings, get_visualizer_settings
from frictionless_architect.visualizer.data_loader import DataLoader, DataLoaderError
from frictionless_architect.visualizer.namespaces import ArchimateNamespaceError
from frictionless_architect.visualizer.sample_parser import SampleParser, SampleParseResult
from frictionless_architect.visualizer.sample_validator import validate_sample_against_schema


class PayloadUnavailable(Exception):
    """Raised when neither Neo4j nor the sample model yields any schema data."""

    def __init__(self, message: str, warnings: list[str] | None = None) -> None:
        """Create the error.

        Args:
            message: Human-readable reason.
            warnings: Warnings collected while trying to build the payload.
        """
        super().__init__(message)
        self.warnings = warnings or []


class RefreshInProgress(Exception):
    """Raised when a refresh is requested while another is still running."""


class RefreshBackoff(Exception):
    """Raised when a refresh is requested too soon after a successful one.

    Attributes:
        retry_after: Whole seconds left until a refresh is accepted again.
    """

    def __init__(self, retry_after: int) -> None:
        """Record how long the caller must wait.

        Args:
            retry_after: Whole seconds left in the backoff window.
        """
        super().__init__(f"Refresh backoff active for another {retry_after}s")
        self.retry_after = retry_after


class RefreshRequest(BaseModel):
    """Body of ``POST /schema-payload/refresh``.

    Attributes:
        source: Optional free-text hint of what triggered the refresh (currently unused).
    """

    source: str | None = None


MODEL_SCHEMA_FILE = "archimate3_Model.xsd"
VIEW_SCHEMA_FILE = "archimate3_View.xsd"


class SchemaPayloadService:
    """Builds, caches and refreshes the merged Neo4j + sample schema payload."""

    def __init__(
        self, settings: "VisualizerSettings", parser: SampleParser, loader: DataLoader, cache: SchemaCache
    ) -> None:
        """Wire the service to its collaborators.

        Args:
            settings: Visualiser settings.
            parser: Parser for the sample model.
            loader: Neo4j reader.
            cache: File cache for the payload.
        """
        self.settings = settings
        self.parser = parser
        self.loader = loader
        self.cache = cache
        self._build_lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[Any] | None = None
        self._retry_task: asyncio.Task[Any] | None = None
        self._last_refresh_started: datetime | None = None
        self._last_refresh_completed: datetime | None = None
        self._last_latency_ms: int | None = None
        self._neo4j_status = "disabled"
        self._sample_status = "missing"
        self._last_warning = ""

    async def get_payload(self, force_reload: bool = False) -> dict[str, Any]:
        """Return the schema payload, preferring the cache.

        Args:
            force_reload: Rebuild instead of reading the cache. A failed rebuild falls
                back to the cached payload when one exists.

        Returns:
            The payload with ``model``, ``elements``, ``relationships``, ``views``,
            ``warnings`` and ``latency_ms``.

        Raises:
            PayloadUnavailable: If the build fails and nothing is cached.
        """
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
        """Start a background rebuild of the cache.

        Returns:
            Estimated completion time in milliseconds.

        Raises:
            RefreshInProgress: If a refresh is already running.
            RefreshBackoff: If the last successful refresh finished less than
                ``refresh_backoff_seconds`` ago. Failed refreshes never start the
                backoff, so they can be retried immediately.
        """
        if self._refresh_task and not self._refresh_task.done():
            raise RefreshInProgress()
        if self._last_refresh_completed is not None:
            elapsed = (datetime.now(timezone.utc) - self._last_refresh_completed).total_seconds()
            remaining = self.settings.refresh_backoff_seconds - elapsed
            if remaining > 0:
                raise RefreshBackoff(math.ceil(remaining))
        estimate = max(500, (self._last_latency_ms or 1200) * 2)
        self._refresh_task = asyncio.create_task(self._background_refresh())
        await asyncio.sleep(0)
        return estimate

    async def _build_and_cache(self) -> dict[str, Any]:
        try:
            payload = await self._build_and_cache_once()
        except PayloadUnavailable:
            self._ensure_retry()
            raise
        if self._neo4j_status == "unavailable":
            self._ensure_retry()
        return payload

    def _ensure_retry(self) -> None:
        if self._retry_task is None or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._retry_until_loaded())

    async def _retry_until_loaded(self) -> None:
        """Retry a failed load every ``retry_interval_seconds`` until it succeeds (SC-006)."""
        try:
            while True:
                await asyncio.sleep(self.settings.retry_interval_seconds)
                try:
                    await self._build_and_cache_once()
                except PayloadUnavailable:
                    continue
                if self._neo4j_status != "unavailable":
                    return
        finally:
            self._retry_task = None

    async def stop_retry(self) -> None:
        """Cancel any pending automatic retry (used on shutdown)."""
        task = self._retry_task
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self._retry_task = None

    async def _build_and_cache_once(self) -> dict[str, Any]:
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
        """Report cache age, source health and refresh state.

        Returns:
            A mapping with ``cache_age_seconds``, ``neo4j_status``, ``sample_file_status``,
            ``last_warning``, ``refresh_in_progress``, ``retry_pending`` and, once known,
            ``last_refresh_started`` / ``last_refresh_completed`` (ISO 8601).
        """
        age = self.cache.age_seconds()
        status = {
            "cache_age_seconds": int(age) if age is not None else None,
            "neo4j_status": self._neo4j_status,
            "sample_file_status": self._sample_status,
            "last_warning": self._last_warning,
            "refresh_in_progress": bool(self._refresh_task and not self._refresh_task.done()),
            "retry_pending": bool(self._retry_task and not self._retry_task.done()),
        }
        if self._last_refresh_started:
            status["last_refresh_started"] = self._last_refresh_started.isoformat()
        if self._last_refresh_completed:
            status["last_refresh_completed"] = self._last_refresh_completed.isoformat()
        return status

    def _load_sample(self, add_warning: Any) -> tuple[str, SampleParseResult]:
        try:
            sample_result = self.parser.parse()
        except (FileNotFoundError, ParseError):
            add_warning(self.settings.warning_text)
            return "missing", SampleParseResult.empty(self.settings.sample_model_path)
        except ArchimateNamespaceError as exc:
            add_warning(str(exc))
            return "invalid", SampleParseResult.empty(self.settings.sample_model_path)

        for issue in sample_result.warnings:
            add_warning(issue)
        for issue in validate_sample_against_schema(
            self.settings.sample_model_path,
            self.settings.schema_diagram_xsd_path,
        ):
            add_warning(issue)
        return "loaded", sample_result

    def _load_schema(self, add_warning: Any) -> tuple[str, dict[str, list[dict[str, Any]]]]:
        if not self.settings.neo4j_uri:
            return "disabled", {"elements": [], "relationships": [], "views": []}
        try:
            return "available", self.loader.collect()
        except DataLoaderError as exc:
            add_warning(str(exc))
            return "unavailable", {"elements": [], "relationships": [], "views": []}

    def _build_payload(self) -> tuple[dict[str, Any], str, str, list[str], int]:
        start = time.monotonic()
        warnings: list[str] = []
        seen: set[str] = set()

        def add_warning(text: str) -> None:
            if not text or text in seen:
                return
            seen.add(text)
            warnings.append(text)

        sample_status, sample_result = self._load_sample(add_warning)
        schema_status, schema_payload = self._load_schema(add_warning)

        if not schema_payload["elements"] and not sample_result.elements:
            raise PayloadUnavailable(
                "Schema data unavailable; no Neo4j connection or sample data.",
                warnings=list(warnings),
            )

        model_payload = sample_result.model or {
            "identifier": "schema",
            "name": "ArchiMate Schema",
        }
        model_payload["source_file"] = MODEL_SCHEMA_FILE

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
        relationships = self._merge_relationships(
            schema_payload["relationships"], sample_result.relationships, add_warning
        )
        views = [{**view, "source_file": VIEW_SCHEMA_FILE} for view in sample_result.views]

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
        model_file = MODEL_SCHEMA_FILE
        schema_map = {el.get("identifier"): el for el in schema_elements if el.get("identifier")}
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
        model_file = MODEL_SCHEMA_FILE
        schema_map = {rel.get("identifier"): rel for rel in schema_relationships if rel.get("identifier")}
        ids = sorted(identifier for identifier in set(schema_map) | set(sample_relationships) if identifier is not None)
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


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_schema_service() -> SchemaPayloadService:
    """Return the process-wide ``SchemaPayloadService`` (built once from settings)."""
    settings = get_visualizer_settings()
    logger.debug(
        "Visualizer settings read: neo4j_uri=%s, neo4j_user=%s, sample_data_dir=%s, sample_model_path=%s, cache_dir=%s",
        settings.neo4j_uri or "<empty>",
        settings.neo4j_user or "<empty>",
        settings.sample_data_dir,
        settings.sample_model_path,
        settings.cache_dir,
    )
    parser = SampleParser(settings.sample_model_path)
    loader = DataLoader(settings)
    cache = SchemaCache(settings.cache_path)
    return SchemaPayloadService(settings, parser, loader, cache)


router = APIRouter()

ForceReloadQuery = Annotated[bool, Query(alias="force_reload")]
RefreshRequestBody = Annotated[RefreshRequest, Body()]


@router.get(
    "/schema-payload",
    responses={503: {"description": "Schema payload unavailable when both sample data and Neo4j are unreachable"}},
)
async def schema_payload(force_reload: ForceReloadQuery = False) -> dict[str, Any]:
    """``GET /schema-payload``: return the schema payload (503 if unavailable)."""
    service = get_schema_service()
    try:
        return await service.get_payload(force_reload)
    except PayloadUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/schema-payload/refresh",
    status_code=202,
    responses={
        409: {"description": "A refresh is already in progress"},
        429: {"description": "Too soon after the last successful refresh; see Retry-After"},
        503: {"description": "Schema payload unavailable while refreshing"},
    },
)
async def schema_payload_refresh(request: RefreshRequestBody) -> dict[str, Any]:
    """``POST /schema-payload/refresh``: start a background refresh.

    Returns 202 when started, 409 if one is running, and 429 with ``Retry-After`` while
    the backoff after the last successful refresh is still active.
    """
    service = get_schema_service()
    try:
        estimated = await service.request_refresh()
    except RefreshInProgress as exc:
        raise HTTPException(status_code=409, detail="Refresh already running") from exc
    except RefreshBackoff as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)}) from exc
    return {"status": "refresh_started", "estimated_completion_ms": estimated}


@router.get("/schema-payload/status")
async def schema_payload_status() -> dict[str, Any]:
    """``GET /schema-payload/status``: report cache and source health."""
    service = get_schema_service()
    return service.get_status()
