# ADR-0014: Mandatory PII/PHI anonymization before any LLM processing

- **Status:** Accepted
- **Date:** unknown (pre-dates this log)
- **Sources:** `PROJECT_SPECIFICATION.md` Phase 3, Phase 6; `specs/001` FR-004; `NONFUNCTIONALS.md` §Security

## Context

Decision capture ingests unstructured text from collaboration tools (Slack,
whiteboard transcripts) and passes it to an external LLM provider to draft ADRs.
That content routinely contains PII/PHI, which must not leave the trust boundary.

## Decision

A **PII Anonymization Gateway** is a mandatory sanitization layer: all
unstructured data ingested from collaboration tools is scrubbed of PII/PHI
**before** any content is passed to an LLM or other external/high-risk component.

## Consequences

- The gateway may start inside `governance-engine` and split into its own
  `pii-gateway` package later (`ARCHITECTURE.md` §10 open question).
- Adds a testable pre-processing stage to every ingestion path (FR-003 → FR-004).
