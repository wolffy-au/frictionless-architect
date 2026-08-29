---
title: Frictionless Architect Wiki
generated: 2026-08-29
generator: claude-sonnet-5
---

> This wiki is **generated** by the `wiki-librarian` skill from the sources
> declared in [`sources.yaml`](sources.yaml). Don't edit pages here — change
> `sources.yaml` (add a topic, add a source, adjust a glob) and rebuild.
> Build state is tracked in `.build-log.yaml`.

## Topics

- [Project Overview](project-overview.md) — what Frictionless Architect is, who
  it's for, the eight-component vision, and which parts are actually built.
- [Governance & Constitution](governance-and-constitution.md) — the SpecKit
  Constitution (principles I–IX), the Specify→Plan→Implement→Verify workflow,
  and quality gates.
- [Architecture Overview](architecture.md) — the governance-layer-at-root
  principle, current vs. target state, the component→package map, the Poetry
  monorepo decision, and the migration sequence.
- [Architecture Model Skeleton](architecture-model.md) — the ~30-node
  load-bearing ArchiMate subset in `architecture/model/` used as decomposition
  input: drivers, principles, constraints, six primary capabilities, and the
  end-to-end process chain.
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
  the wiki skills) and paired agents.

## A note on source quality

The repo began from an accounting-domain SpecKit template. Most of that
heritage has been cleared from `README.md`, `TECHNICAL.md`, `ARCHITECTURE.md`,
`PROJECT_CONSTITUTION.md`, and `.env.sample` (see
[Project Overview](project-overview.md) §"Heritage cleanup"). `AGENTS.md` and
the `quickstart.md` files are still thin or stale (e.g. `quickstart.md` still
recommends `uv` and `requirements.txt`); where they conflict with
`ARCHITECTURE.md`, `pyproject.toml`, or the code, the pages here flag it and
defer to the latter.
