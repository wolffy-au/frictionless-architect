# ADR-0018: Data layer — Postgres for metadata, Neo4j for the knowledge graph

- **Status:** Proposed
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3; `specs/002-neo4j-schema-ui/plan.md`

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
  and for platform metadata" as a **deferred solution decision** — so this record
  is Proposed: it captures the `PROJECT_SPECIFICATION.md` intent and current
  implementation direction, pending formal re-ratification.
- Local dev is intended to provide both via `orchestration/compose/` (plus
  OPA) once scaffolded; no `orchestration/` directory or Postgres dependency
  exists yet — only Neo4j is wired up today (ADR-0023).
