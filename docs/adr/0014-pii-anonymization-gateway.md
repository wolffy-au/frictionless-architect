# ADR-0014: Mandatory PII/PHI anonymization before any LLM processing

- **Status:** Accepted
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3, Phase 6; `specs/001` FR-004; `NONFUNCTIONALS.md` §Security

## Context

Decision capture ingests unstructured text from collaboration tools (Slack,
whiteboard transcripts) and passes it to an external LLM provider to draft ADRs.
That content routinely contains PII/PHI, which must not leave the trust boundary.
The same risk applies to every other path that sends first-party content to an
LLM: `architecture-governance`'s ADR/evaluation drafts, `modelling-specification`'s
spec drafts, and RFP/vendor submissions (which can carry named contacts) assessed
at engagement time. Only policy/regulatory-standard documents are categorically
different — authored, organization-owned governance text — and are exempted by
ADR-0031.

## Decision

A **PII Anonymization Gateway** is a mandatory sanitization layer: content from
every LLM ingestion path is scrubbed of PII/PHI **before** it is passed to an LLM
or other external/high-risk component, *except* policy/regulatory-standard
documents (ADR-0031's scoped exemption). In scope: collaboration-tool transcripts
(Slack, whiteboard) for AI-assisted ADR drafting, ADR/evaluation drafts, spec
drafts, and RFP/vendor submissions.

## Consequences

- The gateway is its own `pii-gateway` package — a **shared, non-subsystem**
  package built per ADR-0034's general pattern (sibling to `llm-provider-config`,
  composed into `sys-platform` the same way), not owned by any one of the six
  subsystems (ADR-0011). It is a sibling package rather than a merge into
  `llm-provider-config` itself: ADR-0034 explicitly scopes *which provider/
  credentials* out of *what content* is sent, and its own "one package per
  shared concern" rule keeps the two separate.
- Consuming subsystems (`architecture-governance`, `modelling-specification`,
  and any other LLM-calling function in scope) take it as a path dependency
  (ADR-0002), the same consumption pattern as `llm-provider-config` — no
  per-consumer Serving edge in the model, since this is a build-time dependency
  rather than a runtime service call.
- Adds a testable pre-processing stage to every in-scope ingestion path
  (FR-003 → FR-004). ADR-0031 remains the authoritative record of the
  policy-document exemption.
