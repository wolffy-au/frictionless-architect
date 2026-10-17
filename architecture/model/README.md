# Architecture model

The **canonical** architecture model for the Frictionless Architecture &
Governance Platform, stored as graph-loadable YAML. Every other form — the
ArchiMate XML, the C4 / PlantUML diagrams, and (later) the Neo4j seed — is a
generated projection of these files. See [ADR-0007](../../docs/adr/0007-architecture-model-as-graph-loadable-yaml.md)
and [ADR-0008](../../docs/adr/0008-model-type-is-bare-archimate-name.md).

```text
elements.yaml + relationships.yaml + views.yaml   (canonical, hand-edited)
   └─▶ build.py ─▶ frictionless-architect.xml ─▶ validate.py
                        ├─▶ diagram-c4     ─▶ diagrams/c4/*.puml / .svg
                        └─▶ diagram-archimate ─▶ diagrams/<layer>/<view>.puml / .svg
```

`build.py`, `render_diagrams.py` and `validate.py` are thin wrappers: the load / merge /
validate / render logic lives in the `modelling-specification` platform package
(`platform/packages/modelling-specification`, ADR-0037) and is reached through its CLI
(`python -m modelling_specification.cli build|render|validate`).

## Files

| File | Contents |
|---|---|
| `elements.yaml` | Every element. `type` / `id` / `name` / `desc?` / `props?` |
| `relationships.yaml` | Every relationship. `type` / `source` / `target` / `label?` / `props?` |
| `views.yaml` | View scoping (`id` / `name` / `members` and/or `include_types` (optionally narrowed by `exclude_elements`) / `context?` / `viewpoint?` / `diagram` / `no_direction?` / `max_width?`) |
| `views-viewpoints.yaml` | Generic views, one per standard ArchiMate viewpoint, `include_types` only (no `members`). Same schema as `views.yaml`; ids unique across both |
| `conventions.yaml` | Enterprise Convention Rules (for example `interposed-pattern`) that the conversational authoring validation applies to proposed changes (spec 004) |
| `import_gh_roadmap.py` | GitHub milestones / issues / releases → `gh-roadmap/` (see below) |
| `gh-roadmap/` | **Generated** Plateaus, Work Packages, Deliverables, links and per-milestone views. Merged by `build.py`, never hand-edited |
| `build.py` | Wrapper: YAML → `frictionless-architect.xml` via pyArchimate, then validates (logic in `modelling-specification`) |
| `render_diagrams.py` | Wrapper: `frictionless-architect.xml` → every `.puml` / `.svg` (view `diagram:` key + C4) |
| `frictionless-architect.xml` | **Generated** (Open Group Exchange Format). Committed, never hand-edited |
| `diagrams/` | **Generated** `.puml` / `.svg`, one subdirectory per layer: `vision/` (TOGAF ADM Phase A views), `business/`, `application/`, `layered/`, `technology/`, `implementation/`, `migration/` and `c4/`, plus the IT4IT capability-bridges view at the top level |

## Schema

- **`type`** — a bare ArchiMate 3.2 concept name (`Driver`, `Capability`,
  `BusinessProcess`, `ApplicationComponent`, `ApplicationFunction`,
  `DataObject`, `Realization`, `Access`, …). Case-insensitive; `build.py`
  canonicalises against `pyArchimate.ArchiType` and hard-errors on a typo.
- **`id`** — stable kebab id. Hashed to a deterministic UUID, so regeneration
  never churns identifiers (or diagrams). **Never renumber a live id.**
- **`name` / `desc`** — top-level keys, not inside `props`.
- **`context`** — optional top-level key: the element's bounded context. Defaults
  to `platform` for first-party files and to the layer directory's name for
  `third_party/<name>` and `gh-roadmap/`. Written to the XML as a `context`
  property. A view's `context:` (default `[platform]`) limits which contexts its
  `include_types` sweep draws from; `members` are always honoured. `platform` in a view's `context:` covers the whole
  first-party family. First-party contexts: `platform` (shared kernel — motivation,
  strategy, business layer, infrastructure, migration, external systems, shared
  stores) plus the eight platform packages (`controls-compliance-catalog`,
  `reusable-architecture-library`, `digital-twin-knowledge-graph`,
  `architecture-governance`, `conformance-drift-assurance`, `modelling-specification`,
  `schema-visualizer-api`, `llm-provider-config`), which own their subsystem, its
  functions, interface and the artefacts it writes. The `portal` host package is
  modelled in section E.
- **`props`** — string→string. `c4` / `c4-label` for the C4 projection,
  `access_type` (`Read`|`Write`|`ReadWrite`) on `Access` relationships,
  `requirement-type`, and `archimate-analogue` on a BusinessObject whose
  *content* in the managed estate's model is an Implementation & Migration
  concept (Plateau, Gap, …) — kept as a tag so this model's own Plateaus stay
  free to mean states of the platform itself.
