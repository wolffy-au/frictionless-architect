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

## Files

| File | Contents |
|---|---|
| `elements.yaml` | Every element. `type` / `id` / `name` / `desc?` / `props?` |
| `relationships.yaml` | Every relationship. `type` / `source` / `target` / `label?` / `props?` |
| `views.yaml` | View scoping (`id` / `name` / `members` and/or `include_types` / `viewpoint?` / `diagram` / `no_direction?` / `max_width?`) |
| `build.py` | YAML → `frictionless-architect.xml` via pyArchimate, then runs `validate.py` |
| `render_diagrams.py` | `frictionless-architect.xml` → every `.puml` / `.svg` (view `diagram:` key + C4) |
| `frictionless-architect.xml` | **Generated** (Open Group Exchange Format). Committed, never hand-edited |
| `diagrams/` | **Generated** `.puml` / `.svg`. `diagrams/vision/` holds the TOGAF ADM Phase A views |

## Schema

- **`type`** — a bare ArchiMate 3.2 concept name (`Driver`, `Capability`,
  `BusinessProcess`, `ApplicationComponent`, `ApplicationFunction`,
  `DataObject`, `Realization`, `Access`, …). Case-insensitive; `build.py`
  canonicalises against `pyArchimate.ArchiType` and hard-errors on a typo.
- **`id`** — stable kebab id. Hashed to a deterministic UUID, so regeneration
  never churns identifiers (or diagrams). **Never renumber a live id.**
- **`name` / `desc`** — top-level keys, not inside `props`.
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
| **A. Skeleton** | Motivation (5 stakeholders, 4 assessments, 4 drivers, 1 goal, 4 outcomes, 3 principles, 4 constraints, 9 functional requirements), Strategy (8 capabilities, 3 courses of action, 5 resources + 4 value streams, one per outcome, with 11 stages), Business (6 processes) — the load-bearing subset ([ADR-0010](../../docs/adr/0010-load-bearing-skeleton-only.md), [ADR-0027](../../docs/adr/0027-capability-value-stream-and-motivation-spine.md), [ADR-0033](../../docs/adr/0033-value-streams-per-outcome.md)) | **Vision (Phase A):** `Stakeholder`, `Motivation`, `Goal Realization`, `Strategy`, `Capability Map`, `Value Stream Hand-offs` + one `Value Stream — <name>` view per stream, `Outcome Realization`, `Requirements Realization`. **Business (Phase B):** `Delivery Choreography` |
| **B. Ecosystem** | The platform `Grouping` (`c4=system`), its 6 subsystems, 5 shared stores, 6 roles, 7 external systems; every subsystem `Realization`-linked to a section-A capability ([ADR-0011](../../docs/adr/0011-six-subsystem-decomposition.md)) | `Subsystems & Capabilities` (Layered); C4 context + container ([ADR-0009](../../docs/adr/0009-c4-diagrams-generated-from-archimate.md)) |
| **C. Artefact flow** | 15 `ApplicationFunction`s assigned to their subsystem, reading input artefacts and writing output artefacts (25 `DataObject`s) via `Access`; stores `Aggregation`-link the persistent artefacts | `Artefact Flow — Controls & OSCAL` / `— Library & Design` / `— Digital Twin & Governance` / `— Assurance & Specification` |
| **E. Implementation & Migration** | The platform's own restructure ([ADR-0010](../../docs/adr/0010-load-bearing-skeleton-only.md), GH #65): the `Schema Visualiser API` component and the Digital Twin's `Knowledge Graph Read Path` interface ([ADR-0005](../../docs/adr/0005-visualiser-api-ui-split-first-extraction.md)); 8 package `Artifact`s (`c4=ignore`) realising their components; the 7 `ARCHITECTURE.md` §8 steps as `WorkPackage`s, 3 `Deliverable`s, and Baseline / Transition / Target `Plateau`s with the 2 `Gap`s between them; `controls-compliance-catalog` is the first extraction (ADR-0005, GH #60). No technology layer yet (GH #55) | `Packaging` (`diagrams/implementation/`), `Migration Sequence` (`diagrams/migration/`) |

Every capability is realized by one subsystem and realizes at least one
functional requirement; capability-to-capability `Serving` edges and the
stages' `Serving` edges record the delivery dependency order. Each of the four
value streams realizes one outcome and is `Association`-linked to its value
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
