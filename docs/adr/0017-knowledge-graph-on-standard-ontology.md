# ADR-0017: Knowledge graph built on a standard ontology

- **Status:** Proposed (from `PROJECT_SPECIFICATION.md`; not re-ratified in `specs/001`)
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3

## Context

An architecture knowledge graph accumulates microservices, data domains, CBS, and
regulations from many sources. Without a shared ontology it degrades into a "data
swamp" where nothing joins cleanly.

## Decision

Build the knowledge graph on a **standardized ontology** — e.g. the **Backstage
Software Catalog** or the **C4 model** — rather than an ad-hoc schema.

## Consequences

- Constrains the `knowledge-graph` package's node/edge vocabulary.
- Interacts with ADR-0008 (ArchiMate concept names as the model vocabulary) — the
  reconciliation between an ArchiMate-typed model and a Backstage/C4 ontology is
  unresolved and should be settled when `knowledge-graph` is scaffolded.
- Persistence technology for the semantic model is a deferred solution decision
  (`specs/001`), though Neo4j is the working assumption (ADR-0018).
