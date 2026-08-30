# ADR-0024: MVP is single-user and locally run

- **Status:** Accepted (explicit scoping compromise)
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` §"MVP Target"; `specs/002-neo4j-schema-ui/plan.md`; `ARCHITECTURE.md` §1

## Context

The full vision is a hosted, multi-user governance platform for a bank. Building
that first would delay any usable output for a long time.

## Decision

The **MVP target is a single-user, locally run application** with no requirement
for multi-user or hosted infrastructure. Feature 002 (the schema visualiser) is
built to that constraint — one analyst, fixed sample data, laptop CPU/memory
budgets.

## Consequences

- `ARCHITECTURE.md` §1 explicitly treats "single-user, locally run" as an
  **early scoping compromise, not a constraint on the target topology** — the
  monorepo restructure (ADR-0001/0002) is designed for the multi-component
  platform regardless.
- Break-Glass, RBAC/ABAC, and hosting concerns are specified but not MVP-blocking.
