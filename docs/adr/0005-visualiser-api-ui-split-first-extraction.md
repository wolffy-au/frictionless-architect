# ADR-0005: Controls catalog is the first extraction; visualiser API/UI split follows the knowledge graph

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §8); revised 2026-09-05; revised 2026-09-24; revised 2026-09-26 (GH #60: first extraction changed to `controls-compliance-catalog`)
- **Sources:** `ARCHITECTURE.md` §3.2, §8, §8.1, §8.2, §10, §11; `refactor-analyst` assessment (2026-08-30);
  GH #44, #60

## Context

The restructure (ADR-0001, ADR-0002) needs a first, low-risk extraction to prove
the monorepo fan-out pattern. Today one FastAPI app serves both the JSON payload
and the HTML/JS UI, and reads Neo4j directly.

This ADR first chose the visualiser API/UI split as that extraction. But the
split makes `schema-visualizer-api` consume `digital-twin-knowledge-graph` as a
library (below), and that package is only scaffolded at `ARCHITECTURE.md` §8
step 4 — so step 2 could not complete before step 4 existed (GH #60).
Meanwhile the policy-to-OSCAL pipeline (GH #44) became the delivery priority:
it is new code with no knowledge-graph dependency — in the model,
`Controls & Compliance Catalog` reads only the framework packs.

## Decision

**The first extraction is `packages/controls-compliance-catalog`**, created as
a new package to house the policy-to-OSCAL pipeline (GH #44) — the converter
code is written there, not in the flat `src/` and moved later. It depends on
nothing but the `platform/` skeleton (§8 step 1), so it can prove the pattern
(step 3) without waiting on the knowledge graph.

**The visualiser API/UI split moves after the knowledge-graph scaffold** (§8
step 4), as part of "extract remaining components" (step 7), so the read path
it consumes already exists when it is extracted. The split itself is
unchanged:

Split the visualiser into two packages:

- `packages/schema-visualizer-api` — JSON only (`/schema-payload*`). Scope:
  `visualizer/{api,cache,config}.py` and the FastAPI router. Drops the
  server-rendered HTML route and Jinja/static mounts.
- `packages/schema-visualizer-ui` (home open since ADR-0020 dropped the
  dashboard — #55) — a Vite app
  fetching `/schema-payload`.

`schema/manager.py`, `visualizer/data_loader.py` (Neo4j read path), and
`sample_parser.py` move to `packages/digital-twin-knowledge-graph` instead — none are
visualiser-specific, and the visualiser only ever needed read access.
`schema-visualizer-api` consumes `digital-twin-knowledge-graph` as a path-dependency
library, not over HTTP, until a second consumer needs that interface to
graduate — so the read-path interface stays narrow and free of leaked Neo4j
driver types now.

## Consequences

- Entry point changes: `uvicorn frictionless_architect.visualizer:app` →
  `uvicorn schema_visualizer_api:app`; update `README.md`.
- `FRICTIONLESS_ARCHITECT_` env prefix stays as-is; renaming it is its own
  epic (`ARCHITECTURE.md` §9).
- Sequence (`ARCHITECTURE.md` §8): `platform/` skeleton → `controls-compliance-catalog`
  → prove pattern → scaffold `digital-twin-knowledge-graph` → vendor forks → re-home
  specs → extract remaining components, the visualiser split among them.
- Policy-to-OSCAL (GH #44) needs the `platform/` skeleton (step 1) before its code
  has a home. `specs/003-oscal-ai-conversion`, which planned an `/oscal` router in
  the flat `src/` (see Implementation status 2026-09-24), is re-targeted at
  `packages/controls-compliance-catalog`.
- Step 3 proves the workspace lock and CI fan-out on a new package; moving
  existing code between packages is first exercised at step 4, when
  `digital-twin-knowledge-graph` absorbs `schema/manager.py` and `sample_parser.py`.

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

- **Keep the visualiser first; scaffold a minimal `digital-twin-knowledge-graph`
  read path (`data_loader.py`, `sample_parser.py`) inside step 2** — rejected:
  splits step 4 across two steps, and still leaves GH #44 waiting behind a
  visualiser refactor.
- **Keep the visualiser first; import the read path from the flat package until
  step 4** — rejected: a temporary dependency on the package being dismantled,
  which the read-path interface would then have to be carved out of twice.
- **Write GH #44's code in the flat `src/` and extract it later** — rejected:
  new code would be written in one place only to be moved, and the agents
  writing it would have no settled package to target.

- **`schema-visualizer-api` calls `digital-twin-knowledge-graph` over HTTP from the start**
  — rejected: no second consumer yet; adds a service contract before it's
  needed.
- **Keep `sample_parser.py` in the API package** — rejected: no
  visualiser-specific coupling; would duplicate parsing logic once
  `digital-twin-knowledge-graph` needs it.
