"""Minimal placeholder landing page for the visualiser (FR-009).

Superseded once GH #74's UI composition/build tooling ships a real
subsystem UI — this route is a smoke-testable stand-in, not meant to
accrete features (ADR-0053).
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from frictionless_architect.visualizer.api import PayloadUnavailable, get_schema_service

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def placeholder_page() -> HTMLResponse:
    """``GET /``: render the placeholder page with a live schema summary.

    Mirrors ``GET /schema-payload``'s fallback: when neither Neo4j nor the
    sample model is reachable and nothing is cached, ``get_payload`` raises
    ``PayloadUnavailable`` carrying an empty-but-valid payload (FR-006) —
    render that instead of letting the page 500.
    """
    service = get_schema_service()
    try:
        payload = await service.get_payload()
    except PayloadUnavailable as exc:
        assert exc.payload is not None
        payload = exc.payload
    element_count = len(payload.get("elements", []))

    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Schema Visualiser</title></head>
<body>
<h1>Schema Visualiser</h1>
<p data-testid="status">Page loaded.</p>
<p data-testid="schema-summary">Elements in schema: {escape(str(element_count))}</p>
</body>
</html>"""
    )
