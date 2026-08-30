# Architecture model

The **canonical** architecture model for the Frictionless Architecture &
Governance Platform, stored as graph-loadable YAML. Every other form — the
ArchiMate XML, the C4 / PlantUML diagrams, and (later) the Neo4j seed — is a
generated projection of these files. See [ADR-0007](../../docs/adr/0007-architecture-model-as-graph-loadable-yaml.md)
and [ADR-0008](../../docs/adr/0008-model-type-is-bare-archimate-name.md).

```text
elements.yaml + relationships.yaml + views.yaml   (canonical, hand-edited)
   └─▶ build.py ─▶ frictionless-architect.xml ─▶ validate.py
                        ├─▶ diagram-c4     ─▶ diagrams/*-c4-*.puml / .svg
                        └─▶ diagram-archimate ─▶ diagrams/*-<view>.puml / .svg
```

## Files

| File | Contents |
|---|---|
| `elements.yaml` | Every element. `type` / `id` / `name` / `desc?` / `props?` |
| `relationships.yaml` | Every relationship. `type` / `source` / `target` / `label?` / `props?` |
| `views.yaml` | Minimal view scoping for `diagram-archimate` (`id` / `name` / `members` and/or `include_types`) |
| `build.py` | YAML → `frictionless-architect.xml` via pyArchimate, then runs `validate.py` |
| `frictionless-architect.xml` | **Generated** (Open Group Exchange Format). Committed, never hand-edited |
| `diagrams/` | **Generated** `.puml` / `.svg` |

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
  `requirement-type`.
- **`label`** on a relationship shows on ArchiMate diagrams and is the default
  C4 edge label; `props.c4-label` overrides it in the C4 projection only.

`build.py` runs `.agents/skills/model-archimate/scripts/validate.py`, which
holds the **whole** model to the ArchiMate 3.2 relationship matrix.

## Model contents

Three layered sections in one model:

| Section | What | Views |
|---|---|---|
| **A. Skeleton** | Motivation (4 drivers, 1 goal, 1 outcome, 3 principles, 4 constraints, 9 functional requirements), Strategy (8 capabilities + the 7-element `Governed Architecture Delivery` value stream), Business (6 processes) — the load-bearing subset ([ADR-0010](../../docs/adr/0010-load-bearing-skeleton-only.md), [ADR-0027](../../docs/adr/0027-capability-value-stream-and-motivation-spine.md)) | `Architecture Skeleton`, `Capability Map & Value Stream`, `Delivery Choreography` |
| **B. Ecosystem** | The platform `Grouping` (`c4=system`), its 6 subsystems, 5 shared stores, 6 roles, 7 external systems; every subsystem `Realization`-linked to a section-A capability ([ADR-0011](../../docs/adr/0011-six-subsystem-decomposition.md)) | `Subsystems & Capabilities`; C4 context + container ([ADR-0009](../../docs/adr/0009-c4-diagrams-generated-from-archimate.md)) |
| **C. Artefact flow** | 15 `ApplicationFunction`s assigned to their subsystem, reading input artefacts and writing output artefacts (25 `DataObject`s) via `Access`; stores `Aggregation`-link the persistent artefacts | `Artefact Flow — Controls & OSCAL` / `— Library & Design` / `— Digital Twin & Governance` / `— Assurance & Specification` |

Every capability is realized by one subsystem and realizes at least one
functional requirement; capability-to-capability `Serving` edges and the value
stream's stage `Serving` edges record the delivery dependency order. Every
motivation element is connected: the four drivers `Influence` the goal, and
drivers, principles and constraints all `Influence` the requirements they
motivate, guide or shape
([ADR-0027](../../docs/adr/0027-capability-value-stream-and-motivation-spine.md)).

## Regenerate

```bash
poetry run python architecture/model/build.py

# C4 context + container
for lvl in context container; do
  poetry run python .agents/skills/diagram-c4/scripts/model_to_c4.py \
    architecture/model/frictionless-architect.xml \
    --system "Frictionless Architecture Platform" --level $lvl \
    --layout $([ $lvl = container ] && echo LEFT_RIGHT || echo WITH_LEGEND) \
    -o architecture/model/diagrams/frictionless-architect-c4-$lvl.puml
done

# every ArchiMate view (name -> diagram slug)
declare -A V=(
  ["Architecture Skeleton"]=skeleton
  ["Capability Map & Value Stream"]=capability-map
  ["Delivery Choreography"]=delivery
  ["Subsystems & Capabilities"]=subsystem-capabilities
  ["Artefact Flow — Controls & OSCAL"]=artefact-oscal
  ["Artefact Flow — Library & Design"]=artefact-library
  ["Artefact Flow — Digital Twin & Governance"]=artefact-twin-governance
  ["Artefact Flow — Assurance & Specification"]=artefact-assurance-spec
)
for name in "${!V[@]}"; do
  poetry run python .agents/skills/diagram-archimate/scripts/model_to_puml.py \
    architecture/model/frictionless-architect.xml --view "$name" \
    -o "architecture/model/diagrams/frictionless-architect-${V[$name]}.puml"
done

# then render: plantuml -tsvg architecture/model/diagrams/*.puml
```

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
