# Quickstart: Neo4j Schema Visualiser

## Prerequisites
1. **Python 3.12** and repo dependencies (`uv sync --all-groups` or `pip install -e .`).
2. **Neo4j 5.x** with a read-only user.
3. Ensure `sample-data/sample-00/Test Model Full.xml` is present (included in the repo) so the visualiser can show schema + sample relationships.

## Environment
Create a `.env` in the repo root defining:
```env
FRICTIONLESS_ARCHITECT_NEO4J_URI=bolt://localhost:7687
FRICTIONLESS_ARCHITECT_NEO4J_USER=reader
FRICTIONLESS_ARCHITECT_NEO4J_PASSWORD=reader-password
FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR=sample-data
FRICTIONLESS_ARCHITECT_CACHE_DIR=.cache/visualiser
FRICTIONLESS_ARCHITECT_SECURITY_ENABLED=false
FRICTIONLESS_ARCHITECT_WARNING_TEXT="Sample data unavailable"
```
The warning text matches FR-006 and the cache directory stores the normalized payloads for offline resilience.

## Start the visualiser
1. Activate your virtual environment and install dependencies:
   ```bash
   source .venv/bin/activate
   uv sync --all-groups
   ```
2. Load the enriched sample schema into Neo4j (reuse the schema manager):
   ```bash
   python -m frictionless_architect.schema.manager --ingest 'sample-data/sample-00/Test Model Full.xml'
   ```
3. Start the FastAPI visualiser:
   ```bash
   uvicorn frictionless_architect.visualizer:app --reload --port 8100
   ```
4. Browse to `http://127.0.0.1:8100/schema-visualizer`:
   - Diagram view (cytoscape) shows every schema definition and sample instance from `Test Model Full.xml`.
   - Tabular view lists element/relationship attributes plus their source schema file.
   - Warning banner appears when Neo4j/sample data is unavailable; the schema summary stays accessible.

## Workflow tips
- Refreshing the sample data triggers `/schema-payload/refresh` and updates the cached JSON payload; the UI polls `/schema-payload/status` for freshness and warnings.
- Logs include `latency_ms` and warning reasons so you can monitor the <2-second load target.
- If Neo4j is unreachable, the cached JSON still powers the UI—the warning banner displays “Sample data unavailable” while the schema list stays visible.
