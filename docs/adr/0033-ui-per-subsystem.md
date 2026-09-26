# ADR-0033: Each subsystem ships its own UI

- **Status:** Accepted
- **Date:** 2026-09-26
- **Sources:** GH #50 (maintainer decision); supersedes [ADR-0020](0020-vite-dashboard-in-backstage.md)

## Context

ADR-0020 proposed a single Vite dashboard package (`packages/dashboard`) as the
platform's frontend, the "Frontend Dashboard" component of the old 8-component
grouping. ADR-0011 replaced that grouping with six subsystems, each serving
different roles (compliance authors control content in the catalog, architects
work in the library and in governance, operations watches assurance), and left
no home for a central dashboard.

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

## Alternatives considered

- **One dashboard package (ADR-0020)** — rejected: a single frontend over six
  subsystems with different users recreates a cross-cutting component that
  ADR-0011's decomposition removed.
- **Leave the frontend open** — rejected: the package layout in `ARCHITECTURE.md`
  §3.2 needs a decision on where UI code lives.
