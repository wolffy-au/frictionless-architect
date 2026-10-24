# ADR-0018: Data layer — Postgres for metadata, Neo4j for the knowledge graph

- **Status:** Accepted (bumped 2026-10-18 — see Consequences)
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3; `platform/packages/schema-visualizer-api/specs/001-neo4j-schema-ui/plan.md`;
  [GH #55](https://github.com/wolffy-au/frictionless-architect/issues/55)

## Context

The platform has two distinct storage needs: persistent relational metadata, and
a highly connected semantic model best queried as a graph.

## Decision

- **Postgres** for persistent platform metadata.
- **Neo4j 5.x** for the architecture knowledge graph / semantic system model.

The implemented schema visualiser already targets Neo4j 5.x (with a sample-data
fallback, ADR-0023).

## Consequences

- `specs/001` explicitly lists "persistence technologies for the semantic model
  and for platform metadata" as a **deferred solution decision** — the original
  Proposed status captured the `PROJECT_SPECIFICATION.md` intent and current
  implementation direction pending formal re-ratification. **Bumped to Accepted
  2026-10-18**: enough specs now cite Neo4j as settled fact (e.g.
  `platform/packages/digital-twin-knowledge-graph`'s spec/plan) that leaving the
  ADR itself Proposed understated how load-bearing it already is in practice.
  The Postgres half remains unimplemented (no `orchestration/` directory, no
  Postgres dependency wired up — only Neo4j, per ADR-0023) — Accepted records
  the *decision*, not that both halves are built yet.
- Local dev is intended to provide both via `orchestration/compose/` (plus
  OPA) once scaffolded; no `orchestration/` directory or Postgres dependency
  exists yet — only Neo4j is wired up today (ADR-0023).

**Update (2026-09-27, GH #55):** the target runtime is phased, resolving #55's
"local compose only, or a hosted cluster?" question:

- **Local compose is the runtime through the MVP milestone** (ADR-0024's
  single-user, locally run MVP — milestone itself is a specific future point,
  currently undated): `orchestration/compose/` above stays the only deployment
  shape until then.
- **Target architecture moves to a hosted cluster** (Postgres + Neo4j) once
  past that milestone. The concrete shape — managed service vs. self-managed,
  which orchestrator — is deliberately deferred to a follow-up ADR; nothing in
  the codebase argues for one option yet.
