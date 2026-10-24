# ADR-0004: Two-tier spec numbering

- **Status:** Accepted; implemented 2026-10-24 (migration step 6, GH #107)
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §6)
- **Sources:** `ARCHITECTURE.md` §6

## Context

Specs were a flat `specs/NNN-*` sequence across the whole platform, and there
was already a collision (`002-neo4j-schema-ui` vs `002-arch-kg-semantics`).
Per-component work would have made this worse.

## Decision

- **Root `specs/`** holds only cross-cutting **epic** specs, prefixed `EPIC-`.
- **Each `packages/<name>/specs/`** restarts its own `NNN-` sequence, scoped to
  that component.
- `.specify/scripts/bash/` is git-ignored and regenerated wholesale by
  `specify integration upgrade` (see `.claude/skills/README.md`), so it is
  never hand-patched. Instead each package that wants its own `NNN-` sequence
  carries a tracked `.specify` symlink back to the root install (one source of
  truth, not a per-package copy), and the tracked `scripts/speckit-package.sh`
  wrapper sets `SPECIFY_INIT_DIR` — an override `common.sh` already documents
  for exactly this ("running a Spec Kit command against a member project from
  a monorepo root without cd") — to point a vendored script's repo-root
  resolution at that package directory.

## Consequences

- Existing specs re-homed: `001-governance-platform` → `EPIC-001` (revised
  2026-09-26: the "or retire" option is closed — `PROJECT_SPECIFICATION.md` was
  retired instead and spec 001 is now the business specification, constitution
  v1.3.0); `002-neo4j-schema-ui` →
  `packages/schema-visualizer-api/specs/001-*` (that package hasn't extracted
  yet — §8 step 7 — so the directory holds only `specs/` and the `.specify`
  symlink until then); `002-arch-kg-semantics` (stub) was deleted before it
  gained any content — nothing to re-home.
- `003-gh-roadmap-archimate` (added 2026-10-05) and `004-conversational-model-authoring`
  (added 2026-10-08, after this issue was filed) re-homed to `EPIC-002` and
  `EPIC-003`: both drive root-level `architecture/model/` tooling, not any one
  package — the same backlog this ADR describes, not a new instance of it.
- Root keeps one platform constitution; per-component constitutions are optional
  lighter addenda.
- GH #102 (generate Gaps from speckit specs) reads spec directories under the
  old `specs/NNN-…` / `platform/packages/*/specs/` scan roots; its scope was
  updated for the new `EPIC-*` / per-package layout as part of this change.
