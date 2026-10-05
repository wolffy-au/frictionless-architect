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
  - No `401/403`: access is the single service credential (ADR-0024). A Neo4j read failure becomes a warning and falls back to the cache or sample; `503` is the only error.

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
- **Error (429)**: within `REFRESH_BACKOFF_SECONDS` (default 300) of the last *successful* refresh; the `Retry-After` header gives the seconds left. A failed refresh is never delayed. This is a manual-refresh throttle, not the SC-006 automatic retry (see Notes under status).

## GET /schema-payload/status
- **Purpose**: Reports cache freshness, last refresh time, and connection state (used by the warning banner to decide whether the schema list remains visible).  
- **Response (200)**:  
  ```json
  {
    "cache_age_seconds": 47,
    "neo4j_status": "available",
    "sample_file_status": "loaded",
    "last_warning": "Sample data reload failed at 2026-04-04T10:17:02Z",
    "refresh_in_progress": false,
    "retry_pending": false,
    "last_refresh_started": "2026-04-04T10:17:01+00:00",
    "last_refresh_completed": "2026-04-04T10:17:02+00:00"
  }
  ```  
- **Notes**: UI uses this endpoint to enforce the non-blocking warning. `last_refresh_started` / `last_refresh_completed` (ISO 8601) appear once a refresh has run. `retry_pending` is `true` while the SC-006 background retry is active: after a failed load (or Neo4j unreachable) it retries every `RETRY_INTERVAL_SECONDS` (default and maximum 300) until a load succeeds.
- **`neo4j_status` values**: `disabled` (not configured), `available`, `unavailable` (read failed; warning set, cache or sample served).
- **`sample_file_status` values**: `loaded` (sample parsed), `missing` (file absent or not well-formed XML), `invalid` (root is not an ArchiMate `<model>` in the `http://www.opengroup.org/xsd/archimate/3.0/` namespace — see ADR-0032; `last_warning` carries the details).
