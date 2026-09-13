# ADR-0004: Two-tier spec numbering

- **Status:** Accepted; not yet implemented — `specs/` is still the flat
  pre-migration layout (see Consequences)
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §6)
- **Sources:** `ARCHITECTURE.md` §6

## Context

Specs are today a flat `specs/NNN-*` sequence across the whole platform, and
there is already a collision (`002-neo4j-schema-ui` vs `002-arch-kg-semantics`).
Per-component work will make this worse.

## Decision

- **Root `specs/`** holds only cross-cutting **epic** specs, prefixed `EPIC-`.
- **Each `packages/<name>/specs/`** restarts its own `NNN-` sequence, scoped to
  that component.
- `.specify/scripts/bash/` scripts gain a `--package <name>` argument targeting
  `packages/<name>/specs/`, kept as one source of truth (not per-package copies).

## Consequences

- Existing specs re-home: `001-governance-platform` → `EPIC-001` (or retire —
  open question, `ARCHITECTURE.md` §10); `002-neo4j-schema-ui` →
  `packages/schema-visualizer-api/specs/001-*`; `002-arch-kg-semantics` (stub) →
  `packages/knowledge-graph/specs/002-*` or delete.
- The `.specify` scripts need patching before per-component specs can be created.
- Root keeps one platform constitution; per-component constitutions are optional
  lighter addenda.
- **This is outstanding** (2026-09-13): `specs/` still holds the flat, un-migrated
  `001-governance-platform` / `002-neo4j-schema-ui` layout — no `EPIC-*` specs,
  no `packages/*/specs/`, and `.specify/scripts/bash/` has no `--package`
  argument. Blocked on the same `packages/` monorepo layout ADR-0001/ADR-0002
  still owe.
