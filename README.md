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
platform requirements live in the business specification,
[`specs/001-governance-platform/spec.md`](specs/001-governance-platform/spec.md); the target repository
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
- `FRICTIONLESS_ARCHITECT_REFRESH_BACKOFF_SECONDS` — seconds after a *successful*
  refresh during which `POST /schema-payload/refresh` answers `429` with `Retry-After`
  (default: `300`; failed refreshes are never delayed).
- `FRICTIONLESS_ARCHITECT_RETRY_INTERVAL_SECONDS` — seconds between automatic background
  retries after a failed load (default and maximum: `300`).

`scripts/neo4j_schema.py` is a separate CLI that reads its own **unprefixed**
`NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` (or `--uri` / `--user` /
`--password` flags).

## Running the schema visualiser

The visualiser is the FastAPI app `frictionless_architect.app:app` (title
"Frictionless Architect"; the OpenAPI docs are at `/docs`).

```bash
poetry run uvicorn frictionless_architect.app:app --reload --port 8100
```

The service is JSON-only for now — fetch `http://127.0.0.1:8100/schema-payload`
for the diagram, table, and schema data. The server-rendered HTML page
(`/schema-visualizer`) described in ADR-0005 has been dropped ahead of the
planned `schema-visualizer-ui` extraction; there is no browser UI until that
package exists.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/schema-payload` | JSON payload (`model`, `elements`, `relationships`, `views`, `warnings`, `latency_ms`; includes duplicate-identifier warnings from the sample); `?force_reload=true` rebuilds instead of serving the cache; `503` only if nothing reachable *and* nothing cached |
| `POST` | `/schema-payload/refresh` | Start async refresh: `202` + `{status, estimated_completion_ms}`; `409` if busy; `429` during backoff |
| `GET` | `/schema-payload/status` | `cache_age_seconds`, `neo4j_status`, `sample_file_status`, `last_warning`, `refresh_in_progress`, `retry_pending`, plus `last_refresh_started` / `last_refresh_completed` once a refresh has run |

`?force_reload=true` tries to rebuild the payload from Neo4j and the sample file.
If that rebuild fails (e.g. Neo4j is down and the sample is missing) but a payload
was cached from an earlier successful build, `/schema-payload` still returns that
cached payload (HTTP 200) instead of a `503` — the forced reload is best-effort, not
all-or-nothing. A `503` only happens when the rebuild fails *and* there is no cache
to fall back on.

`GET /schema-payload/status` fields that take a small set of values:

- `neo4j_status`: `disabled` (no `FRICTIONLESS_ARCHITECT_NEO4J_URI` configured —
  sample-only mode), `available` (last load from Neo4j succeeded), or
  `unavailable` (Neo4j is configured but the last load failed; a background retry
  is scheduled — see `retry_pending` below).
- `sample_file_status`: `missing` (the sample XML could not be found/parsed),
  `invalid` (found, but not a valid ArchiMate exchange-format `<model>`), or
  `loaded` (parsed successfully; `warnings` may still list XSD validation issues).
- `refresh_in_progress`: `true` while a `POST /schema-payload/refresh` rebuild is
  running.
- `retry_pending`: `true` while the automatic background retry (below) has a
  rebuild scheduled or running.

### Automatic retry and offline-cache fallback

If a build finds `neo4j_status: unavailable` (Neo4j configured but unreachable),
the service schedules an automatic background retry every
`FRICTIONLESS_ARCHITECT_RETRY_INTERVAL_SECONDS` seconds (default and maximum
`300`) until a load succeeds or stops being degraded — no client action is
needed. Poll `GET /schema-payload/status` and watch `retry_pending`: `true` means
a retry is scheduled or running; it clears once Neo4j is reachable again (or you
can also watch `neo4j_status` go back to `available`).

Whether reached via automatic retry or normal cache-first `GET /schema-payload`
calls, the cached `schema_payload.json` under `FRICTIONLESS_ARCHITECT_CACHE_DIR`
(default `.cache/visualiser`) is what keeps the service answering when Neo4j
drops out entirely: as long as one build has ever succeeded, every later
`/schema-payload` call — forced reload or not — can fall back to that cache
rather than failing.

### Sample warnings reference

The payload's `warnings` list (and `GET /schema-payload/status`'s `last_warning`,
which holds the most recent one) is always non-fatal — the service still comes up
and serves what it can. The shapes to expect:

- **Duplicate identifiers** — `Duplicate element identifier <id> in the sample;
  the last definition is used`, `Duplicate relationship identifier <id> in the
  sample; the last definition is used`, or `Duplicate view identifier <id> in the
  sample`. The sample model keeps the *last* definition for a repeated element or
  relationship identifier (silently overwriting earlier ones in memory) and keeps
  all definitions for a repeated view identifier; either way, each repeat after
  the first appends one of these warnings so the collision isn't silent.
- **Missing sample coverage** — `Missing sample entry for <type> <name>` for an
  element, or `Missing sample entry for <type> <identifier>` for a relationship:
  Neo4j defines it but the sample XML has no matching instance, so the merged
  payload entry's `coverage` is `false` and `sample_instances` is empty.
- **XSD schema-validation issues** (ADR-0022) — every build validates the sample
  against the bundled ArchiMate XSDs
  (`sample-data/schema/archimate3_Diagram.xsd` and its includes):
  - `XSD: <reason> (at <path>)` — a schema-validation error, with the offending
    element path. More than `MAX_XSD_ISSUES` (50) of these truncates the list
    with a final `XSD: further XSD issues suppressed after the first 50`.
  - `Relationship … references missing …` / `View … references missing …` — a
    hand-written check (not from the XSD) that names a dangling relationship or
    view reference by identifier, which raw XSD key/keyref errors don't do.
- **Sample load failures** — if the sample file is missing or unparseable, the
  configured `FRICTIONLESS_ARCHITECT_WARNING_TEXT` (default `Sample data
  unavailable`) is used instead; `sample_file_status` reports `missing` or
  `invalid` (see above).

### Sample-only mode (no Neo4j)

To run with no Neo4j instance at all:

1. Leave `FRICTIONLESS_ARCHITECT_NEO4J_URI` unset (or empty) — this is the
   default, so an `.env` that simply omits it is enough.
2. Keep `sample-data/sample-00/Test Model Full.xml` in place; it's checked into
   the repo, so no extra setup is needed.
3. Start the service as usual:

   ```bash
   poetry run uvicorn frictionless_architect.app:app --reload --port 8100
   ```

4. `GET /schema-payload/status` will report `neo4j_status: disabled` and
   `sample_file_status: loaded`; `GET /schema-payload` serves the sample-derived
   payload, with no Neo4j connection attempted. Once that first load succeeds, no
   automatic retry is scheduled (retries are for a configured-but-unreachable
   Neo4j, or a build that fails outright — not the disabled case).

## Platform packages

Code being extracted from the flat `src/` layout lives in the `platform/` Poetry
monorepo (ADR-0002), which has its own lock and virtualenv — run its commands from
`platform/`. Today it holds:

- [`controls-compliance-catalog`](platform/packages/controls-compliance-catalog/README.md) —
  policy and standard documents to OSCAL Catalogs and Profiles.
- [`llm-provider-config`](platform/packages/llm-provider-config/README.md) — shared
  LLM provider, model and credential resolution.

`bash scripts/platform_checks.sh` runs their quality gate.

## Operations: seeding Neo4j

This is operator tooling for standing up the database, not an end-user feature of the
visualiser — the visualiser itself is read-only against whatever Neo4j already holds.

- `scripts/neo4j_schema.py` — CLI that bootstraps the ArchiMate schema in Neo4j
  directly via `SchemaManager`, independent of the FastAPI service. Subcommands:
  - `constraints` — create the uniqueness constraints and indexes (idempotent).
  - `ingest --data-file <path.json>` — merge a JSON fixture (elements,
    relationships, views, diagrams) into the graph.
  - `version [--version-name <name>]` — stamp a `SchemaVersion` node with the
    current time (default name: `initial-constraints`).
  - `audit` — report dangling view/diagram relationship references and views
    with no members.
  - `all` — run `constraints`, `ingest`, `version` and `audit` in sequence (the
    whole bootstrap in one command; still needs `--data-file`).

  Example, bootstrapping from a JSON fixture (no fixture ships in the repo today;
  `<path/to/fixture.json>` is a mapping with optional `elements`, `relationships`,
  `views` and `diagrams` lists, matching `SchemaManager.ingest_payload`):

  ```bash
  poetry run python scripts/neo4j_schema.py all --data-file <path/to/fixture.json>
  ```

  Unlike the FastAPI service's `FRICTIONLESS_ARCHITECT_*` settings, this script
  reads its connection details from **unprefixed** `NEO4J_URI`, `NEO4J_USER` and
  `NEO4J_PASSWORD` — either already exported in the environment, or in the same
  root `.env` file (loaded via `python-dotenv`; see `scripts/neo4j_schema.py`'s
  `load_env`) alongside unrelated names, or via `--uri` / `--user` / `--password`
  flags. Setting only the `FRICTIONLESS_ARCHITECT_NEO4J_*` variables has no effect
  on this script.

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
