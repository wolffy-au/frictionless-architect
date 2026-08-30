# ADR-0010: Central model is a load-bearing skeleton only

- **Status:** Accepted; skeleton contents extended by [ADR-0027](0027-capability-value-stream-and-motivation-spine.md)
- **Date:** unknown (pre-dates this log; recorded in `architecture/model/README.md`)
- **Sources:** `architecture/model/README.md`

## Context

The `prototype-neo4j` model had 95 nodes / 143 relationships across three
ArchiMate layers — stakeholders, SWOT assessments, goals, outcomes with
placeholder target metrics, six "enabler" capabilities, speculative named AI
agents. Much of it was modelling detail against component boundaries that are
still being decided (ADR-0011).

## Decision

The centrally maintained model is the **load-bearing subset only** — the
motivation, strategy, and business-process backbone that stays true regardless
of how component boundaries finally land. It is **decomposition input**, not the
final architecture. The primary capabilities map ~1:1 onto the platform grouping
and are trusted as the skeleton.

As of [ADR-0027](0027-capability-value-stream-and-motivation-spine.md) the
skeleton (section A of `architecture/model/elements.yaml`) holds: 4 drivers,
1 goal, 1 outcome, 3 principles, 4 constraints, 9 functional requirements,
8 primary capabilities, a 7-element value stream, and 6 business processes.

## Consequences

- NFR targets, agent rosters, and enabler capabilities are rebuilt inside each
  package's own spec when that package is real — not modelled centrally.
- The full prototype model stays on tag `archive/prototype-neo4j`.
- Wording is verbatim from the prototype except where product-specific terms were
  generalised; a full technology-agnostic pass is still owed.
- The skeleton may grow to carry genuine structural traceability (the motivation
  spine, the value stream) — ADR-0027 — but not the speculative detail this ADR
  excluded.
