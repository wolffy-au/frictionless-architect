# ADR-0026: Governed-lifecycle entities are FSMs with action-based endpoints

- **Status:** Accepted
- **Date:** 2026-02-18 (Constitution VI); detail in `TECHNICAL.md`
- **Sources:** `.specify/memory/constitution.md` VI; `TECHNICAL.md`
  §"Software Architectural Patterns" / §"API Design Principles"; `data-model.md`

## Context

Governance entities (ADRs, Break-Glass exceptions, managed-drift tickets) have
distinct states and illegal transitions. Exposing raw state fields via CRUD lets
callers put an entity into an invalid state and loses the "why" of a transition.

## Decision

Model entities with governed lifecycles as **finite state machines**. Document
each entity's states and transition rules and enforce them with Pydantic models.
Prefer **action-based endpoints** (`/resource/{id}/action`) that trigger state
changes as side-effects over direct state updates.

## Consequences

- ADR lifecycle (ADR-0012), Break-Glass expiry, and drift tickets all follow this
  pattern.
- Complements the DDD guidance in `TECHNICAL.md` (FSMs manage aggregate state).
- Every state/output change must be traceable via logging or metadata
  (Constitution VII).
