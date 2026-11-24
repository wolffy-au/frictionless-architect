# ADR-0055: A context-split view may redirect its slice into the owning package's own `specs/diagrams/`

- **Status:** Accepted (2026-11-23)
- **Date:** 2026-11-15
- **Sources:** GH #183; `architecture/model/views-viewpoints.yaml` (`view-business-process-cooperation`'s
  `package_diagrams: true`); `platform/packages/modelling-specification/src/modelling_specification/rendering.py`
  (`_package_diagram_dir`, `_package_diagram_dirs`); commits `c514fff` (feat(model): split process
  cooperation by context), `172a154` (feat(model): prototype a package-local diagram output path),
  `d32ca4d` (refactor(modelling-specification): generalize package diagram redirect)

<!-- adr-auditor 2026-11-15: MISSING decision found during release pre-flight audit. GH #183 shipped a
     real, load-bearing rendering-output-location decision (merged via PR #215) with no ADR. Drafted
     from the commit trail and the implementation; a human must confirm Decision/Consequences below. -->

## Context

ADR-0040 splits an oversized whole-platform viewpoint sweep into one `.puml`/`.svg` per bounded
context, but every split diagram still rendered to
`architecture/model/diagrams/<slug>/<context>.puml`, alongside every other generated diagram,
regardless of which package owned that context. GH #183 observed that a context's own split
slice of `view-business-process-cooperation` would be more discoverable sitting next to the
package it describes (e.g. `controls-compliance-catalog`) than in the central diagrams tree a
reviewer has to know to look in. `rendering.py` first hardcoded one `(view, context)` redirect
as a spike (`172a154`), then generalized it to a declarative `package_diagrams: true` view flag
resolved per context at render time (`d32ca4d`), and extended the orphan-sweep logic so turning
the flag off (or a package losing its `specs/diagrams/` directory) cleans up the now-stale file
in the package too.

## Decision

> DRAFT — confirm: A view that sets `split_by: context` may additionally set
> `package_diagrams: true`. For each context slice, if `platform/packages/<context>/specs/diagrams/`
> already exists on disk, that context's `.puml`/`.svg` renders there instead of under
> `architecture/model/diagrams/<slug>/<context>.puml`; a context whose package has no such
> directory keeps the old central path. Nothing creates the directory automatically — a package
> opts in simply by having it. The directory is reserved for generator-owned output only (never
> hand-authored diagrams, which live under the package's own `specs/<NNN-slug>/diagrams/`
> instead), so the render pipeline's orphan sweep can safely delete anything under it that is no
> longer wanted, including after a view's `package_diagrams: true` is removed or the directory
> disappears.

## Consequences

> DRAFT — confirm:

- A package's own generated, per-context diagram slice becomes discoverable beside that
  package's other specs, without the model-build pipeline knowing about any specific package —
  the redirect is driven entirely by whether the directory already exists, not by a hardcoded
  package list.
- Two possible output locations now exist for the same kind of generated artifact (central
  `architecture/model/diagrams/` vs. per-package `specs/diagrams/`), decided per context by a
  filesystem check rather than declared once in `views-viewpoints.yaml`; a reviewer has to know
  this rule to find a given context's diagram.
- Today only `controls-compliance-catalog` has a `specs/diagrams/` directory, so
  `view-business-process-cooperation` is the only view with `package_diagrams: true` and every
  other context still falls back to the central path — this decision's real impact grows as more
  packages are scaffolded with that directory.
- Revisit if a second, inconsistent redirect convention is proposed, or if the implicit
  "directory existence" trigger proves surprising enough that an explicit per-package allow-list
  in `views-viewpoints.yaml` would read more clearly.

## Alternatives considered

None found in the commit trail beyond the single-pair hardcoded spike that was generalized; a
human should add any genuine alternatives weighed (e.g. keeping every generated diagram under
`architecture/model/diagrams/` and instead linking to it from the package's own docs).
