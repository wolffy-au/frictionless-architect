"""Tests for /schema-payload/status and refresh controls."""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_schema_status_reports_metadata(schema_client):
    await schema_client.get("/schema-payload")
    response = await schema_client.get("/schema-payload/status")
    assert response.status_code == 200
    status = response.json()
    assert status["neo4j_status"] == "disabled"
    assert status["sample_file_status"] == "loaded"
    assert isinstance(status["cache_age_seconds"], (int, type(None)))


@pytest.mark.asyncio
async def test_schema_refresh_handles_concurrent_requests(schema_client_with_slow_refresh):
    client = schema_client_with_slow_refresh
    first = await client.post("/schema-payload/refresh", json={"source": "manual"})
    assert first.status_code == 202
    second = await client.post("/schema-payload/refresh", json={})
    assert second.status_code == 409
    await asyncio.sleep(0.15)
    status = await client.get("/schema-payload/status")
    assert status.json().get("refresh_in_progress") in (True, False)
