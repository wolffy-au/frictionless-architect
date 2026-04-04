# API Contracts for the Neo4j Schema Visualiser

## GET /schema-payload
- **Purpose**: Returns the aggregated model/element/relationship/view payload that both the diagram and table views consume.  
- **Query Parameters**:  
  - `force_reload` (boolean, default `false`): bypass cached JSON and reload from Neo4j + the enriched sample before responding.  
- **Response (200)**:  
  ```json
  {
    "model": { ... ModelDefinition ... },
    "elements": [ ... ElementType + sample coverage summary ... ],
    "relationships": [ ... RelationshipType + sample coverage ... ],
    "views": [ ... ViewDiagram ... ],
    "warnings": ["Missing sample entry for ValueStream VS3"],
    "latency_ms": 312
  }
  ```  
  - `warnings` is always present (empty array when there are no issues).  
  - `latency_ms` supports the <2s load goal and can be surfaced in UI logs.  
- **Errors**:  
  - `503` when Neo4j/sample data both fail and no cache exists (UI should show a fatal error).  
  - `401/403` when Neo4j credentials reject the read attempt (surface the message and fall back to cached payload if available).

## POST /schema-payload/refresh
- **Purpose**: Triggers an asynchronous rebuild of the cached payload from Neo4j + `Test Model Full.xml`; returns immediately to keep the UI responsive while a background job runs.  
- **Body**: `{ "source": "manual" }` (optional tracing metadata).  
- **Response (202)**:  
  ```json
  {
    "status": "refresh_started",
    "estimated_completion_ms": 1200
  }
  ```  
- **Error (409)**: when a refresh is already running; UI may show a toast and rely on the previous payload until the new one is ready.

## GET /schema-payload/status
- **Purpose**: Reports cache freshness, last refresh time, and connection state (used by the warning banner to decide whether the schema list remains visible).  
- **Response (200)**:  
  ```json
  {
    "cache_age_seconds": 47,
    "neo4j_status": "available",
    "sample_file_status": "loaded",
    "last_warning": "Sample data reload failed at 2026-04-04T10:17:02Z"
  }
  ```  
- **Notes**: UI uses this endpoint to enforce the non-blocking warning and honor the 5-minute retry window from the spec.
