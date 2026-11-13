# ADR-0051: Derived-relationship overlay is a render-time-only, never-persisted view annotation

- **Status:** Accepted
- **Date:** 2026-11-13
- **Sources:** `platform/packages/modelling-specification/src/modelling_specification/puml.py`
  (`_compute_derived_edges`, `_derived_rel_line`, `derived` parameter); `architecture/model/views.yaml`
  (`derived: true`); `.claude/skills/model-archimate/SKILL.md` "Avoiding derived relationships";
  `.claude/skills/model-archimate/scripts/check_derived.py`; commits `61717a2` (feat(modelling-specification):
  overlay derived relationships on views), `a470eeb` (feat(model): add a derived-relationship overlay
  probe view), `37dd065` (fix(modelling-specification): drop sample-azure from vendored sweep)

## Context

ArchiMate 3.2 §3.5's derivation rules let a two-hop relationship chain (`A --r1--> B --r2--> C`)
imply a weaker direct relationship (`A --r3--> C`) without it being modelled explicitly.
`check_derived.py` already flagged the opposite failure mode — an explicit relationship that
only duplicates what a chain already implies — as advisory findings to review by hand. This
cycle added the complementary capability: *seeing* a derived relationship on a view without
adding it to the model. `views.yaml` gained a `derived: true` flag; at render time `puml.py`
walks `pyArchimate.derivation.find_chains()` for two-hop chains where both endpoints are on the
view but the intermediate element is not, and draws each inferred relationship as a dashed
`<<derived>>`-stereotyped arrow, distinct from every modelled-relationship notation (`REL_MACRO`).
This was implemented directly against `check_derived.py`'s existing design note
("If what's wanted is to *see* a derived relationship... give the view `derived: true` ... instead
of adding the explicit edge") rather than against a filed spec or GitHub issue — `check_derived.py`'s
own docstring cites "spec 015-derived-relationships, GitHub issue #140" for the underlying
`pyArchimate.derivation` computation, but GH #140 is actually "Adapt #108's chat/live-view UI into
`reusable-architecture-library/ui`..." — an unrelated issue — and no `015-derived-relationships` spec
exists anywhere in `specs/` or `platform/packages/*/specs/`. The extended-scope reference to GH #146
(`include_dependency=True`) is also wrong: #146 is "Pluggable framework touchpoints (IT4IT first)".

## Decision

The overlay is render-time-only and one-way: it is wired into all three render
paths (`render_diagrams`, `render_single_view`, `render_candidate_view`), draws a dashed
`<<derived>>`-stereotyped arrow carrying the derived relationship type, and is never written back
into `relationships.yaml` or the generated `.archimate`/XML — the model's YAML source stays the
only authoritative record of modelled relationships, exactly as `check_derived.py`'s existing
guidance already described but had not yet implemented. Confirmed as the intended permanent
design, not an interim step toward auto-promoting derived relationships into the model.

## Consequences

- A view's derived overlay can change silently as the underlying chain changes (an intermediate
  element or hop relationship is added/removed), with no diff in `relationships.yaml` to review —
  intentional, per the design note, and accepted as a tradeoff: visibility of implied structure
  is worth more here than a reviewable diff trail for it.
- `check_derived.py`'s own docstring citations (GH #140, GH #146) were wrong (pointing at unrelated
  issues) and have been corrected as part of ratifying this ADR — see
  `.claude/skills/model-archimate/scripts/check_derived.py`.
- Interacts with `check_derived.py`'s existing advisory check (the opposite failure mode): this
  ADR is the cross-reference for both going forward.
