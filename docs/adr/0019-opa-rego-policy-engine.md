# ADR-0019: Policy engine is Open Policy Agent (Rego); bypass raises managed-drift debt

- **Status:** Proposed
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3, Phase 4; `specs/001` FR-009, FR-020

## Context

The platform must automatically enforce APRA CPS 230 / 234 and RBAC/ABAC policy,
and must handle the case where a team deliberately bypasses a policy during an
incident (ADR-0024's Break-Glass).

## Decision

- Integrate **Open Policy Agent** with policies authored in **Rego**.
- "**Managed Drift**": when a policy is bypassed, the system auto-generates a
  technical-debt ticket (FR-009) rather than silently allowing the deviation.

## Consequences

- `specs/001` de-specifies "the concrete authorization model and policy-rule
  language" as a deferred decision — hence Proposed, pending re-ratification.
- Rego policies get their own unit tests to prevent CI "false passes"
  (`PROJECT_SPECIFICATION.md` Phase 11).
- Lives in the `policy-enforcement` package, wrapping OPA + forked OSCAL tooling.
