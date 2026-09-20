# frictionless-architect

[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![codecov](https://codecov.io/gh/wolffy-au/frictionless-architect/graph/badge.svg?token=K5AQRYWNFU)](https://codecov.io/gh/wolffy-au/frictionless-architect)
[![test](https://github.com/wolffy-au/frictionless-architect/actions/workflows/ci.yml/badge.svg)](https://github.com/wolffy-au/frictionless-architect/actions/workflows/ci.yml)

[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=wolffy-au_frictionless-architect&metric=alert_status)](https://sonarcloud.io/project/overview?id=wolffy-au_frictionless-architect)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=wolffy-au_frictionless-architect&metric=bugs)](https://sonarcloud.io/project/overview?id=wolffy-au_frictionless-architect)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=wolffy-au_frictionless-architect&metric=security_rating)](https://sonarcloud.io/project/overview?id=wolffy-au_frictionless-architect)
[![Maintainability](https://sonarcloud.io/api/project_badges/measure?project=wolffy-au_frictionless-architect&metric=sqale_rating)](https://sonarcloud.io/project/overview?id=wolffy-au_frictionless-architect)

`frictionless-architect` is a platform for describing, validating, and visualising
enterprise architecture models (ArchiMate) backed by a graph database. The full
platform vision and capability inventory live in
[`PROJECT_SPECIFICATION.md`](PROJECT_SPECIFICATION.md); the target repository
topology is described in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## What is built today

One slice is implemented and runnable: the **Neo4j schema visualiser** — a FastAPI
service that aggregates an ArchiMate schema from a live Neo4j instance and/or a
bundled sample model, then renders it as a diagram, a table, and a schema summary.
When Neo4j is unreachable it falls back to the sample data under `sample-data/`, so
the service is useful with no infrastructure at all.

## Prerequisites

- Python 3.12 (the project supports `>=3.11,<3.14`)
- [Poetry](https://python-poetry.org/) 2.x for dependency management
- Optionally, a reachable Neo4j 5.x instance (the visualiser falls back to bundled
  sample data when none is configured)

## Installation

```bash
git clone <repository_url>
cd frictionless-architect
poetry install
```

`poetry install` creates the virtual environment and installs the project plus all
dependency groups (`dev`, `tests`, `lint`, `docs`, declared under
`[dependency-groups]` in `pyproject.toml`). Prefix commands with `poetry run`
(e.g. `poetry run uvicorn ...`) or activate the environment with
`poetry env activate`.

## Configuration

Settings are defined by `VisualizerSettings` in
`src/frictionless_architect/visualizer/config.py` (env prefix
`FRICTIONLESS_ARCHITECT_`). Override defaults by exporting the variables or placing
them in a `.env` file at the repository root (loaded automatically when present):

- `FRICTIONLESS_ARCHITECT_NEO4J_URI` — Bolt URI for Neo4j
  (e.g. `bolt://localhost:7687`). Empty by default; empty means "sample data only".
- `FRICTIONLESS_ARCHITECT_NEO4J_USER` / `FRICTIONLESS_ARCHITECT_NEO4J_PASSWORD` —
  Neo4j credentials (both empty by default).
- `FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR` — directory holding the sample model
  (default: `sample-data`); the visualiser reads
  `<dir>/sample-00/Test Model Full.xml`.
- `FRICTIONLESS_ARCHITECT_CACHE_DIR` — directory for the payload cache
  (default: `.cache/visualiser`; payload file `schema_payload.json`).
- `FRICTIONLESS_ARCHITECT_WARNING_TEXT` — banner text shown when the sample model
  cannot be loaded (default: `Sample data unavailable`).
- `FRICTIONLESS_ARCHITECT_REFRESH_BACKOFF_SECONDS` — minimum gap between cache
  refreshes (default: `300`).

`scripts/neo4j_schema.py` is a separate CLI that reads its own **unprefixed**
`NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` (or `--uri` / `--user` /
`--password` flags).

## Running the schema visualiser

The visualiser is the FastAPI app `frictionless_architect.visualizer:app` (title
"Neo4j Schema Visualiser").

```bash
poetry run uvicorn frictionless_architect.visualizer:app --reload --port 8100
```

The service is JSON-only for now — fetch `http://127.0.0.1:8100/schema-payload`
for the diagram, table, and schema data. The server-rendered HTML page
(`/schema-visualizer`) described in ADR-0005 has been dropped ahead of the
planned `schema-visualizer-ui` extraction; there is no browser UI until that
package exists.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/schema-payload` | JSON payload; `?force_reload=true` skips cache; `503` if nothing reachable |
| `POST` | `/schema-payload/refresh` | Start async refresh: `202` + `{status, estimated_completion_ms}`; `409` if busy |
| `GET` | `/schema-payload/status` | `cache_age_seconds`, `neo4j_status`, `sample_file_status`, `last_warning` |

## Related tooling

- `scripts/neo4j_schema.py` — CLI that bootstraps the ArchiMate schema in Neo4j
  (`SchemaManager`). Subcommands: `constraints`, `ingest` (needs `--data-file`),
  `version`, `audit`, `all`.

## Running the tests

```bash
poetry run pytest
```

- Unit tests live under `tests/unit/`, mirroring the `src/` package layout
  (`tests/unit/schema/`, `tests/unit/visualizer/`), one `test_<module>.py` per
  production module.
- API tests live under `tests/api/` and exercise the FastAPI app in-process via
  `httpx.AsyncClient` + `ASGITransport` — no running server required.
- BDD scenarios live under `tests/features/` (behave).

Scope a run with `-k` (e.g. `poetry run pytest tests/api -k schema`) or target one
test (`poetry run pytest tests/api/test_schema_payload.py::<test_name>`).

Doing development work on this repo? [`AGENTS.md`](AGENTS.md) covers the toolchain,
layout, local quality gates, and commit conventions; [`TECHNICAL.md`](TECHNICAL.md)
covers the testing layout and coding standards.
