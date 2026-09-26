# ADR-0031: Policy/standard documents bypass the PII anonymization gateway

- **Status:** Accepted
- **Date:** 2026-09-24
- **Sources:** `specs/003-oscal-ai-conversion/spec.md` FR-016; `specs/003-oscal-ai-conversion/plan.md` Constitution Check (V. Security)

## Context

`ADR-0014` requires PII/PHI anonymization before any content reaches an
LLM, written for decision capture's ingestion of unstructured
collaboration-tool text (Slack, whiteboard transcripts). `specs/003-oscal-ai-conversion`
sends verbatim policy/regulatory-standard document text to an LLM with no
redaction step (FR-016) — a different ingestion path than the one
`ADR-0014` was written for.

## Decision

FR-016's no-redaction behavior is a scoped exception to `ADR-0014`, limited
to the OSCAL conversion ingestion path. Policy and regulatory-standard
documents are authored, organization-owned governance text — categorically
different from incidental personal data swept up from collaboration-tool
capture. `ADR-0014`'s gateway remains mandatory for every other LLM
ingestion path.

## Consequences

- `ADR-0014`'s Decision text is unchanged; this ADR narrows its scope
  rather than amending it.
- If a policy/standard document is later found to routinely carry PII/PHI
  (e.g. named individuals in an internal HR policy), revisit — scope
  FR-016 further or route that document class through the gateway.
- No redaction code is added for this feature; `ext-llm`
  (`specs/003-oscal-ai-conversion/research.md` R2) passes document text
  through as-is.

## Alternatives considered

- **Run policy/standard documents through the existing PII gateway
  anyway** — rejected: the gateway doesn't exist as first-party code yet;
  building it as a prerequisite here would scope-creep a conversion
  pipeline into also delivering an unrelated component.
- **Amend `ADR-0014` with a blanket document-type carve-out** — rejected:
  its rule is correct for the ingestion path it was written to cover;
  narrowing it in place would weaken it there.
