---
name: model-archimate
description: Author, edit, and validate ArchiMate models (`.archimate` Archi-native or Open Group Exchange `.xml`). Validation runs pyArchimate's metamodel checks — relationship-matrix legality plus referential integrity — and is the conformance gate every ArchiMate/C4 diagram is generated from. Use whenever asked to create or change an ArchiMate model, add a layer, check a model, or before running `diagram-archimate` / `diagram-c4`.
---

# model-archimate

The ArchiMate model is the single source of truth. This skill owns the model
file and its validation; `diagram-archimate` and `diagram-c4` are downstream
projections that must not be generated from an unvalidated model.

## Toolchain

`pyArchimate` (not a repo dependency — invoke ephemerally):

```bash
uv run --no-project --with 'pyArchimate==1.12.3' --python 3.12 python <script> ...
```

Readers/writers auto-detect by extension: `.archimate` → Archi native,
`.xml` → Open Group Exchange Format. Match whatever the target repo already
uses (the samples under `sample-data/**` are Archi native).

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

## Validation (always run before handing back, and before any diagram)

Run `scripts/validate.py`:

```bash
uv run --no-project --with 'pyArchimate==1.12.3' --python 3.12 \
  python .agents/skills/model-archimate/scripts/validate.py model.archimate
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
