# ADR-0011: Platform decomposes into 6 subsystems

- **Status:** Accepted
- **Date:** 2026-08-29
- **Sources:** session memory `ecosystem-c4`; `architecture/model/README.md`
  §"Model contents" (section B); `architecture/model/diagrams/c4/container.puml`

## Context

The ~15 capabilities from the ecosystem brief were first drawn as a 15-container
("32 box") C4 diagram, which was too dense to read. `ARCHITECTURE.md` §3–4
documents an 8-component decomposition that no longer matches.

## Decision

Group the ~15 capabilities into **6 subsystems**:

1. Controls & Compliance Catalog
2. Reusable Architecture Library
3. Digital Twin & Knowledge Graph
4. Architecture Governance
5. Conformance & Drift Assurance
6. Modelling & Specification

Each container carries an `includes` property listing its constituent
capabilities. Architecture Governance explicitly covers competing solution
options (RFP / multi-vendor): comparative evaluation, decision, and archival of
rejected options with rationale into the KG intent plane. The Architecture
Knowledge Graph is one store with two planes (intent + digital twin).

## Consequences

- The unified architecture model (ADR-0007) already implements this: section B
  carries the platform `Grouping`, its 6 subsystems, shared stores, roles, and
  external systems, with subsystems `Realization`-linked to the section-A
  capabilities.
- Applied in #50: `ARCHITECTURE.md` §3–4 now maps the six subsystems to packages
  (`controls-compliance-catalog`, `reusable-architecture-library`,
  `digital-twin-knowledge-graph`, `architecture-governance`,
  `conformance-drift-assurance`, `modelling-specification`), and
  `PROJECT_SPECIFICATION.md` carried a historical note until it was retired
  (2026-09-26). The packaging /
  deployment view (`ARCHITECTURE.md` §3.3) is tracked separately in #55.
