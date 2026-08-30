# ADR-0012: ADRs are an attested finite-state machine

- **Status:** Accepted
- **Date:** 2026-02-18 (constitution ratification); refined in `specs/001`
- **Sources:** `data-model.md`; `specs/001-governance-platform/spec.md`
  (FR-005, FR-006, clarification Q); `PROJECT_SPECIFICATION.md` Phase 1

## Context

The platform's core premise is "the why over the what": every technical change
must be tied to a decision record with a legal-grade audit trail. ADRs therefore
need a governed lifecycle and non-repudiable sign-off.

## Decision

The Architecture Decision Record entity has attributes Title, Status, Date,
Rationale, Decision, Consequences, Human Attestation, and a fixed state machine:

```text
Draft → Under Review → Approved → Superseded
```

Moving to **Approved** or **Superseded** requires a **verifiable human
cryptographic signature** (AI may draft and detect conflicts, but cannot attest).
The platform must also flag when a new decision contradicts an existing ADR in
the graph (FR-014).

## Consequences

- ADR is a canonical example of the FSM + action-endpoint pattern (ADR-0026).
- The concrete cryptographic scheme and identity/certificate model is a deferred
  solution decision (`specs/001` §"Deferred solution decisions").
- This ADR log's own records follow the same lifecycle in their `Status` field.
