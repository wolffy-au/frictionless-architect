---
title: Frictionless Architect Wiki
generated: '2026-10-31'
generator: claude-sonnet-5
---

> This wiki is **generated** by the `wiki-librarian` skill from the sources
> declared in [`sources.yaml`](sources.yaml). Don't edit pages here — change
> `sources.yaml` (add a topic, add a source, adjust a glob) and rebuild.
> Build state is tracked in `.build-log.yaml`.

## Topics

- [Project Overview](project-overview.md) — what Frictionless Architect is, its
  business specification (`specs/EPIC-001-governance-platform`, re-homed
  2026-10-24 under ADR-0004's two-tier scheme, which replaced
  `PROJECT_SPECIFICATION.md`), who it's for, the headline capabilities, and
  which parts are actually built.
- [Governance & Constitution](governance-and-constitution.md) — the single
  SpecKit Constitution at the root of the document tree (principles I–X), the
  document index and conflict-resolution rule, the six-stage workflow, and
  quality gates.
- [Architecture Overview](architecture.md) — the governance-layer-at-root
  principle, current vs. target state, the six-subsystem → package mapping
  (per-subsystem UIs), the Poetry monorepo decision and the migration sequence.
- [Architecture Decision Log](decision-log.md) — the `docs/adr/` decision log for
  ADR-0000–0019 (MADR index, status key and per-decision summaries).
- [Architecture Decision Log: UIs, Visualiser & Model Conventions](decision-log-ui-visualiser-model.md)
  — ADR-0020–0029: per-subsystem UIs, the schema visualiser stack, the
  single-user MVP, commit conventions, governed-entity FSMs, the capability
  value stream, relationship storage and the vendored IT4IT model.
- [Architecture Decision Log: OSCAL, Roadmap, Authoring & Contexts](decision-log-0030-onward.md)
  — ADR-0030 onward: vendored OSCAL content, ArchiMate namespace, value streams,
  shared packages, the GitHub-roadmap layer, conversational authoring, roles,
  bounded contexts and maintenance agents.
- [Architecture Model](architecture-model.md) — the canonical graph-loadable
  YAML model in `architecture/model/` from which every ArchiMate/C4 diagram is
  generated: files, schema, the content sections and the generated GitHub
  roadmap layer. Contexts and viewpoints, and the build pipeline with the
  IT4IT merge, have their own pages below.
- [Architecture Model: Context-Level Viewpoints & Bounded Contexts](architecture-model-contexts.md) —
  the generic per-viewpoint views and the `context:` tag that scopes them:
  generated bounded-context Groupings, split views and the context map
  (GH #105, GH #129, ADR-0040).
- [Architecture Model: Build Pipeline & IT4IT Merge](architecture-model-build-it4it.md) —
  how the YAML model is built into the exchange file, and how the vendored
  IT4IT 3.0 reference model (`third_party/it4it`) is merged in at build time
  (ADR-0029).
- [Architecture Model: Skeleton](architecture-model-skeleton.md) — section A:
  stakeholders, drivers, assessments, one top goal with five sub-goals and ten
  measurable outcomes, principles,
  constraints, requirements, and the business layer (functions, processes,
  business objects). Strategy has its own page below.
- [Architecture Model: Strategy](architecture-model-strategy.md) — section A's
  strategy layer: capabilities, courses of action and the five value streams
  (including the Intent to Model stream, GH #108).
- [Architecture Model: Ecosystem](architecture-model-ecosystem.md) — section B:
  the six subsystems, shared stores, business roles, and external systems
  behind the C4 views.
- [Architecture Model: Artefact Flow](architecture-model-artefact-flow.md) —
  section C: the application functions and artefacts of the input/output
  pipeline, including the policy-to-OSCAL chain.
- [Architecture Model: Packaging, Migration & Technology](architecture-model-migration.md) —
  sections E and F: the platform's own packaging/migration restructure (Work
  Packages, Plateaus, Gaps) and its first Technology-layer cut.
- [GitHub Roadmap Layer](gh-roadmap-layer.md) — `specs/EPIC-002-gh-roadmap-archimate`
  (re-homed 2026-10-24, formerly spec 003): GitHub milestones, releases and
  issues imported as ArchiMate Plateaus, Deliverables and Work Packages; a
  release now realizes every Plateau it delivered work for (clarified
  2026-10-12), not just ones its notes name.
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
  `fedramp-automation` — plain tracked files with `PROVENANCE.md` since
  GH #167, not submodules), the `compliance-trestle` runtime dependency, and
  how ADR-0030 splits the vendoring approach between the two.
- [Data Model](data-model.md) — the platform domain model (ADR, CBS, Semantic
  System Model, Policy), the ArchiMate 3.1 XSD basis, the Neo4j graph shape, and
  the schema-visualiser payload contract.
- [Platform Specification & API](platform-spec.md) — the
  `specs/EPIC-001-governance-platform` spec (re-homed 2026-10-24; FR-001…FR-023,
  FR-018 now an NFR; deferred solution decisions, the governance API contract)
  and the implemented `platform/packages/schema-visualizer-api/specs/001-neo4j-schema-ui`
  spec (formerly root `specs/002-neo4j-schema-ui`) and endpoints.
- [Controls & Compliance Catalog](controls-compliance-catalog.md) — the
  `platform/packages/controls-compliance-catalog` package: the first
  extraction into the `platform/` monorepo, its AI-assisted policy/standard →
  OSCAL conversion pipeline (spec `001-oscal-ai-conversion`), data model, API
  surface, and golden-dataset validation.
- [Conversational Model Authoring](modelling-specification.md) — the
  `platform/packages/modelling-specification` package (GH #108,
  [ADR-0037](decision-log-0030-onward.md); renamed "Conversational Candidate Architecture
  Authoring" and scoped to Enterprise Architects only per
  [ADR-0039](decision-log-0030-onward.md), 2026-10-24): the conversational ArchiMate
  authoring agent, its candidate-delta propose/validate/decide/render
  pipeline, Enterprise Convention Rules, and the ported
  `build`/`render`/`validate` CLI that root's scripts and the
  `model-archimate` skill now wrap.
- [Digital Twin Knowledge Graph](digital-twin-knowledge-graph.md) — the
  `platform/packages/digital-twin-knowledge-graph` package (GH #106): the
  intent-plane knowledge-graph read path over the Neo4j-backed ArchiMate
  model, the ArchiMate exchange-format parser and idempotent schema/ingestion
  manager, consumed as a library by Conversational Model Authoring.
- [Schema Visualizer API](schema-visualizer-api.md) — the
  `platform/packages/schema-visualizer-api` package: today a specs-only
  placeholder homing the re-homed `001-neo4j-schema-ui` spec (formerly root
  `specs/002-neo4j-schema-ui`) ahead of the visualiser API/UI split
  (`ARCHITECTURE.md` §8, step 7).
- [Portal](portal.md) — the `platform/packages/portal` host package
  ([ADR-0020](decision-log-ui-visualiser-model.md) update, GH #120): mounts every package's UI
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
