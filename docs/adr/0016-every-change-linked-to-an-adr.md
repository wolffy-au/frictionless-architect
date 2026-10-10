# ADR-0016: Every technical change links to an ADR ("why over what")

- **Status:** Accepted
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 1; `specs/001` FR-005

## Context

A regulated bank must be able to explain *why* its architecture is the way it is,
not just *what* it is. Undocumented change is the friction the platform exists to
remove.

## Decision

Every technical change must be linked to an **Architecture Decision Record** that
captures the trade-offs. "The why over the what" is a governing principle: the
platform produces ADRs (FR-005) and ties each change to one.

## Consequences

- The platform enforces this for its *users'* architectures; this repo adopts the
  same discipline via this `docs/adr/` log for its *own* load-bearing decisions.
- ADR conflict detection (ADR-0012, FR-014) depends on decisions being captured
  in the graph rather than lost in chat.
- Extended 2026-10-04 (constitution Principle X, commits `1a7408d`/`491d8e7`): a
  `speckit-plan` must state its own **model impact** — the element, relationship
  and view ids it adds, changes or retires in `architecture/model/`, or "none" —
  so a plan's effect on the model is traceable the same way a technical change is
  traceable to an ADR. `tasks.md` then carries the matching model edits,
  `validate.py` and diagram regeneration. Recorded directly in the constitution
  (its own Sync Impact Report) rather than as a separate ADR, since it is a
  procedural extension of this decision, not a new one.
