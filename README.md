# frictionless-architect Development Setup

This document outlines the steps to set up the development environment for the
frictionless-architect project. The repository currently ships one built slice: the
**Neo4j schema visualiser** (a FastAPI service that renders an ArchiMate/Neo4j schema
as a diagram, table, and summary). See `PROJECT_SPECIFICATION.md` for the full platform
vision and `ARCHITECTURE.md` for the target repository topology.

## Prerequisites

- Python 3.12 (project supports `>=3.10,<3.14`)
- [Poetry](https://python-poetry.org/) for dependency management
- A reachable Neo4j instance (optional — the visualiser falls back to bundled sample data)

## Installation

1. **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd frictionless-architect
    ```

2. **Install dependencies with Poetry:**

    ```bash
    poetry install --with dev,tests,lint,docs
    ```

    This creates the virtual environment and installs the project plus its
    dependency groups. Prefix commands with `poetry run` (e.g. `poetry run pytest`)
    or spawn a shell with `poetry shell`.

## Configuration

The project uses `pydantic-settings` to drive environment-specific values. Override the
defaults by exporting these variables (or placing them in a `.env` file at the project
root, which is loaded automatically when present):

- `FRICTIONLESS_ARCHITECT_LOG_LEVEL` – default log level for the structured logger
  (`INFO`, `DEBUG`, etc.).
- `FRICTIONLESS_ARCHITECT_NEO4J_URI` – Bolt URI for the Neo4j instance
  (e.g. `bolt://localhost:7687`). Leave empty to run purely against sample data.
- `FRICTIONLESS_ARCHITECT_NEO4J_USER` / `FRICTIONLESS_ARCHITECT_NEO4J_PASSWORD` – Neo4j
  credentials.
- `FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR` – directory holding the sample ArchiMate
  model used when Neo4j is unavailable (default: `sample-data`).
- `FRICTIONLESS_ARCHITECT_CACHE_DIR` – directory for the visualiser payload cache
  (default: `.cache/visualiser`).
- `FRICTIONLESS_ARCHITECT_WARNING_TEXT` – banner text shown when sample data is
  unavailable.

## Running the Tests

All tests run through pytest:

```bash
poetry run pytest
```

- Unit tests live under `tests/unit/...` (one `test_<module>.py` per production module).
- API integration tests live under `tests/api/` and exercise the FastAPI app in-process
  via `httpx.AsyncClient` + `ASGITransport` — no external server required.
- BDD scenarios live under `tests/features/` (behave).

Scope the run with `-k` (e.g. `poetry run pytest tests/api -k schema`) or target a single
test (`poetry run pytest tests/api/test_schema_payload.py::<test_name>`).

## Schema Visualiser

The Neo4j schema visualiser ships as its own FastAPI entry point
(`frictionless_architect.visualizer:app`, titled "Neo4j Schema Visualiser").

1. Point your `.env` at the Neo4j instance and sample data:

   ```
   FRICTIONLESS_ARCHITECT_NEO4J_URI=bolt://localhost:7687
   FRICTIONLESS_ARCHITECT_NEO4J_USER=reader
   FRICTIONLESS_ARCHITECT_NEO4J_PASSWORD=reader
   FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR=sample-data
   FRICTIONLESS_ARCHITECT_CACHE_DIR=.cache/visualiser
   FRICTIONLESS_ARCHITECT_WARNING_TEXT="Sample data unavailable"
   ```

2. Start the visualiser service:

   ```bash
   poetry run uvicorn frictionless_architect.visualizer:app --reload --port 8100
   ```

3. Visit `http://127.0.0.1:8100/schema-visualizer` to see the diagram, table, and
   schema summary driven by `/schema-payload`.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/schema-visualizer` | HTML page (diagram + table + summary) |
| `GET` | `/schema-payload` | JSON schema payload; `?force_reload=true` bypasses the cache |
| `POST` | `/schema-payload/refresh` | Trigger an asynchronous cache refresh (`202`; `409` if one is already running) |
| `GET` | `/schema-payload/status` | Cache age, Neo4j health, and active warnings |

The interface keeps the schema list visible even when the banner reads
"Sample data unavailable", so you can still inspect the last known model while a
refresh is in flight.

## Related Tooling

- `scripts/neo4j_schema.py` – helper for inspecting the live Neo4j schema.
- `scripts/pre_commit_checks.sh` / `scripts/pre_merge_checks.sh` – run the markdown,
  ruff, pyright, mypy, behave, and pytest gates locally before committing or merging.
