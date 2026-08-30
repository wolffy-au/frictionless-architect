# ADR-0007: Architecture model stored as graph-loadable YAML; everything else generated

- **Status:** Accepted
- **Date:** 2026-08-30
- **Sources:** `architecture/model/README.md`; `architecture/model/build.py`; session memory `model-storage`

## Context

The platform's own thesis is architecture-as-graph-native-structured-data. The
model needs one canonical representation from which the ArchiMate model file, the
C4 / PlantUML diagrams, and (later) the Neo4j seed can all be derived without
hand-editing generated artifacts. That representation must also review well in a
pull request — line-oriented, small diffs.

## Decision

The canonical architecture model is **graph-loadable YAML** under
`architecture/model/` (`elements.yaml` + `relationships.yaml` + `views.yaml`),
hand-edited. Every other form is a generated projection:

```text
architecture/model/{elements,relationships,views}.yaml   (canonical, hand-edited)
  ├─▶ build.py ─▶ architecture/model/frictionless-architect.xml ─▶ validate.py
  │                   ├─▶ diagram-c4        ─▶ architecture/model/diagrams/*-c4-*.puml / .svg
  │                   └─▶ diagram-archimate ─▶ architecture/model/diagrams/*-<view>.puml / .svg
  └─▶ Neo4j seed (reads the YAML directly)   [later]
```

- The generated model file is **Open Group Exchange Format `.xml`**, not Archi's
  native `.archimate`. Both are XML, but the exchange format is stable,
  tool-neutral, and produces smaller, more legible diffs — chosen for
  reviewability of a committed-but-generated artifact.
- `name` / `desc` are top-level keys (mirroring `m.add(name=, desc=)`), not `props`.
- `id` is a stable kebab id, hashed to a deterministic UUID in `build.py`, so
  regeneration never churns identifiers (or diagrams).

## Consequences

- `frictionless-architect.xml` and everything under `diagrams/` are committed but
  generated — same status as `.puml` / `.svg`; never hand-edited.
- `build.py` runs `.agents/skills/model-archimate/scripts/validate.py`, which now
  gates the **whole** model against the ArchiMate 3.2 relationship matrix
  (previously only the C4 subset was checked).
- One unified model holds three layered sections — A. Skeleton (ADR-0010),
  B. Ecosystem / 6 subsystems (ADR-0011), C. Artefact flow — projected to the
  C4 context/container views (ADR-0009) and per-view ArchiMate diagrams.
- The old ecosystem builder `sample-data/archimate/build_frictionless_architect.py`
  is retired (ported into section B), and `sample-data/archimate/` is **removed
  entirely**. The generic teaching models keep their own committed `.puml` under
  `sample-data/sample-01/` and `sample-data/sample-02/`.
