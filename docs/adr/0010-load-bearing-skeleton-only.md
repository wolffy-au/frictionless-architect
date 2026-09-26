# ADR-0010: Central model is a load-bearing skeleton only

- **Status:** Accepted; skeleton contents extended by [ADR-0027](0027-capability-value-stream-and-motivation-spine.md)
- **Date:** unknown (pre-dates this log; recorded in `architecture/model/README.md`; revised 2026-09-26 (GH #65))
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
8 primary capabilities, a 7-element value stream, and 11 business processes
(count as of 2026-09-13; grown from the original 6 as the process backbone
was fleshed out — see `git log -- architecture/model/elements.yaml`).

## Consequences

- NFR targets, agent rosters, and enabler capabilities are rebuilt inside each
  package's own spec when that package is real — not modelled centrally.
- The full prototype model stays on tag `archive/prototype-neo4j`.
- Wording is verbatim from the prototype except where product-specific terms were
  generalised; a full technology-agnostic pass is still owed.
- The skeleton may grow to carry genuine structural traceability (the motivation
  spine, the value stream) — ADR-0027 — but not the speculative detail this ADR
  excluded.
- The model also carries the platform's **own packaging and migration** (section E,
  GH #65): code packages as Artifacts realising their components, the
  `ARCHITECTURE.md` §8 restructure steps as Work Packages, and the platform's
  Baseline / Transition / Target Plateaus. These are load-bearing — ADR-0005's
  package dependency and the §8 order are decided against them — and are kept
  to what `ARCHITECTURE.md` §3.2 and §8 already commit to. Infrastructure (Nodes,
  SystemSoftware) waits for GH #55's open decisions.
