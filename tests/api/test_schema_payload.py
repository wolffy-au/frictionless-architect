"""Contract tests for /schema-payload."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_schema_payload_returns_elements_and_relationships(schema_client):
    response = await schema_client.get("/schema-payload")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("model")
    assert payload.get("elements")
    assert payload.get("relationships")
    assert all("source_file" in elem for elem in payload["elements"])
    assert any(elem["sample_instances"] for elem in payload["elements"])
    assert payload.get("warnings") is not None


@pytest.mark.asyncio
async def test_schema_payload_warns_when_sample_missing(schema_client_without_sample):
    response = await schema_client_without_sample.get("/schema-payload")
    assert response.status_code == 503
    status = (await schema_client_without_sample.get("/schema-payload/status")).json()
    assert status["sample_file_status"] == "missing"
    assert status["last_warning"] == "Sample data unavailable"
