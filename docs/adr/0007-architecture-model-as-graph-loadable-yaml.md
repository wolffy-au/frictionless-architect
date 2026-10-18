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
  │                   ├─▶ diagram-c4        ─▶ architecture/model/diagrams/c4/*.puml / .svg
  │                   └─▶ diagram-archimate ─▶ architecture/model/diagrams/<layer>/<view>.puml / .svg
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
- `build.py` runs `.claude/skills/model-archimate/scripts/validate.py`, which now
  gates the **whole** model against the ArchiMate 3.2 relationship matrix
  (previously only the C4 subset was checked).
- One unified model holds three layered sections — A. Skeleton (ADR-0010),
  B. Ecosystem / 6 subsystems (ADR-0011), C. Artefact flow — projected to the
  C4 context/container views (ADR-0009) and per-view ArchiMate diagrams.
- The old ecosystem builder `sample-data/archimate/build_frictionless_architect.py`
  is retired (ported into section B), and `sample-data/archimate/` is **removed
  entirely**. The generic teaching models keep their own committed `.puml` under
  `sample-data/sample-01/` and `sample-data/sample-02/`.

## Update 2026-10-18: hand-edited YAML has a scale ceiling; past it, Neo4j
## becomes authoritative instead

This decision holds **through the MVP milestone** (`plat-architecture-strategy-mvp-7`),
at the model's current scale (hundreds of elements/relationships, reviewable as
line-oriented diffs). It does not hold indefinitely: hand-edited YAML does not
scale to the tens or hundreds of thousands of elements and relationships a live
enterprise landscape eventually needs — at that point the file stops reviewing
well in a PR, the exact property this ADR chose YAML for in the first place.

Past that ceiling, the authoritative source moves to **Neo4j**, and
`architecture/model/`'s YAML becomes a generated export for human review instead
of the hand-edited source — the inverse of today's direction of generation. No
numeric threshold or concrete trigger condition is fixed yet; this is deliberately
left open, to be set by a follow-up ADR once a real growth trajectory exists to
measure against.

This transition is recorded in the Implementation & Migration layer as
`gap-yaml-to-neo4j-authoritative` (`plat-architecture-strategy-mvp-7 ->
plat-architecture-strategy-future-13`, GH milestone #13), not as a change to the
Decision above — the diagram's `[later]` Neo4j-seed path and this migration are
two different things. The `[later]` seed path stays a *generated projection* of
the YAML (same direction of generation as everything else in this ADR); the
scale-ceiling migration is the point at which that direction reverses. This Gap
is also what makes the existing `cap-digital-twin -> cap-conversational-governance`
Serving relationship ("authoritative model for proposal validation", GH #108) a
true target-state claim rather than a stale edge: it names where the
authoritative-source migration lands, once past the ceiling.
