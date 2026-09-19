# ADR-0029: IT4IT vendored as a `third_party/` model, imported at touchpoints

- **Status:** Accepted
- **Date:** 2026-09-13
- **Sources:** conversation record (this ADR is not yet back-filled from any narrative doc)

## Context

The architecture model has grown a substantial IT4IT alignment — capabilities,
value-stream outcomes, and cross-references from the first-party model
(`frictionless-architect-it4it-alignment.*`,
`frictionless-architect-it4it-capability-bridges.*`). IT4IT itself is large,
changes on its own (slower) cadence, and is a reference model rather than
first-party architecture — the same change-profile split ADR-0002 already
draws between first-party packages and vendored forks. Keeping it inline in
`architecture/model/elements.yaml` / `relationships.yaml` makes those files
harder to navigate and conflates "our architecture" with "a standard we
reference."

Model elements and relationships are authored as plain YAML (`id` / `type` /
`name` / ...), not hand-written XML. `build.py` projects that YAML into the
Open Group Exchange XML via `det_id()` — `uuid.uuid5(NS, "|".join(parts))`
against one fixed `NS` constant — so element identity is really just "the
`id:` string, hashed." Two elements only collide if they share the exact same
`id:` string.

## Decision

Vendor IT4IT as its own repo, pulled in as a `third_party/`-style git
submodule managed by `fork-sync` (ADR-0002's mechanism), containing raw
`elements.yaml` / `relationships.yaml` in this repo's existing schema. Every
IT4IT element and relationship `id:` carries the `it4it-` prefix already in
use inline today (e.g. `it4it-capability-plan-portfolio`) — the vendoring
move keeps this convention, it doesn't change it.

`architecture/model/build.py` loads the vendored YAML alongside
`architecture/model/elements.yaml` / `relationships.yaml` — filtered to
touchpoint elements, or the whole file, at the author's discretion — and
merges them into **one** `det_id()` pass through **one** `NS`. There is no
separate build step, no separate `.xml`, and no new ID-reconciliation
machinery: the `it4it-` prefix alone guarantees the merged `id:` strings stay
unique, which is all `det_id()` needs.

## Consequences

- IT4IT updates independently via `fork-sync`, on its own cadence, without
  touching first-party model files.
- The main model's `views.yaml` can reference `it4it-*` element ids directly,
  same as any other element — no adapter layer.
- If IT4IT is ever consumed with its own independently-generated `.xml`
  (its own `build.py` / `NS`) instead of raw YAML, this decision no longer
  holds — merging two separately-hashed UUID spaces is the hard version of
  this problem and would need its own ADR.
- Implemented: `third_party/it4it` (GitHub home:
  `wolffy-au/frictionless-it4it`) holds the full IT4IT
  `elements.yaml`/`relationships.yaml`; there is
  no touchpoint-filtering — `build.py` imports the whole vendored file, and
  only the bridge `Association` edges (props: `source: it4it-alignment`) stay
  first-party, in `relationships.yaml`. It is in
  `.agents/skills/fork-sync/forks.yml`, though as an authored repo (not a fork
  of an existing upstream) `fork-sync` on it is a no-op until it has a real
  upstream.

## Alternatives considered

- **Keep IT4IT inline in the first-party YAML** — simplest today, but the
  file keeps growing and mixes reference-standard content with authored
  architecture, with no independent update cadence.
- **IT4IT as its own first-party monorepo package** — wrong shape per
  ADR-0002: it isn't actively co-developed first-party code, it's a
  low-touch external reference, same as the ArchiMate-parser/OSCAL forks.
- **Separate `build.py` per model, merge generated `.xml`** — rejected: forces
  reconciling two independently-hashed UUID spaces instead of getting
  uniqueness for free from one shared `det_id()`/`NS` pass.
