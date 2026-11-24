# ADR-0056: Wire format for structured API error responses

- **Status:** Proposed
- **Date:** 2026-11-24
- **Sources:** `specs/EPIC-001-governance-platform/spec.md` "Deferred solution decisions"
  ("Wire format for structured API error responses"); `specs/EPIC-001-governance-platform/contracts/api.yaml`
  (every error response, `application/problem+json` + `#/components/schemas/Error`);
  `platform/packages/llm-provider-config/src/llm_provider_config/router.py`;
  `platform/packages/modelling-specification/src/modelling_specification/router.py`;
  `platform/packages/pii-gateway/src/pii_gateway/router.py` (all raise plain
  `fastapi.HTTPException(status_code=..., detail=...)`)

## Context

`specs/EPIC-001-governance-platform/spec.md` lists "wire format for structured API error
responses" under **Deferred solution decisions** — explicitly not yet decided. Its own
contract, `contracts/api.yaml`, already fixes an answer throughout: every documented error
response uses `application/problem+json` against a shared `Error` schema (RFC 7807-shaped),
for every endpoint across auth, ADRs, model, compliance, and break-glass.

Three built packages with real FastAPI routers — `llm-provider-config`,
`modelling-specification`, `pii-gateway` — do not follow that contract. They raise plain
`fastapi.HTTPException(status_code=..., detail=...)`, which FastAPI serialises as
`application/json` with a bare `{"detail": "..."}` body, not `problem+json` and not the
`Error` schema the contract names. No ADR records either choice, so there is nothing to
reconcile the contract's implicit decision against the implementation's different one.

## Decision

> DRAFT — confirm: pick one of (a) ratify `application/problem+json` / RFC 7807 as the
> platform-wide error wire format and treat the three packages above as needing a
> conformance fix, or (b) ratify the plain FastAPI `HTTPException` `{"detail": ...}` shape
> actually built today and update `contracts/api.yaml` (and `spec.md`'s deferred-decision
> entry) to match, or (c) something else. This stub does not pick a side — no built
> consumer of either shape was found to argue from, and the EPIC-001 contract has not been
> ratified against the running code.

## Consequences

> DRAFT — confirm: whichever option is chosen, every package with a FastAPI router needs
> the same error-handling convention (FastAPI exception handler registration, or a shared
> helper in a package like `llm-provider-config`'s sibling pattern, ADR-0034) so new
> packages do not repeat today's drift. `spec.md`'s "Deferred solution decisions" entry
> should be resolved (moved to Accepted / removed from the deferred list) once this is
> ratified, via `speckit-specify`'s normal spec-alignment flow, not by editing the spec
> directly from this ADR.

## Alternatives considered

> DRAFT — confirm: no alternatives beyond the two shapes already found in the repo
> (`problem+json`/RFC 7807 in the contract, plain `HTTPException` in the implementation)
> were identified; a human should weigh in other candidates (e.g. a custom envelope with
> `code`/`message`/`details`, as `TECHNICAL.md`'s general "Consistent Error Responses"
> guidance gestures at without naming a format) if any are live options.
