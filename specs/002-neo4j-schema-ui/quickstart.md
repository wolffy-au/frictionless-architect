# Quickstart: Neo4j Schema Visualiser

## Prerequisites

1. **Python 3.12** and repo dependencies (`poetry sync` or `pip install -e .`).
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
FRICTIONLESS_ARCHITECT_REFRESH_BACKOFF=300
```

The cache directory stores the normalized payload (`schema_payload.json`) so the UI can display schema metadata even when Neo4j is offline, and `FRICTIONLESS_ARCHITECT_WARNING_TEXT` defines the non-blocking banner shown when the sample file cannot be read.

## Start the visualiser

1. Activate your virtual environment and install dependencies:
   ```bash
   source .venv/bin/activate
   poetry sync
   ```
2. (Optional) If you want Neo4j to hold the same dataset as the sample XML, use the schema manager with a JSON fixture derived from `Test Model Full.xml`.
3. Run the FastAPI visualiser:
   ```bash
   uvicorn frictionless_architect.visualizer:app --reload --port 8100
   ```
4. Open `http://127.0.0.1:8100/schema-visualizer`:
   - The Cytoscape-driven diagram replays the ArchiMate view positions and relationships included in the sample file.
   - The table view surfaces the same element/relationship metadata (identifier, type, source file, coverage badge).
   - The summary pane keeps every schema entry visible, even when the yellow banner reads “Sample data unavailable” because so few dependencies are blocking the view.

## Workflow tips

- The page polls `/schema-payload/status` to display cache age, Neo4j health, and the latest warning; refreshes happen every 15 seconds so you can monitor recoveries.
- Pressing **Refresh sample** calls `/schema-payload/refresh`, starts a background rebuild (`202 Accepted`), and keeps the cache-based UI while the loader works.
- Each `/schema-payload` response includes `latency_ms`, so you can confirm the <2-second load goal and track warnings like missing samples or Neo4j timeouts.
