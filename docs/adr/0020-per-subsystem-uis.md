# ADR-0020: Each subsystem ships its own UI

- **Status:** Accepted
- **Date:** unknown (pre-dates this log); revised 2026-09-26 (GH #50)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3; `ARCHITECTURE.md` §3–4, §10; GH #50
  (maintainer decision); [GH #55](https://github.com/wolffy-au/frictionless-architect/issues/55);
  `relationships.yaml` role↔subsystem Serving edges

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
- The schema-visualiser UI (ADR-0005's `schema-visualizer-ui`) no longer folds
  into a dashboard; its home is also open in #55.
- `turborepo` is adopted only once JS weight justifies a task graph (ADR-0002).

**Update (2026-09-27, GH #55): composition is role-aware, not just cross-subsystem.**

`relationships.yaml`'s role↔subsystem Serving edges show roles cut *across*
subsystems, not one-to-one with them — e.g. `role-ea` is served by
`sub-library`, `sub-governance` and `sub-assurance`; `role-compliance` by
`sub-catalog`, `sub-governance` and `sub-assurance`. Combined with journey
APIs being designed one-per-role so RBAC falls out of the API shape early
(user design preference, 2026-09-26), the composition layer's job isn't
occasional dashboard-style stitching — it's the default way most roles see
the platform at all, since most roles span multiple subsystems.

- **Cross-subsystem views must be composed per role journey**, from the
  subsystem UIs, rather than owned by a central dashboard — same "no central
  dashboard" constraint as before, but scoped explicitly to role, not just to
  ad hoc cross-cutting views like a traceability overview.
- **Resolved: composition is server-composed per role, not client-side
  runtime MFE** (Backstage plugins or a client shell app were the two
  alternatives considered — see below). Each subsystem's `ui/` stays an
  independently built/owned UI fragment; the role-facing page a given
  BusinessRole lands on is assembled server-side per journey, pairing
  naturally with that role's journey API rather than re-deriving role
  composition logic in a client-side plugin host or shell. Concrete
  mechanism (templating layer, per-role route ownership) is deferred to
  implementation; no new client-side composition framework
  (module federation, single-spa, Backstage) is adopted.
- Build tooling for the per-subsystem `ui/` trees remains open, tracked in #55.

## Alternatives considered

- **One Vite dashboard package, embedded in Backstage** (this record's original
  proposal) — rejected: a single frontend over six subsystems with different
  users recreates a cross-cutting component that ADR-0011's decomposition removed.
- **Leave the frontend open** — rejected: the package layout in `ARCHITECTURE.md`
  §3.2 needs a decision on where UI code lives.
- **Backstage plugins** (each subsystem `ui/` installed as a Backstage frontend
  plugin) — rejected for now: gets nav/auth/layout chrome for free, but imports
  a new platform dependency (a Backstage instance) nothing in this repo stands
  up today, and couples role-aware composition to Backstage's own plugin/
  permissions API rather than the journey-API shape already chosen.
- **Client-side shell app** (module federation / single-spa composing each
  `ui/` at runtime in the browser) — rejected for now: avoids the Backstage
  dependency, but re-derives per-role composition logic client-side that the
  journey APIs already express server-side, and inherits the usual
  client-MFE costs (duplicate framework runtimes, cross-fragment state sync).
