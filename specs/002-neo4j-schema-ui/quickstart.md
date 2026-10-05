# Quickstart: Neo4j Schema Visualiser

## Prerequisites

1. **Python 3.12** and repo dependencies (`poetry install`).
2. **Neo4j 5.x** with a read-only user (the visualiser only needs read access because it never mutates data).
3. Verify `sample-data/sample-00/Test Model Full.xml` exists in the repo; the visualiser parses it to seed the diagram bounds, sample nodes, and relationships.

## Environment

Add a `.env` in the project root with the values below (adjust credentials for your Neo4j instance):

```env
FRICTIONLESS_ARCHITECT_NEO4J_URI=bolt://localhost:7687
FRICTIONLESS_ARCHITECT_NEO4J_USER=reader
FRICTIONLESS_ARCHITECT_NEO4J_PASSWORD=reader-password
FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR=sample-data
FRICTIONLESS_ARCHITECT_CACHE_DIR=.cache/visualiser
FRICTIONLESS_ARCHITECT_WARNING_TEXT="Sample data unavailable"
FRICTIONLESS_ARCHITECT_REFRESH_BACKOFF_SECONDS=300
FRICTIONLESS_ARCHITECT_RETRY_INTERVAL_SECONDS=300
```

The cache directory stores the normalized payload (`schema_payload.json`) so the service can return schema metadata even when Neo4j is offline, and `FRICTIONLESS_ARCHITECT_WARNING_TEXT` defines the non-blocking banner shown when the sample file cannot be read.

## Start the visualiser

1. Activate your virtual environment and install dependencies:

   ```bash
   poetry install
   poetry env activate
   ```

2. (Optional) If you want Neo4j to hold the same dataset as the sample XML, use the schema manager with a JSON fixture derived from `Test Model Full.xml`.
3. Run the FastAPI visualiser:

   ```bash
   poetry run uvicorn frictionless_architect.app:app --reload --port 8100
   ```

4. Fetch `http://127.0.0.1:8100/schema-payload` (interactive API docs at `/docs`). The
   service is JSON-only: the server-rendered `/schema-visualizer` page was dropped ahead of
   the planned `schema-visualizer-ui` extraction (ADR-0005), so there is no browser UI yet.
   The payload carries:

   - the ArchiMate elements, relationships and views (Neo4j merged with the sample file),
   - a `warnings` list (for example "Sample data unavailable"), and
   - `latency_ms` for the build.

## Workflow tips

- `GET /schema-payload/status` reports cache age, Neo4j health (`neo4j_status`), sample
  file health (`sample_file_status`), the latest warning and whether a refresh is running.
- `POST /schema-payload/refresh` starts a background rebuild (`202 Accepted`; `409` if one
  is already running; `429` with `Retry-After` for `REFRESH_BACKOFF_SECONDS` after a successful one) while `/schema-payload` keeps serving the cached payload.
- Each `/schema-payload` response includes `latency_ms`, so you can confirm the <2-second
  load goal and track warnings like missing samples or Neo4j timeouts.
