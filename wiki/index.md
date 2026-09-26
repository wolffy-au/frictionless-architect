---
title: Frictionless Architect Wiki
generated: 2026-09-26
generator: claude-opus-5-5
---

> This wiki is **generated** by the `wiki-librarian` skill from the sources
> declared in [`sources.yaml`](sources.yaml). Don't edit pages here — change
> `sources.yaml` (add a topic, add a source, adjust a glob) and rebuild.
> Build state is tracked in `.build-log.yaml`.

## Topics

- [Project Overview](project-overview.md) — what Frictionless Architect is, its
  business specification (spec 001, which replaced `PROJECT_SPECIFICATION.md`),
  who it's for, the headline capabilities, and which parts are actually built.
- [Governance & Constitution](governance-and-constitution.md) — the single
  SpecKit Constitution at the root of the document tree (principles I–X), the
  document index and conflict-resolution rule, the six-stage workflow, and
  quality gates.
- [Architecture Overview](architecture.md) — the governance-layer-at-root
  principle, current vs. target state, the six-subsystem → package mapping
  (per-subsystem UIs), the Poetry monorepo decision, the migration sequence, and the full `docs/adr/`
  decision log.
- [Architecture Model](architecture-model.md) — the canonical graph-loadable
  YAML model in `architecture/model/` from which every ArchiMate/C4 diagram is
  generated: files, schema, the `build.py` pipeline, and the vendored IT4IT 3.0
  reference model (`third_party/it4it`, merged in at build time — 301 elements,
  610 relationships, 21 views).
- [Architecture Model: Skeleton](architecture-model-skeleton.md) — section A:
  stakeholders, drivers, assessments, goal/outcome, principles, constraints,
  requirements, capabilities, strategy, value stream, and business processes.
- [Architecture Model: Ecosystem](architecture-model-ecosystem.md) — section B:
  the six subsystems, shared stores, business roles, and external systems
  behind the C4 views.
- [Architecture Model: Artefact Flow](architecture-model-artefact-flow.md) —
  section C: the application functions and artefacts of the input/output
  pipeline, including the policy-to-OSCAL chain.
- [Architecture Views & Diagrams](architecture-diagrams.md) — how those views
  map to ArchiMate viewpoints, the TOGAF Phase A vision-view set, the IT4IT
  reference views, and how to regenerate every `.puml`/`.svg` diagram.
- [IT4IT Reference Model](it4it-model.md) — the vendored `third_party/it4it`
  repo itself: its schema, the 142-element value-stream/capability/
  stakeholder/outcome content, the derived Serving edges, and its own 4
  standard-viewpoint views.
- [OSCAL Compliance Content](oscal-compliance.md) — the vendored OSCAL/FedRAMP
  reference content (`third_party/oscal`, `oscal-content`,
  `fedramp-automation`), the `compliance-trestle` runtime dependency, and how
  ADR-0030 splits the vendoring approach between the two.
- [Data Model](data-model.md) — the platform domain model (ADR, CBS, Semantic
  System Model, Policy), the ArchiMate 3.1 XSD basis, the Neo4j graph shape, and
  the schema-visualiser payload contract.
- [Platform Specification & API](platform-spec.md) — the `001-governance-platform`
  spec (FR-001…FR-023, FR-018 now an NFR; deferred solution decisions, the
  governance API contract)
  and the implemented `002-neo4j-schema-ui` spec and endpoints.
- [Non-Functional Requirements](non-functionals.md) — performance, security,
  reliability, compliance, observability, and quality targets.
- [Visualizer Service](visualizer-service.md) — the one implemented component:
  the FastAPI schema visualiser, its config, request flow, parser, Neo4j
  loader, cache, and the standalone `SchemaManager`.
- [Development & Quickstart](development.md) — prerequisites, setup, running the
  visualiser, tests, the quality-gate toolchain, the SpecKit workflow, and what
  `AGENTS.md` covers.
- [Sample Data](sample-data.md) — the bundled ArchiMate/C4 sample models, the
  Archi CSV exports, and the OSCAL profile-resolution diagrams.
- [Agent Skills & Workflows](agent-workflows.md) — the repo's coding-agent
  skills (`speckit-*`, `commit-message`, `fork-sync`, the diagram/model chain,
  the wiki skills) and the maintenance-agent fleet (`quality-uplift`,
  `coverage-uplift`, `docs-uplift`, `adr-auditor`, `release-runner`, …).

## A note on source quality

The repo began from an accounting-domain SpecKit template; that heritage has
been cleared from `README.md`, `TECHNICAL.md`, `ARCHITECTURE.md` and
`.env.sample`, and the template-era `PROJECT_CONSTITUTION.md` and
`PROJECT_SPECIFICATION.md` have been retired. `.specify/memory/constitution.md`
is the root of the document tree and sets the rule for conflicts: no document automatically wins — stop, find
the root cause, and get a maintainer decision (see
[Governance & Constitution](governance-and-constitution.md)). Where sources
still disagree, the pages here flag it rather than silently picking a side.
