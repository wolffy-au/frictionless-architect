---
name: diagram-archimate
description: Render an ArchiMate view (or a whole model) as a PlantUML diagram using the bundled `<archimate/Archimate>` stdlib. Generates the `.puml` from a validated `.archimate`/`.xml` model, then validates and renders it via the diagram-plantuml workflow. Use when asked for an ArchiMate diagram, an ArchiMate view as PlantUML, or a picture of an ArchiMate model.
---

# diagram-archimate

Projects a validated ArchiMate model into an ArchiMate-notation PlantUML
diagram. The model is the source of truth (`model-archimate` owns it); this
skill only renders.

## Steps

1. **Require a clean model.** Run `model-archimate`'s `validate.py` first.
   Do not render an unvalidated or invalid model — a bad model produces a
   misleading picture.

2. **Generate the `.puml`** with `scripts/model_to_puml.py`:

   ```bash
   poetry run python .agents/skills/diagram-archimate/scripts/model_to_puml.py \
     MODEL.archimate [--view "View Name"] -o OUT.puml
   ```

   - `--view` restricts output to the elements/relationships shown on that
     ArchiMate view (recommended — whole-model diagrams are usually
     unreadable). List views by loading the model and reading `model.views`.
   - Element types map to `<archimate/Archimate>` macros
     (`Application_Component`, `Business_Actor`, `Rel_Serving`, …); the
     mapping table lives in the script and is verified against the bundled
     stdlib. Unmapped types fall back to a plain `rectangle` and print a
     `warning:` — if you see one, check whether the stdlib version gained
     the macro or extend `ELEMENT_MACRO`.

3. **Validate and render via `diagram-plantuml`.** Hand `OUT.puml` to that
   skill's validate→render loop (`plantuml -checkonly`, then `-tsvg` /
   `-tpng`). Don't re-implement rendering here.

4. **Report** the model path, the view rendered, output file(s), any
   unmapped-type warnings, and how validation/rendering was done.

## Nested notation

`Composition`, `Aggregation` and `Assignment` relationships render as
containment — the target is nested inside the source's box and the arrow is
dropped — matching the ArchiMate nested-notation convention (functions inside
their component, stages inside their value stream, artefacts inside their
store). A target keeps its arrow when it has more than one such parent on the
diagram, or when nesting would form a cycle. Edit `NEST_RELS` in the script
to change the set.

Nested `<archimate/Archimate>` element macros (`Application_Component(...) {
... }`) need a recent PlantUML: 1.2026.7 renders them, 1.2024.3 errors on the
opening brace. `post-create.sh` installs the current release at
`/usr/share/plantuml/plantuml.jar`; the VS Code `jebbs.plantuml` extension
ships its own older jar, so `.devcontainer/devcontainer.json` points
`plantuml.jar` at the system one.

## Layout

The generator emits declarations only — no positions. PlantUML auto-lays
out. For a faithful reproduction of a hand-drawn Archi view (exact
coordinates), use pyArchimate's native `view.to_svg()` instead; this skill
is for regenerating diagrams from the model, not pixel-matching Archi.

## Conventions

- One `.puml` per view; name it `<model>-<view>.puml`.
- Keep generated `.puml` next to the model or in the repo's diagram dir,
  matching existing placement.
- Regenerate rather than hand-editing generated `.puml` — edits belong in
  the model.
