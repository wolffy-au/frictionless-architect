# ADR-0005: Visualiser API/UI split is the first extraction

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §8)
- **Sources:** `ARCHITECTURE.md` §8, §8.1, §11

## Context

The restructure (ADR-0001, ADR-0002) needs a first, low-risk extraction to prove
the monorepo fan-out pattern (root CI fans out, shared lock resolves, tests
pass). Today one FastAPI app (`visualizer/api.py`) serves both the JSON payload
and the HTML/JS UI.

## Decision

The **first extraction** splits the visualiser:

- `packages/schema-visualizer-api` — JSON only (`/schema-payload`, `/refresh`,
  `/status`); drop the HTML route and Jinja/static mounts.
- `packages/schema-visualizer-ui` (or fold into `dashboard`) — a Vite app that
  fetches `/schema-payload`.

## Consequences

- `visualizer/{api,cache,config,data_loader,sample_parser}.py` + `schema/manager.py`
  and their tests move into the new package.
- Entry point changes: `uvicorn frictionless_architect.visualizer:app` →
  `uvicorn schema_visualizer_api:app`; update `README.md` / `quickstart.md`.
- The `FRICTIONLESS_ARCHITECT_` env prefix is kept as-is for this step; renaming
  it is its own epic (`ARCHITECTURE.md` §9).
- Subsequent sequence: scaffold `knowledge-graph` → vendor forks → re-home specs
  → extract remaining components as work reaches them.

## Amendment (2026-08-30)

Raised by the `refactor-analyst` assessment (session-recorded).

- **`schema/manager.py` does not move in the first extraction.** The Consequences
  above list it moving into `packages/schema-visualizer-api`; that contradicts
  `ARCHITECTURE.md` §4, which has `packages/knowledge-graph` absorb
  `schema/manager.py` and `sample_parser.py`. `manager.py` is the Neo4j
  write / migrate / audit controller — the visualiser needs read-only access,
  not that.
- Placement of `manager.py`, the Neo4j **read** path (today in
  `visualizer/data_loader.py`), and `sample_parser.py` is **deferred to the
  `knowledge-graph` extraction** and is not yet settled.
- Revised first-extraction scope: move `visualizer/{api,cache,config}.py` + the
  visualiser's own payload / coverage-merge logic + the FastAPI router into
  `packages/schema-visualizer-api`; stand up the UI package; drop the
  server-rendered HTML route — **confirmed: no consumer today**.
- Open questions to resolve before the extraction starts (also in
  `ARCHITECTURE.md` §10):
  - Does `schema-visualizer-api` consume `knowledge-graph` as a path-dependency
    library (its own Neo4j connection) or over HTTP? `ARCHITECTURE.md` §3.3
    implies a library.
  - Is `sample_parser.py` visualiser-specific, or generic ArchiMate ingestion?
    If generic it belongs in `knowledge-graph` and the API package stays thin.
- Unchanged: the API/UI split is still the first extraction; the
  `FRICTIONLESS_ARCHITECT_` prefix stays; the rename is its own epic.
