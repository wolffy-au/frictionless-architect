# ADR-0040: Bounded contexts are generated Groupings, split views, and a derived context map

- **Status:** Accepted
- **Date:** 2026-10-25
- **Sources:** GH #129; `architecture/model/model_io.py`; `architecture/model/views.yaml`,
  `architecture/model/views-viewpoints.yaml`

## Context

Six whole-platform viewpoint sweeps in `views-viewpoints.yaml`
(`view-product`, `view-application-usage`, `view-service-realization`,
`view-implementation-deployment`, `view-implementation-migration-overview`,
`view-application-cooperation`) render every first-party element of a given
set of ArchiMate types across the whole model in one `.puml`/`.svg`. As the
model grew past nine first-party packages, each of those diagrams grew past
the point of being readable (90–160 elements each) — a reviewer could no
longer tell which subsystem owned what, or where one package's
responsibility ended and another's began. The model had no explicit notion
of a package/subsystem's bounded context at all: `context:` tagging,
sweep-splitting, and a boundary-level dependency view all needed to exist
before the oversized views could be fixed without hand-curating six
diagrams' membership by hand (which would re-create the maintenance burden
`include_types` exists to avoid).

## Decision

1. **`context:` is a first-class element property**, defaulting to
   `"platform"` (the shared-kernel fallback) when absent. A vendored layer
   (`it4it`, `gh-roadmap`) gets its own context named after its directory,
   not a first-party package decision. `check_context_coverage` warns about
   a first-party element of a type that should carry an explicit context but
   doesn't, with a recorded-exemption escape hatch for genuinely
   cross-subsystem elements (ADR-0020).

2. **One ArchiMate `Grouping` is generated per real context**
   (`generate_context_groupings`, id `grp-ctx-<context>`), with a generated
   `Aggregation` from the Grouping to each of its members. Not hand-authored
   — the only input is the `context:` tag already on each element, so a
   context's boundary can never drift out of sync with its membership.
   `platform` and vendored layers get no Grouping: they are not bounded
   contexts in the DDD sense, they are the shared kernel and bulk imports
   respectively.

3. **A view may declare `split_by: context` + `include_neighbours: true`**
   to render one `.puml`/`.svg` per context actually present on it instead
   of one monolithic sweep. `include_neighbours` adds any element exactly
   one relationship hop from the view's own membership, regardless of its
   context, so a cross-context edge still has both endpoints on the
   diagram — without that, a context-scoped diagram would silently drop
   every edge leaving its boundary. A neighbour pulled in this way is
   deliberately **not** folded into the view's own `viewpoint:`
   conformance check: it is incidental boundary context, not part of what
   the view's declared viewpoint is about, and several of the split views
   require exactly the type their neighbours add. Applied to five of the
   six oversized views; the sixth, `view-product`, is dropped entirely
   (the model has no `Product`/`Contract`/`Value`/`Material`/`*Service`
   element to give that viewpoint its own shape, so it was a duplicate of
   content already on the usage/service-realization views).

4. **A generated context map** (`generate_context_map_relationships`,
   `view-context-map`) derives one directed `Serving` edge between two
   context Groupings for every ordered pair of real contexts that has at
   least one element-level relationship crossing between them, direction
   following the underlying relationship's own source → target, collapsed
   to one edge per pair regardless of how many element-level edges or
   their ArchiMate type. This is the new top-level overview: a reviewer can
   see which context depends on which, and in which direction, without
   opening any of the per-context split diagrams.

5. **Interfaces as the boundary contract between contexts** (deferred past
   this ADR's initial scope): the eventual shape is Grouping →
   Business/ApplicationInterface (Aggregation), the owning
   Role/Component → that Interface (Composition), Interface →
   BusinessService (Assignment), Interface → the consuming context's
   Role/Process (Serving) — all generated from existing cross-context
   edges, never hand-authored, mirroring how the Groupings and context map
   are generated. Tracked as GH #129 follow-up rather than blocking this
   ADR, since the context map already gives a coarse-grained version of
   the same story (which context depends on which) without it.

## Consequences

- A new context appears as its own Grouping, its own split diagrams, and
  its own context-map node automatically the moment an element is tagged
  with it — no view, Grouping, or relationship needs hand-maintenance when
  a package is added or grows.
- `add_views` now receives `elements + groupings` (not `elements` alone),
  so a view's `include_types` can reach generated Groupings; this is a
  narrow, additive change to what a view can select, not a change to any
  existing view's own membership (no existing view declared
  `include_types: [Grouping]` before this ADR).
- Several per-context split diagrams still exceed the ~60-element target
  the oversized-view problem was trying to reach (the context itself owns
  a lot, or — `conformance-drift-assurance` — is directly connected to
  almost every other context by design, being the compliance
  cross-cutting concern). Read off the real post-build element counts, not
  predicted; a second splitting axis within one context is left for a
  follow-up rather than engineered speculatively here.
- `check_view_coverage` adds a build warning for a first-party element on
  no view at all, independent of the context-splitting work but added
  alongside it (GH #129's own acceptance list groups both under "step 7").

## Alternatives considered

- **Hand-curate six smaller views per subsystem instead of generating a
  split** — rejected: re-creates exactly the maintenance burden
  `include_types` sweeps exist to avoid; a new element would again need a
  human to remember to add it to the right view.
- **Model bounded contexts as a dedicated non-ArchiMate concept (a new
  YAML-only grouping construct) instead of a real `Grouping` element** —
  rejected: `Grouping` is the ArchiMate 3.2 concept that exists for exactly
  this ("a collection of concepts that belong together"), renders in any
  viewpoint without a conformance exception (`ALWAYS_ALLOWED_ELEMENTS`),
  and needs no new tooling to view, export, or validate.
- **Fold a neighbour pulled in by `include_neighbours` into the
  viewpoint-conformance check, same as the view's own members** — rejected
  after it broke the build: several of the six named views declare a
  strict standard viewpoint, and a neighbour's type is often outside that
  viewpoint's allow-set by construction (that's exactly why it's a
  neighbour and not a member). A neighbour is boundary context, not core
  content.
