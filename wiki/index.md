---
title: Frictionless Architect Wiki
generated: 2026-08-30
generator: claude-sonnet-5
---

> This wiki is **generated** by the `wiki-librarian` skill from the sources
> declared in [`sources.yaml`](sources.yaml). Don't edit pages here — change
> `sources.yaml` (add a topic, add a source, adjust a glob) and rebuild.
> Build state is tracked in `.build-log.yaml`.

## Topics

- [Project Overview](project-overview.md) — what Frictionless Architect is, who
  it's for, the platform vision (now six subsystems, formerly eight components),
  and which parts are actually built.
- [Governance & Constitution](governance-and-constitution.md) — the SpecKit
  Constitution (principles I–IX), the Specify→Plan→Implement→Verify workflow,
  and quality gates.
- [Architecture Overview](architecture.md) — the governance-layer-at-root
  principle, current vs. target state, the component decomposition (8 → 6), the
  Poetry monorepo decision, the migration sequence, and the full `docs/adr/`
  decision log.
- [Architecture Model](architecture-model.md) — the canonical graph-loadable
  YAML model in `architecture/model/` from which every ArchiMate/C4 diagram is
  generated: the load-bearing skeleton, the six-subsystem ecosystem, and the
  artefact input/output pipeline.
- [Data Model](data-model.md) — the platform domain model (ADR, CBS, Semantic
  System Model, Policy), the ArchiMate 3.1 XSD basis, the Neo4j graph shape, and
  the schema-visualiser payload contract.
- [Platform Specification & API](platform-spec.md) — the `001-governance-platform`
  spec (FR-001…FR-020, deferred solution decisions, the governance API contract)
  and the implemented `002-neo4j-schema-ui` spec and endpoints.
- [Non-Functional Requirements](non-functionals.md) — performance, security,
  reliability, compliance, observability, and quality targets.
- [Visualizer Service](visualizer-service.md) — the one implemented component:
  the FastAPI schema visualiser, its config, request flow, parser, Neo4j
  loader, cache, and the standalone `SchemaManager`.
- [Development & Quickstart](development.md) — prerequisites, setup, running the
  visualiser, tests, the quality-gate toolchain, and the SpecKit workflow — with
  the stale-doc caveats called out.
- [Sample Data](sample-data.md) — the bundled ArchiMate/C4 sample models, the
  Archi CSV exports, and the OSCAL profile-resolution diagrams.
- [Agent Skills & Workflows](agent-workflows.md) — the repo's coding-agent
  skills (`speckit-*`, `commit-message`, `fork-sync`, the diagram/model chain,
  the wiki skills) and the maintenance-agent fleet (`quality-uplift`,
  `coverage-uplift`, `docs-uplift`, `adr-auditor`, `release-runner`, …).

## A note on source quality

The repo began from an accounting-domain SpecKit template. Most of that
heritage has been cleared from `README.md`, `TECHNICAL.md`, `ARCHITECTURE.md`,
`PROJECT_CONSTITUTION.md`, and `.env.sample` (see
[Project Overview](project-overview.md) §"Heritage cleanup"). `AGENTS.md` and
the `quickstart.md` files are still thin or stale (e.g. `quickstart.md` still
recommends `uv` and `requirements.txt`); where they conflict with
`ARCHITECTURE.md`, `pyproject.toml`, or the code, the pages here flag it and
defer to the latter.
