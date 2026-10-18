---
title: Frictionless Architect Wiki
generated: 2026-10-18
generator: GitHub Copilot CLI (Auto)
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
  (per-subsystem UIs), the Poetry monorepo decision and the migration sequence.
- [Architecture Decision Log](decision-log.md) — the full `docs/adr/` decision log
  (MADR index and per-decision summaries).
- [Architecture Model](architecture-model.md) — the canonical graph-loadable
  YAML model in `architecture/model/` from which every ArchiMate/C4 diagram is
  generated: files, schema, the `build.py` pipeline, the generic per-viewpoint
  `views-viewpoints.yaml` layer (GH #105), the generated GitHub roadmap
  layer, and the vendored IT4IT 3.0 reference model (`third_party/it4it`,
  merged in at build time — 489 elements, 1,001 relationships, 64 views total).
- [Architecture Model: Skeleton](architecture-model-skeleton.md) — section A:
  stakeholders, drivers, assessments, one top goal with five sub-goals and ten
  measurable outcomes, principles,
  constraints, requirements, capabilities, strategy, five value streams
  (including the new Intent to Model stream, GH #108), and the business layer
  (functions, processes, business objects).
- [Architecture Model: Ecosystem](architecture-model-ecosystem.md) — section B:
  the six subsystems, shared stores, business roles, and external systems
  behind the C4 views.
- [Architecture Model: Artefact Flow](architecture-model-artefact-flow.md) —
  section C: the application functions and artefacts of the input/output
  pipeline, including the policy-to-OSCAL chain.
- [Architecture Model: Packaging, Migration & Technology](architecture-model-migration.md) —
  sections E and F: the platform's own packaging/migration restructure (Work
  Packages, Plateaus, Gaps) and its first Technology-layer cut.
- [GitHub Roadmap Layer](gh-roadmap-layer.md) — spec 003: GitHub milestones,
  releases and issues imported as ArchiMate Plateaus, Deliverables and Work
  Packages; a release now realizes every Plateau it delivered work for
  (clarified 2026-10-12), not just ones its notes name.
- [Architecture Views & Diagrams: Vision, Business & Viewpoints](architecture-diagrams.md) —
  how the vision and business views map to ArchiMate viewpoints, the TOGAF
  Phase A vision-view set, the 17 new generic per-viewpoint views (GH #105),
  and the `include_types`/`exclude_elements` platform-only scoping mechanism.
- [Architecture Views & Diagrams: Platform, Migration & Rendering](architecture-diagrams-platform.md) —
  the Implementation & Migration and Technology-layer views (sections E/F),
  the vendored IT4IT reference views, and how to regenerate every
  `.puml`/`.svg` diagram. Split out of the page above (2026-10-16) once it
  passed 600 lines.
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
- [Controls & Compliance Catalog](controls-compliance-catalog.md) — the
  `platform/packages/controls-compliance-catalog` package: the first
  extraction into the `platform/` monorepo, its AI-assisted policy/standard →
  OSCAL conversion pipeline (spec `001-oscal-ai-conversion`), data model, API
  surface, and golden-dataset validation.
- [Conversational Model Authoring](modelling-specification.md) — the
  `platform/packages/modelling-specification` package (GH #108,
  [ADR-0037](decision-log.md)): the conversational ArchiMate authoring agent,
  its candidate-delta propose/validate/decide/render pipeline, Enterprise
  Convention Rules, and the ported `build`/`render`/`validate` CLI that root's
  scripts and the `model-archimate` skill now wrap.
- [Portal](portal.md) — the `platform/packages/portal` host package
  ([ADR-0020](decision-log.md) update, GH #120): mounts every package's UI
  under one app, owning only chrome, navigation and the role landing page.
- [LLM Provider Configuration](llm-provider-config.md) — the shared
  `llm-provider-config` package (ADR-0034): global default plus per-component
  provider settings, keychain keys with an env-var fallback, keyless Ollama and
  GitHub Copilot, and the settings router now mounted once by Portal for
  every package.
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
- [Agent Skills & Workflows](agent-workflows.md) — the repo's committed
  coding-agent skills (`commit-message`, `fork-sync`, the diagram/model
  chain, the wiki skills) and the maintenance-agent fleet (`quality-uplift`,
  `coverage-uplift`, `docs-uplift`, `adr-auditor`, `release-runner`, …); the
  generated, git-ignored `speckit-*` scaffolding is covered only where this
  checkout has it on disk.

## A note on source quality

The repo began from an accounting-domain SpecKit template; that heritage has
been cleared from `README.md`, `TECHNICAL.md`, `ARCHITECTURE.md` and
`.env.sample`, and the template-era `PROJECT_CONSTITUTION.md` and
`PROJECT_SPECIFICATION.md` have been retired. `.specify/memory/constitution.md`
is the root of the document tree and sets the rule for conflicts: no document automatically wins — stop, find
the root cause, and get a maintainer decision (see
[Governance & Constitution](governance-and-constitution.md)). Where sources
still disagree, the pages here flag it rather than silently picking a side.
