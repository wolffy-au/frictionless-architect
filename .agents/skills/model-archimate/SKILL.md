---
name: model-archimate
description: Author, edit, and validate ArchiMate models (`.archimate` Archi-native or Open Group Exchange `.xml`). Validation runs pyArchimate's metamodel checks — relationship-matrix legality plus referential integrity — and is the conformance gate every ArchiMate/C4 diagram is generated from. Use whenever asked to create or change an ArchiMate model, add a layer, check a model, or before running `diagram-archimate` / `diagram-c4`.
---

# model-archimate

The ArchiMate model is the single source of truth. This skill owns the model
file and its validation; `diagram-archimate` and `diagram-c4` are downstream
projections that must not be generated from an unvalidated model.

## Toolchain

`pyArchimate` is a `dev` dependency (`pyproject.toml`). Run the scripts and
any snippets under the project env — `poetry run python <script> …` (or a
plain `python` if the env is already active).

Readers/writers auto-detect by extension: `.archimate` → Archi native,
`.xml` → Open Group Exchange Format. Match whatever the target repo already
uses (`sample-data/` carries both — `.archimate` from Archi, `.xml` in Open
Group Exchange Format).

## Authoring

Minimal pyArchimate shape:

```python
from pyArchimate import Model
m = Model("my-model")
m.read("model.archimate")                       # or start empty
comp = m.get_or_create_element("ApplicationComponent", "Billing")
svc  = m.get_or_create_element("ApplicationService", "Invoicing")
m.get_or_create_relationship("Realization", comp, svc)
m.write("model.archimate")
```

- Element/relationship `type` is the bare ArchiMate name, no `Relationship`
  suffix (`Composition`, `Serving`, `Assignment`, …).
- Prefer `get_or_create_*` so re-runs are idempotent.
- Keep folder/layer organisation intact when editing an existing file.
- Full language is in scope — business, application, technology, physical,
  motivation, strategy, implementation & migration.

## Viewpoints

A **view** should declare the **viewpoint** it is drawn to. The authority for
which concepts a viewpoint may show is `reference/archi-viewpoints.xml` — a
verbatim copy of Archi's viewpoint file, the closest freely-available
machine-readable form of the ArchiMate 3.2 §14 viewpoint tables. See
`reference/README.md`. `scripts/viewpoints.py` parses it (expanding Archi's
`$…Elements$` collection tokens and applying Archi's allow-list semantics):

```bash
poetry run python .agents/skills/model-archimate/scripts/viewpoints.py list
poetry run python .agents/skills/model-archimate/scripts/viewpoints.py show value_stream
poetry run python .agents/skills/model-archimate/scripts/viewpoints.py \
  check MODEL.xml --view "Value Stream — …" --viewpoint value_stream
```

Semantics (from Archi's `ViewpointManager` / `Viewpoint`):

- An **empty allow-set means unrestricted** — `layered` allows everything, and
  every current viewpoint has an empty *relationship* set, so relationships
  are not filtered in practice (only elements are).
- `Junction` and `Grouping` are always allowed.
- A relationship shows only if both endpoints are allowed — the rule
  `build.py` already applies by drawing only connections with both endpoints
  on the view.

Choosing one — `reference/viewpoints-guidance.yaml` (advisory, ArchiMate 3.2
§14.2) has purpose / abstraction / concerns / stakeholders per slug:

- **Purpose** — *designing* (architects, detailed), *deciding* (managers,
  cross-cutting, often tabular), *informing* (everyone, illustrative).
- **Abstraction** — *detail* (one element / one layer), *coherence* (across
  layers, for architects), *overview* (high level, for enterprise architects
  and CxO).
- **Early / vision stage** favours the overview strategy and motivation
  viewpoints: `stakeholder`, `motivation`, `goal_realization`, `strategy`,
  `capability`, `value_stream`, `outcome_realization`. Leave
  `application_cooperation`, `technology`, `implementation_deployment`,
  `migration` etc. until there is something designed to put in them.

When a repo model tags views (`architecture/model/views.yaml`'s `viewpoint:`
key), the build holds each tagged view to its allow-set and fails on a stray
concept. Use `viewpoint: custom` for a deliberate cross-layer view —
consciously, not as the default.

**The viewpoint tag is a conformance gate, not a projection filter.** The
renderer draws whatever the view's `members` / `include_types` put in scope;
two views with the same membership produce the same diagram whatever their
tags say. Differentiate views by *scoping membership to the concepts that
viewpoint is about* — and if two standard viewpoints only differ by an
element type the model doesn't have yet (e.g. `strategy` vs `value_stream`
differ by `Resource`/`CourseOfAction` vs `Stakeholder`), add those elements or
the views will be identical.

**Tooling limits:** pyArchimate (pinned) cannot round-trip a view-level
property, so the viewpoint is *not* written into the generated `.archimate` /
`.xml` — the model's YAML source stays authoritative. pyArchimate's own
`set_primary_viewpoint` accepts only a non-standard 13-slug list; don't use
it.

## Validation (always run before handing back, and before any diagram)

Run `scripts/validate.py`:

```bash
poetry run python .agents/skills/model-archimate/scripts/validate.py model.archimate
```

It reports and exits non-zero on any of:

| Check | pyArchimate |
|-------|-------------|
| Relationship type illegal between its endpoint types (ArchiMate 3.2 matrix) | `check_valid_relationship` per relationship + `check_invalid_relationships()` |
| Relationship with a dangling source/target | `check_invalid_conn()` |
| View node referencing an unknown element | `check_invalid_nodes()` |

Add `--json` for machine-readable output. **Note:** pyArchimate does *not*
perform derivation-rule inference (implied relationships across intermediate
elements) — see pyArchimate#139. Model explicit relationships; don't rely on
derived ones being synthesised.

Fix every violation and re-validate until clean. If a relationship is
flagged, `get_default_rel_type(src_type, tgt_type)` gives a legal
alternative.

## Report

State the model path, format, element/relationship counts, and the
validation verdict (clean / what was fixed). A downstream diagram skill
should refuse to run until this reports clean.
