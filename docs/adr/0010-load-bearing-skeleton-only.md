# ADR-0010: Central model is a ~30-node load-bearing skeleton only

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `architecture/model/README.md`)
- **Sources:** `architecture/model/README.md`

## Context

The `prototype-neo4j` model had 95 nodes / 143 relationships across three
ArchiMate layers — stakeholders, SWOT assessments, goals, outcomes with
placeholder target metrics, six "enabler" capabilities, speculative named AI
agents. Much of it was modelling detail against component boundaries that are
still being decided (ADR-0011).

## Decision

The centrally maintained model is the **load-bearing subset only** — ~30 nodes
(4 drivers, 4 principles, 5 constraints, 5 functional requirements, 6 primary
capabilities, 6 business processes) plus 13 edges. It is **decomposition input**,
not the final architecture. The 6 primary capabilities map ~1:1 onto the platform
grouping and are trusted as the skeleton.

## Consequences

- NFR targets, agent rosters, and enabler capabilities are rebuilt inside each
  package's own spec when that package is real — not modelled centrally.
- The full prototype model stays on tag `archive/prototype-neo4j`.
- Wording is verbatim from the prototype except where product-specific terms were
  generalised; a full technology-agnostic pass is still owed.
