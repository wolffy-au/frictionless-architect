# Architecture Decision Records

This directory is the canonical log of load-bearing decisions for
`frictionless-architect`. Each record is a single Markdown file in
[MADR](https://adr.github.io/madr/)-lite format (`NNNN-short-title.md`).

Before this log existed, decisions were scattered across `ARCHITECTURE.md`,
`TECHNICAL.md`, `PROJECT_SPECIFICATION.md`, the constitution files, and the
feature specs. ADRs 0001–0024 were back-filled from those documents on
2026-08-30; the "Date" field of a back-filled record is the decision's original
date where known, otherwise `unknown (pre-dates this log)`.

## Keeping it honest

The [`adr-auditor`](../../.agents/agents/adr-auditor.md) agent sweeps the
decision-bearing docs (`ARCHITECTURE.md`, `TECHNICAL.md`, the constitution files,
`specs/**`) and recent commits for choices that were made without a record, for
ADRs that have drifted from their sources, and for conflicting records. It opens
a **draft** PR with `Status: Proposed` stubs and status-line edits — a human
still writes the decision and attests it. Run it before a release (`RELEASE.md`
step 5) or any time you suspect the log has fallen behind.

## How to add one

1. Copy [`0000-adr-template.md`](0000-adr-template.md) to the next free number.
2. Fill in Context / Decision / Consequences. Keep it to one screen.
3. Set `Status: Proposed`; flip to `Accepted` once agreed.
4. When a later ADR overturns this one, set `Status: Superseded by ADR-NNNN`
   and add the reverse link to the new record. Never delete a record.
5. Link the record from the table below and, if it changes the wiki, it is
   already covered by `wiki/sources.yaml` (`architecture` topic globs
   `docs/adr/*.md`).

## Index

Status key: **A** = Accepted · **P** = Proposed (captured from the vision docs,
not yet re-ratified in a spec) · **A\*** = Accepted but not yet reflected in the
narrative docs.

- **A** — [0001](0001-root-is-governance-only.md) — Root is governance-only;
  app code lives one level below
- **A** — [0002](0002-poetry-monorepo-forks-as-submodules.md) — One Poetry
  monorepo for first-party code; forks as `third_party/` submodules
- **A** — [0003](0003-poetry-not-uv.md) — Poetry is the package manager, not `uv`
- **A** — [0004](0004-two-tier-spec-numbering.md) — Two-tier spec numbering
  (`EPIC-` at root, `NNN-` per package)
- **A** — [0005](0005-visualiser-api-ui-split-first-extraction.md) — Visualiser
  API/UI split is the first extraction
- **A** — [0006](0006-prototype-neo4j-reference-only.md) — `prototype-neo4j` is
  reference-only, not a merge source
- **A** — [0007](0007-architecture-model-as-graph-loadable-yaml.md) — Model
  stored as graph-loadable YAML; everything else generated
- **A** — [0008](0008-model-type-is-bare-archimate-name.md) — Model `type` =
  bare ArchiMate 3.2 concept name
- **A** — [0009](0009-c4-diagrams-generated-from-archimate.md) — C4 diagrams are
  generated from the ArchiMate model
- **A** — [0010](0010-load-bearing-skeleton-only.md) — Central model is a
  ~30-node load-bearing skeleton only
- **A\*** — [0011](0011-six-subsystem-decomposition.md) — Platform decomposes
  into 6 subsystems (replacing the 8-component grouping)
- **A** — [0012](0012-adr-as-attested-fsm.md) — ADRs are an attested
  finite-state machine
- **A** — [0013](0013-authorization-separate-from-authentication.md) —
  Authorization is a dedicated policy component, separate from authentication
- **A** — [0014](0014-pii-anonymization-gateway.md) — Mandatory PII/PHI
  anonymization before any LLM processing
- **A** — [0015](0015-machine-readability-first.md) — Machine-readability first:
  all artifacts are structured/executable data
- **A** — [0016](0016-every-change-linked-to-an-adr.md) — Every technical change
  links to an ADR ("why over what")
- **P** — [0017](0017-knowledge-graph-on-standard-ontology.md) — Knowledge graph
  built on a standard ontology (Backstage/C4)
- **P** — [0018](0018-postgres-plus-neo4j-data-layer.md) — Data layer: Postgres
  for metadata, Neo4j for the knowledge graph
- **P** — [0019](0019-opa-rego-policy-engine.md) — Policy engine is OPA (Rego);
  bypass raises managed-drift debt
- **P** — [0020](0020-vite-dashboard-in-backstage.md) — Frontend is a Vite
  dashboard, target-embedded in Backstage
- **A** — [0021](0021-schema-visualiser-cytoscape.md) — Schema visualiser uses
  cytoscape.js + coordinated tables
- **A** — [0022](0022-schema-visualiser-lxml-xmlschema.md) — Schema visualiser
  parses ArchiMate with `lxml` + `xmlschema`
- **A** — [0023](0023-visualiser-reuses-neo4j-credentials-with-cache-fallback.md)
  — Visualiser reuses Neo4j read credentials; caches payloads offline
- **A** — [0024](0024-single-user-local-mvp.md) — MVP is single-user and locally
  run (explicit scoping compromise)
- **A** — [0025](0025-conventional-commits-scm-versioning.md) — Conventional
  Commits + commitizen; SCM-derived versions; branch model
- **A** — [0026](0026-fsm-action-endpoints-for-governed-entities.md) —
  Governed-lifecycle entities are FSMs with action-based endpoints
