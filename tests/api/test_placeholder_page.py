"""Contract tests for the visualiser placeholder page (`GET /`)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_placeholder_page_renders_schema_summary(schema_client):
    response = await schema_client.get("/")
    assert response.status_code == 200
    assert "Page loaded." in response.text
    assert "Elements in schema:" in response.text


@pytest.mark.asyncio
async def test_placeholder_page_falls_back_when_sample_missing(schema_client_without_sample):
    response = await schema_client_without_sample.get("/")
    assert response.status_code == 200
    assert "Page loaded." in response.text
    assert "Elements in schema: 0" in response.text