- **`label`** on a relationship shows on ArchiMate diagrams and is the default
  C4 edge label; `props.c4-label` overrides it in the C4 projection only.

`build.py` runs `.claude/skills/model-archimate/scripts/validate.py`, which
holds the **whole** model to the ArchiMate 3.2 relationship matrix.

- **`exclude_elements`** on a view (optional) — a list of patterns that drop
  otherwise-selected elements (via `members` or `include_types`) before nodes
  and connections are built. Each entry may give `type` (ArchiMate concept
  name), `id` (a specific element id) and/or `id_prefix`; an element is
  excluded when every key given in an entry matches (omitted keys are
  wildcards). This lets a view use `include_types` for a type that is
  otherwise polluted by a vendored layer sharing the same ArchiMate type —
  e.g. `third_party/it4it` contributes 42 Capability / 35 Outcome / 28
  ValueStream elements, all `it4it-`-prefixed, so `{id_prefix: "it4it-"}`
  keeps those off a first-party view without reverting to an explicit
  `members` allow-list that silently drops any new first-party element of
  that type until someone remembers to add it (GH #117).
- **`viewpoint`** on a view (optional) — a standard ArchiMate viewpoint slug
  from `.claude/skills/model-archimate/reference/archi-viewpoints.xml` (run
  `scripts/viewpoints.py list`). `build.py` holds that view to the
  viewpoint's allowed concepts and fails on a stray one. `custom` = a
  deliberate cross-layer view (not checked); omitting the key also skips the
  check. The tag lives only here — pyArchimate (pinned) cannot round-trip it
  into the generated XML.
- **`no_direction`** on a view (optional) — a list of relationship types
  (e.g. `[Flow]`) to render with a plain, undirected macro on this view only,
  instead of `diagram-archimate`'s default `Up`/`Right` layout hint for that
  type. Use it where the graph for that type isn't actually a one-way
  sequence — e.g. edges running both ways between the same pair of elements
  (a hub-and-spoke or mesh) — which makes the rank hint fight itself and
  produces a tangled layout (dot silently drops half the constraints as
  back-edges) no matter how clean the underlying relationship data is.
- **`max_width`** on a view (optional) — an integer pixel width; the
  diagram is rendered with PlantUML's `scale max <px> width`, so a wider
  layout is scaled down to fit (a narrower one is left at its natural size).
  Use it for long chains that would otherwise need horizontal scrolling.

## Model contents

Layered sections in one model (section D, the IT4IT capability bridges, is relationships only and has no row here):

| Section | What | Views |
|---|---|---|
| **A. Skeleton** | Motivation (stakeholders, drivers, assessments, a goal, outcomes, principles, constraints, functional requirements), Strategy (capabilities, courses of action, resources, and one value stream per outcome with its stages), Business (processes and business objects) — the load-bearing subset ([ADR-0010](../../docs/adr/0010-load-bearing-skeleton-only.md), [ADR-0027](../../docs/adr/0027-capability-value-stream-and-motivation-spine.md), [ADR-0033](../../docs/adr/0033-value-streams-per-outcome.md)) | **Vision (Phase A):** `Stakeholder`, `Motivation`, `Goal Realization`, `Strategy`, `Capability Map`, `Value Stream Hand-offs` + one `Value Stream — <name>` view per stream, `Outcome Realization`, `Requirements Realization`. **Business (Phase B):** `Delivery Choreography` and the per-flow views in `diagrams/business/` |
| **B. Ecosystem** | The platform `Grouping` (`c4=system`), its six subsystems, shared stores, roles and external systems; every subsystem `Realization`-linked to a section-A capability ([ADR-0011](../../docs/adr/0011-six-subsystem-decomposition.md)) | `Subsystems & Capabilities` (Layered); C4 context + container ([ADR-0009](../../docs/adr/0009-c4-diagrams-generated-from-archimate.md)) |
| **C. Artefact flow** | `ApplicationFunction`s assigned to their subsystem, reading input artefacts and writing output artefacts (`DataObject`s) via `Access`; stores `Aggregation`-link the persistent artefacts | `diagrams/application/`: `Artefact Flow — Controls & OSCAL` / `— Library & Design` / `— Digital Twin & Governance` / `— Assurance & Specification`, and the catalog structure view |
| **E. Implementation & Migration** | The platform's own restructure ([ADR-0010](../../docs/adr/0010-load-bearing-skeleton-only.md), GH #65): the `Schema Visualiser API` component and the Digital Twin's `Knowledge Graph Read Path` interface ([ADR-0005](../../docs/adr/0005-visualiser-api-ui-split-first-extraction.md)); the `Portal` composition host and its `Portal UI` interface ([ADR-0020](../../docs/adr/0020-per-subsystem-uis.md), GH #120); one package `Artifact` per platform package (`c4=ignore`) realising its component; `WorkPackage`s, a Baseline `Plateau` and `Gap`s for the `ARCHITECTURE.md` §8 steps; `controls-compliance-catalog` is the first extraction (ADR-0005, GH #60). The generated `gh-roadmap/` layer adds the Plateaus, Work Packages and Deliverables imported from GitHub milestones ([ADR-0035](../../docs/adr/0035-github-roadmap-as-implementation-migration-layer.md)) | `Packaging` (`diagrams/implementation/`); `Migration Sequence`, runtime and work-package-dependency views and one roadmap view per milestone (`diagrams/migration/`) |
| **F. Technology** | Nodes and system software (CI runner, application server, hosted cluster, Neo4j, keyring), technology artifacts (OSCAL workspace, ledger file, Neo4j volume), the OSCAL golden-check process and the server-side role-journey composition function ([ADR-0018](../../docs/adr/0018-postgres-plus-neo4j-data-layer.md), [ADR-0020](../../docs/adr/0020-per-subsystem-uis.md)) | `diagrams/technology/` (CI check, persistence boundary, landscape, usage) |

Every capability is realized by one subsystem and realizes at least one
functional requirement; capability-to-capability `Serving` edges and the
stages' `Serving` edges record the delivery dependency order. Each
value stream realizes one outcome and is `Association`-linked to its value
recipients; stages are `Triggering`-linked in sequence within a stream and
hand off across streams (Build → Prove → Release, Prove → Escalate, Sign Off
→ Release as a `Flow`, Release → Observe, and a `Flow` feedback edge from
`Reconcile & Remediate` back to `Specify the Change`)
([ADR-0033](../../docs/adr/0033-value-streams-per-outcome.md)). Every
motivation element is connected: each stakeholder is `Association`-linked to
the drivers it holds, each driver `Influence`s the assessment that analyses it,
each assessment `Influence`s the outcome that answers it, the outcomes
`Realization`-link to the goal, each requirement realizes exactly one outcome,
and principles and constraints `Influence` the requirements they guide or shape
— no Assessment → Goal, Assessment → Requirement or Requirement → Goal edge,
since each would make an existing edge derived
([ADR-0027](../../docs/adr/0027-capability-value-stream-and-motivation-spine.md)).

## Regenerate

```bash
poetry run python architecture/model/build.py           # YAML -> XML (+ validate)
poetry run python architecture/model/render_diagrams.py # XML -> every .puml / .svg
```

`render_diagrams.py` reads the `diagram:` key on each view in `views.yaml`
(one `.puml`/`.svg` pair per view, TOGAF Phase A views under `diagrams/vision/`)
plus the two C4 diagrams. `--check` fails if any committed diagram is stale
(CI / pre-commit); `--no-svg` skips the PlantUML render.

## GitHub roadmap layer

```bash
poetry run python architecture/model/import_gh_roadmap.py          # gh -> gh-roadmap/
poetry run python architecture/model/import_gh_roadmap.py --check  # exit 1 if it would change
```

Needs an authenticated `gh`. Output is deterministic; a failed or incomplete read writes
nothing. Mapping and ownership rules: [ADR-0035](../../docs/adr/0035-github-roadmap-as-implementation-migration-layer.md).
Run `build.py` and `render_diagrams.py` afterwards.

## Provenance

Section A extracted from `prototype/nodes.yaml` at `prototype-neo4j` (`d0c30b4`);
section B ported from the retired `sample-data/archimate/build_frictionless_architect.py`;
section C authored 2026-08-30. Amended 2026-08-30: option/design authoring
consolidated into the Reusable Architecture Library (Architecture Governance is
now pure decision-making), `cap-control-catalog` / `cap-reusable-architecture`
added so every subsystem realizes a capability, and a Forensic Audit Ledger
(`fn-ledger-record` + `store-ledger`) gives `cap-forensic-ledger` substance.
Amended 2026-08-30 ([ADR-0027](../../docs/adr/0027-capability-value-stream-and-motivation-spine.md)):
capabilities renamed as abilities; `req-authoritative-twin` /
`req-immutable-audit-ledger` added so every capability has a contract;
`req-regulatory-mapping` moved to `cap-control-catalog`; the `Governed
Architecture Delivery` value stream, the driver→goal→outcome spine and the
driver→requirement influences added; `const-model-governance` merged into
`const-model-risk`; `principle-executable-intel` remodelled as an `Outcome`;
subsystem `includes` prose dropped in favour of the section-C functions.
Full history in the ADR log.
