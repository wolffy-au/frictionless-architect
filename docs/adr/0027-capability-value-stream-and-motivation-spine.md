# ADR-0027: Capability layer carries a value stream and an explicit motivation spine

- **Status:** Proposed
- **Date:** 2026-08-30
- **Sources:** this session; `architecture/model/elements.yaml` §A, `architecture/model/relationships.yaml` §A

## Context

The architecture model's Strategy and Motivation layers were under-connected:

- 4 drivers, 4 principles and 5 constraints had **zero** relationships — the
  skeleton view rendered them as orphan boxes, and no capability could be traced
  to *why* it exists or *what* constrains it.
- Two of the eight capabilities (`cap-digital-twin`, `cap-forensic-ledger`)
  realised no functional requirement, though the model's own comment calls each
  capability "a component contract".
- Capability names were half ability-phrased (`Executable Specification
  Generation`) and half named after the artefact they own (`Digital Twin
  Knowledge Graph`, `Forensic Audit & Compliance Ledger`).
- There was no model of how the capabilities combine to deliver value — the only
  end-to-end view was the business-process chain, which is choreography, not
  outcome.
- `cap-spec-engine` realised both `req-auto-spec-generation` and
  `req-regulatory-mapping`; obligation mapping is a control-catalog concern.
- Two constraints (`const-model-risk`, `const-model-governance`) were near
  duplicates.

## Decision

1. **Every capability realises at least one functional requirement.** Added
   `req-authoritative-twin` (realised by `cap-digital-twin`) and
   `req-immutable-audit-ledger` (realised by `cap-forensic-ledger`). Moved
   `req-regulatory-mapping` from `cap-spec-engine` to `cap-control-catalog`.

2. **Capabilities are named as abilities**, not the artefact they own:
   `cap-digital-twin` → *Architecture Knowledge Management*, `cap-control-plane`
   → *Agentic Development Supervision*, `cap-forensic-ledger` → *Forensic Audit
   Recording*, `cap-human-approval-workflow` → *Human Oversight & Approval*,
   `cap-control-catalog` → *Control & Obligation Management* (now explicitly
   covers the organisation's own standards and controls, not just external
   regulation), `cap-reusable-architecture` → *Reusable Architecture Curation*.
   IDs are unchanged.

3. **A value stream is the outcome-oriented view of delivery.**
   `vs-governed-delivery` "Governed Architecture Delivery" is a `Composition` of
   six stages (`ValueStream` elements): Establish Control & Reuse Baseline →
   Specify the Change → Build Under Supervision → Prove Compliance → Release &
   Attest → Reconcile & Remediate. Each stage is `Serving`-linked from the
   capabilities that enable it. `Capability → Capability` `Serving` edges record
   the dependency order (e.g. Architecture Knowledge Management serves Executable
   Specification Generation).

4. **"Architecture as Executable Intelligence" is an Outcome, not a Principle.**
   It is `Realization`-linked to a new `Goal`, *Frictionless Architecture &
   Governance at Machine Speed*, which the four drivers `Influence`. The value
   stream `Realization`-links to the outcome. This gives the motivation layer a
   spine: drivers → goal ← outcome ← value stream.

5. **Drivers `Influence` the functional requirements they motivate** (11 edges).
   `Principle → Requirement` and `Constraint → Requirement` wiring is a deliberate
   **deferred second pass**, to be done once this change is verified.

6. **`const-model-governance` merged into `const-model-risk`** —
   *Model Risk Management (SR 11-7 / APRA)*.

## Consequences

- The skeleton grows by 1 goal, 1 outcome and 7 value-stream elements. ADR-0010
  is annotated to reflect the new element counts; these are structural
  traceability, not the speculative detail ADR-0010 excluded.
- Two new views: **Capability Map & Value Stream** and **Delivery
  Choreography** (the latter carries the business-process chain, which was
  dropped from the now motivation-only skeleton view).
- Principle and Constraint elements are still only partially connected until the
  deferred second pass lands.
- `includes` free-text properties were removed from the six subsystems — the
  same decomposition is already carried by the section-C `ApplicationFunction`
  elements and their `Assignment` edges (unrelated cleanup, done in the same
  pass).
- Downstream `wiki/architecture-model.md` is stale until the next `wiki-librarian`
  run.

## Alternatives considered

- **Keep the business-process chain as the only delivery view** — rejected: it is
  choreography between components, not an outcome view; the value stream answers
  "what value, in what order" and the two coexist cleanly.
- **Wire principles/constraints in the same pass** — deferred by explicit choice
  to keep this change reviewable.
- **Leave the two unlinked capabilities as "foundational, no contract"** —
  rejected: both are load-bearing and deserve an explicit requirement.
