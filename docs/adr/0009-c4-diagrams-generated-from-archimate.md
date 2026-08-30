# ADR-0009: C4 context/container diagrams are generated from the ArchiMate model

- **Status:** Accepted
- **Date:** 2026-08-29
- **Sources:** `PROJECT_SPECIFICATION.md` §"C4 Context Diagram";
  `architecture/model/README.md`; session memory `ecosystem-c4`; `.agents/skills/diagram-c4/`

## Context

`PROJECT_SPECIFICATION.md` previously carried a hand-written C4-PlantUML context
block. Hand-drawn diagrams drift from the model they describe. `TECHNICAL.md`
mandates PlantUML / C4-PlantUML for UML and C4.

## Decision

The C4 **Context** and **Container** views are **generated from the ArchiMate
model** via the `diagram-c4` skill (`model_to_c4.py architecture/model/frictionless-architect.xml
--system … --level context|container`), not hand-drawn. The model itself is built
from the canonical YAML by `architecture/model/build.py` (ADR-0007). The
hand-written block in `PROJECT_SPECIFICATION.md` is replaced with a pointer to the
generated
`architecture/model/diagrams/frictionless-architect-c4-{context,container}.puml` / `.svg`.

## Consequences

- Generated `.puml` files carry a `' GENERATED …` header and are committed.
- The context generator merges parallel edges onto the one system box (distinct
  sub-labels stacked one per line) — a `diagram-c4` convention.
- Fixed ArchiMate→C4 mapping lives in
  `.agents/skills/diagram-c4/references/archimate-to-c4-mapping.md`.
