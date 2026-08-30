# ADR-0015: Machine-readability first — all artifacts are structured/executable data

- **Status:** Accepted
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 1; `specs/001` FR-019; `NONFUNCTIONALS.md` §"Usability & Efficiency"; `data-model.md`

## Context

The platform is a "digital twin" of an organisation's architecture that automates
governance. Governance automation, drift detection, and traceability queries are
only possible if every artifact is data a machine can parse and reason over.

## Decision

**All architectural artifacts must be executable or structured data**
(JSON / Markdown / graph). No artifact of record is free-form prose or an opaque
binary. This is a standing constraint on every feature, not a one-time choice.

## Consequences

- Drives the graph-native model (ADR-0007), the ArchiMate exchange format
  support, and one-click "Compliance Pack" exports.
- New formats or integrations must carry documented migration/mapping paths
  (Constitution VIII / `PROJECT_CONSTITUTION.md` VIII).
