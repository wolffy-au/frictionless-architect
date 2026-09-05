# ADR-0005: Visualiser API/UI split is the first extraction

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §8); revised 2026-09-05
- **Sources:** `ARCHITECTURE.md` §8, §8.1, §10, §11; `refactor-analyst` assessment (2026-08-30)

## Context

The restructure (ADR-0001, ADR-0002) needs a first, low-risk extraction to prove
the monorepo fan-out pattern (root CI fans out, shared lock resolves, tests
pass). Today one FastAPI app (`visualizer/api.py`) serves both the JSON payload
and the HTML/JS UI, and reads Neo4j directly via `visualizer/data_loader.py`.

## Decision

The **first extraction** splits the visualiser into two packages:

- `packages/schema-visualizer-api` — JSON only (`/schema-payload`, `/refresh`,
  `/status`). Scope: `visualizer/{api,cache,config}.py`, the payload /
  coverage-merge logic, and the FastAPI router. Drop the server-rendered HTML
  route and Jinja/static mounts — confirmed no consumer today.
- `packages/schema-visualizer-ui` (or fold into `dashboard`) — a Vite app that
  fetches `/schema-payload`.

`schema/manager.py` (the Neo4j write/migrate/audit controller),
`visualizer/data_loader.py` (the Neo4j read path), and `sample_parser.py`
do **not** move into `schema-visualizer-api`:

- `sample_parser.py` is dependency-free stdlib ArchiMate-XML parsing with no
  coupling to FastAPI/cache/config — generic ingestion, not visualiser logic —
  so it moves to `packages/knowledge-graph` with the rest of the ingestion
  path.
- `manager.py` and the Neo4j read path belong with `knowledge-graph` for the
  same reason: the visualiser only ever needed read access, not the
  write/migrate/audit surface.
- `schema-visualizer-api` consumes `knowledge-graph` as a **path-dependency
  library** (its own Neo4j connection), not over HTTP — matches
  `ARCHITECTURE.md` §3.3 and avoids a service contract before there's a second
  consumer. This is expected to graduate to HTTP later (more consumers, or
  independent scaling), so the read-path interface must stay narrow and free
  of leaked Neo4j driver types — a seam to swap, not a rewrite.

## Consequences

- Entry point changes: `uvicorn frictionless_architect.visualizer:app` →
  `uvicorn schema_visualizer_api:app`; update `README.md` / `quickstart.md`.
- The `FRICTIONLESS_ARCHITECT_` env prefix is kept as-is for this step; renaming
  it is its own epic (`ARCHITECTURE.md` §9).
- Subsequent sequence: scaffold `knowledge-graph` → vendor forks → re-home specs
  → extract remaining components as work reaches them.
- Placement and library-vs-HTTP questions are settled; the extraction can
  proceed against them without revisiting placement.

## Alternatives considered

- **`schema-visualizer-api` calls `knowledge-graph` over HTTP from the start**
  — rejected for now: no second consumer yet, and it adds a service contract
  and internal auth before either is needed. Revisit if `knowledge-graph`
  gains other consumers or the two packages need independent scaling.
- **Keep `sample_parser.py` in the API package** — rejected: it has no
  visualiser-specific coupling, and leaving it behind would duplicate parsing
  logic once `knowledge-graph`'s own ingestion path needs it.
