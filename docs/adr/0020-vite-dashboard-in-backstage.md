# ADR-0020: Frontend is a Vite dashboard, target-embedded in Backstage

- **Status:** Proposed (Backstage embedding unconfirmed)
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3; `ARCHITECTURE.md` §4 (component 7), §10

## Context

The platform needs a governance dashboard (digital-twin visualisation,
attestation UI). Developers are the primary users and already work in a developer
portal.

## Decision

Build the dashboard as a **Vite-based SPA**, delivered as a pnpm sub-tree inside
the monorepo (`packages/dashboard`), with the **target** of embedding it in the
**Backstage** developer portal.

## Consequences

- Whether it ships as a Backstage plugin or a standalone SPA is an open question
  (`ARCHITECTURE.md` §10) that changes the package's build shape — hence Proposed.
- The schema-visualiser UI (ADR-0005) folds into this dashboard or ships as a
  small sibling package.
- `turborepo` is adopted only once JS weight justifies a task graph (ADR-0002).
