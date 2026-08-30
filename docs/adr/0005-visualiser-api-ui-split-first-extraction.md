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
