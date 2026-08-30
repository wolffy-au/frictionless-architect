# ADR-0013: Authorization is a dedicated policy component, separate from authentication

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; `specs/001` clarification)
- **Sources:** `specs/001-governance-platform/spec.md` (FR-015, FR-016, clarification Q)

## Context

The platform must authenticate both human users and automated agents, and must
make access-control decisions consistently across capabilities. Baking
authorization logic into each service or into the auth mechanism couples policy
to identity.

## Decision

**Authentication establishes identity; authorization decisions are made by a
separate, dedicated policy component** that consumes verified identity
attributes. The authentication mechanism must supply those attributes.

## Consequences

- The authorization model and policy-rule language, and the token/session
  mechanism, are deferred solution decisions (`specs/001`).
- Aligns with the OPA/Rego direction (ADR-0019) and ABAC in `NONFUNCTIONALS.md`.
