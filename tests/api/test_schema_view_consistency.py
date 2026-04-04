"""Ensure diagram/table payloads share the same dataset."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_schema_view_consistency(schema_client):
    response = await schema_client.get("/schema-payload")
    assert response.status_code == 200
    payload = response.json()
    elements = {item["identifier"] for item in payload.get("elements", []) if item.get("identifier")}
    relationships = {item["identifier"] for item in payload.get("relationships", []) if item.get("identifier")}
    assert payload.get("views")
    view = payload["views"][0]
    nodes = view.get("nodes", [])
    connections = view.get("connections", [])
    assert all(node.get("elementRef") in elements for node in nodes if node.get("elementRef"))
    assert all(conn.get("relationshipRef") in relationships for conn in connections if conn.get("relationshipRef"))
    assert all("bounds" in node and node["bounds"] for node in nodes)
