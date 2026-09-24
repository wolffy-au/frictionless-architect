# ADR-0005: Visualiser API/UI split is the first extraction

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §8); revised 2026-09-05; revised 2026-09-24
- **Sources:** `ARCHITECTURE.md` §8, §8.1, §10, §11; `refactor-analyst` assessment (2026-08-30)

## Context

The restructure (ADR-0001, ADR-0002) needs a first, low-risk extraction to prove
the monorepo fan-out pattern. Today one FastAPI app serves both the JSON payload
and the HTML/JS UI, and reads Neo4j directly.

## Decision

Split the visualiser into two packages:

- `packages/schema-visualizer-api` — JSON only (`/schema-payload*`). Scope:
  `visualizer/{api,cache,config}.py` and the FastAPI router. Drops the
  server-rendered HTML route and Jinja/static mounts.
- `packages/schema-visualizer-ui` (or fold into `dashboard`) — a Vite app
  fetching `/schema-payload`.

`schema/manager.py`, `visualizer/data_loader.py` (Neo4j read path), and
`sample_parser.py` move to `packages/knowledge-graph` instead — none are
visualiser-specific, and the visualiser only ever needed read access.
`schema-visualizer-api` consumes `knowledge-graph` as a path-dependency
library, not over HTTP, until a second consumer needs that interface to
graduate — so the read-path interface stays narrow and free of leaked Neo4j
driver types now.

## Consequences

- Entry point changes: `uvicorn frictionless_architect.visualizer:app` →
  `uvicorn schema_visualizer_api:app`; update `README.md` / `quickstart.md`.
- `FRICTIONLESS_ARCHITECT_` env prefix stays as-is; renaming it is its own
  epic (`ARCHITECTURE.md` §9).
- Sequence: scaffold `knowledge-graph` → vendor forks → re-home specs →
  extract remaining components as work reaches them.

## Implementation status (2026-09-13)

The package split hasn't happened (`packages/` blocked on ADR-0001/0002). One
piece was actioned standalone: dropped the server-rendered `/schema-visualizer`
HTML route and its Jinja/static mounts from `visualizer/__init__.py`, and
repointed `README.md`/`quickstart.md` at `/schema-payload`.
`visualizer/static/`/`templates/` are now orphaned.

## Implementation status (2026-09-24)

`specs/003-oscal-ai-conversion` mounts a new `/oscal` router onto the same
FastAPI app the visualiser uses, so naming that shared app after the
visualiser no longer matched reality. The `app`/`lifespan` construction moved
out of `visualizer/__init__.py` into a neutral `frictionless_architect/app.py`;
entry point is now `uvicorn frictionless_architect.app:app`. This is an
interim rename for the current flat layout — `schema-visualizer-api` still
gets its own app object when the package split above happens.

## Alternatives considered

- **`schema-visualizer-api` calls `knowledge-graph` over HTTP from the start**
  — rejected: no second consumer yet; adds a service contract before it's
  needed.
- **Keep `sample_parser.py` in the API package** — rejected: no
  visualiser-specific coupling; would duplicate parsing logic once
  `knowledge-graph` needs it.
