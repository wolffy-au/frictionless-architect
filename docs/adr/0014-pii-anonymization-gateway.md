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
drafts, RFP/vendor submissions, and the conversational-modelling agent's own
prompts (`fn-conversational-authoring`, ADR-0037, GH #68/#108 — added
2026-10-31, `specs/EPIC-001-governance-platform/spec.md` Clarifications session
2026-10-31: no exemption basis comparable to ADR-0031's applies to that agent's
architect-authored free text).

**Default failure-mode behavior (added 2026-10-31, GH #136):** when the gateway
detects a PII/PHI match, the default action is **auto-redact and proceed** for
every consumer except the conversational-modelling agent
(`fn-conversational-authoring`, ADR-0037), which defaults to
**flag-for-review** instead — a match pauses the call and the architect
confirms, edits, or overrides it before it proceeds, since that agent already
has a human present in the same conversational turn. Neither default is a
hard-block. Per-category tuning (e.g. a stricter default for PHI-specific
recognizers than for email/phone) is left to `pii-gateway`'s config surface
(GH #136 scope) rather than decided here.

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
- **Model impact:** none — `fn-conversational-authoring` (GH #68/#108, built as
  `modelling-specification.authoring.delta.propose_delta()`) takes `pii-gateway`
  as a path dependency the same way `architecture-governance` and
  `modelling-specification`'s other consumers do; no new Serving edge is
  modelled, consistent with the no-per-consumer-edge statement above.

## Amendment (2026-10-31, GH #181 spec-alignment follow-up)

GH #136's spec-alignment audit flagged that `propose_delta()` called `scrub()`
with `context="spec-generator"` — a context with no real caller, since there is
no `fn-spec-generator` implementation in this codebase. The one context
purpose-built for this call, `"conversational-authoring"` (already seeded with
`flagged_for_review` in `pii-gateway`'s own config defaults), was never actually
used by it: every match was silently auto-redacted and sent on, exactly the
behavior this ADR rejected under "Auto-redact globally, including the
conversational agent" above.

Fixed: `propose_delta()` now calls `scrub()` with
`context="conversational-authoring"`. A flagged match no longer proceeds to the
LLM call at all — `delta.py` raises `PiiReviewRequired` and the
`modelling-specification` router (`POST /authoring/sessions/{id}/propose`)
returns `{"status": "pii_review_required", "matches": [...]}` with no LLM call
made; the architect resolves it via `POST .../propose/resolve-pii`
(`redact`/`allow`/`edit`) before the call proceeds with the resolved text. This
closes the gap between this ADR's decision and `fn-conversational-authoring`'s
actual behavior; no further model or decision change follows from it.

## Alternatives considered

- **Hard-block globally on any match (added 2026-10-31)** — rejected. The
  automated, unattended paths (`fn-governance-eval`, `fn-spec-generator`) have
  no human present at call time to resolve a false positive; a block would
  stop ADR/spec drafting outright on any detector false alarm, and this
  platform's content is mostly ordinary technical prose where false positives
  are expected.
- **Flag-for-review globally** — rejected. The same unattended paths have no
  one to flag to; a pending confirmation with no confirmer is a silent stall,
  not a safety improvement.
- **Auto-redact globally, including the conversational agent** — rejected.
  That agent already has the architect present in the same conversational
  turn (ADR-0037's "within one conversational turn" framing); silently
  mutating their free-text input on a detector guess costs them nothing to
  avoid, by asking instead, where the automated paths have no one to ask.
