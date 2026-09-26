# ADR-0020: Each subsystem ships its own UI

- **Status:** Accepted
- **Date:** unknown (pre-dates this log); revised 2026-09-26 (GH #50)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3; `ARCHITECTURE.md` §3–4, §10; GH #50
  (maintainer decision)

## Context

The platform needs UIs for its users (digital-twin visualisation, attestation,
control authoring).

> **Revised 2026-09-26 (GH #50):** this record originally proposed a single
> Vite dashboard package (`packages/dashboard`), target-embedded in Backstage —
> the "Frontend Dashboard" component of the old 8-component grouping. It was
> never ratified or built. ADR-0011 replaced that grouping with six subsystems
> serving different roles (compliance authors control content in the catalog,
> architects work in the library and in governance, operations watches
> assurance), leaving no home for a central dashboard, so the decision was
> revised in place rather than superseded.

## Decision

Each subsystem package ships its own UI in a `ui/` tree beside its `api/`.
There is no central dashboard package.

## Consequences

- Package layout: `packages/<subsystem>/api/` + `packages/<subsystem>/ui/`
  (`ARCHITECTURE.md` §3–4).
- How the UIs are composed — Backstage plugins or a shell app — and their build
  tooling are open, tracked in #55 with the deployment view.
- The schema-visualiser UI (ADR-0005's `schema-visualizer-ui`) no longer folds
  into a dashboard; its home is also open in #55.
- Cross-subsystem views (e.g. a traceability overview spanning catalog,
  governance and assurance) must be composed from the subsystem UIs rather than
  owned by a dashboard.
- `turborepo` is adopted only once JS weight justifies a task graph (ADR-0002).

## Alternatives considered

- **One Vite dashboard package, embedded in Backstage** (this record's original
  proposal) — rejected: a single frontend over six subsystems with different
  users recreates a cross-cutting component that ADR-0011's decomposition removed.
- **Leave the frontend open** — rejected: the package layout in `ARCHITECTURE.md`
  §3.2 needs a decision on where UI code lives.
