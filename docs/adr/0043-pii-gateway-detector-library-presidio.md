# ADR-0043: Presidio as the `pii-gateway` detection/anonymization engine

- **Status:** Proposed
- **Date:** 2026-10-31
- **Sources:** GH #136 (`pii-gateway` package build), ADR-0014 (mandatory scrubbing scope), ADR-0034 (shared-package pattern)

## Context

ADR-0014 mandates that every in-scope LLM ingestion path be scrubbed of PII/PHI
before content leaves the trust boundary, but leaves the detector-library choice
open. GH #136 (building `platform/packages/pii-gateway`) requires that choice be
recorded before the package ships, including PHI-specific categories (ADR-0014's
language), not just generic PII.

A GitHub contributor (`emorilebo`, GH #136 comments) proposed building the gateway
around their own third-party package, `sether` (PyPI, MIT licensed, v0.4.1 at time
of writing). It was evaluated alongside the established options below.

## Decision

We use **Presidio** (`presidio-analyzer` + `presidio-anonymizer`, MIT licensed;
originated at Microsoft, now maintained under the `data-privacy-stack` GitHub
org at `github.com/data-privacy-stack/presidio`) as the detection and
anonymization engine inside `pii-gateway`. It
provides the `scrub()` contract's detection (regex + NER-based recognizers) and
anonymization (redact/replace/hash) primitives; `pii-gateway` wraps it with this
platform's config surface (detector categories, failure-mode behavior) and
consumer-facing `ScrubResult` type, per GH #136's scope.

## Consequences

- Adds `presidio-analyzer`, `presidio-anonymizer`, and their `spacy` dependency
  (plus a spaCy language model) to `pii-gateway`'s `pyproject.toml` — heavier
  than a regex-only alternative, but the NER model is what makes name/address
  detection reliable in free-text transcripts rather than just structured fields.
- Custom PHI recognizers (medical record numbers, provider/patient identifiers
  per ADR-0014's PHI language) are added as Presidio custom recognizers in
  `pii-gateway`, not sourced from a third party — these are first-party and
  testable per GH #136's acceptance criteria.
- Revisit if Presidio's spaCy dependency proves too heavy for the deployment
  target (ADR-0024's single-user local MVP posture), or if a maintained,
  audited lighter-weight alternative emerges with equivalent PHI coverage.
- **Model impact**: adds `sw-presidio` (`SystemSoftware`) to `architecture/model/`, wired
  to `sub-pii-gateway` with a `Serving` relationship (ADR-0044's "subject of its own ADR
  decision" bar). Diagrams including `sub-pii-gateway` are regenerated in the same change.

## Alternatives considered

- **`sether` (third-party PyPI package, MIT)** — rejected. Functionally
  plausible (streaming redaction, decoy/restore mode, LLM-framework
  middlewares) and the license is clear and compatible, but it is a
  single-maintainer package three months old at time of review (first PyPI
  release 2026-07-03, five releases total, one GitHub contributor) with no
  independent audit history. Adopting an unaudited, newly-published dependency
  as the engine sitting directly in the PHI data path is a disproportionate
  supply-chain risk for what this package guarantees (Principle V). Revisit if
  it accumulates a longer track record and independent security review.
- **`scrubadub` (MIT)** — rejected as primary engine. Lighter weight than
  Presidio (regex + optional spaCy detectors) but has no healthcare-specific
  PHI recognizers out of the box, so it would need the same amount of
  first-party PHI-recognizer work as Presidio while starting from a smaller,
  less actively maintained detector base.
- **Cloud DLP APIs (AWS Comprehend Medical, Google Cloud DLP)** — rejected.
  Both require sending the very content being screened for PII/PHI to another
  third-party API for analysis, which contradicts the trust-boundary premise
  ADR-0014 is built on, and adds a network dependency and per-call cost to a
  path that must work offline/locally per this platform's MVP posture
  (ADR-0024).
- **Hand-rolled regex only, no NER** — rejected as insufficient on its own.
  Regex alone covers structured categories (email, phone number, basic address
  patterns) adequately, but free-text name detection and most PHI categories
  (diagnoses, provider names referenced in prose) need context-aware NER;
  regex-only would under-detect exactly the free-text collaboration-tool and
  spec-draft content ADR-0014 is scoped around. Presidio is used instead of
  writing and maintaining an equivalent NER-based recognizer set from scratch.
