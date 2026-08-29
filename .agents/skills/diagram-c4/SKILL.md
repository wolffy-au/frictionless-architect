---
name: diagram-c4
description: Generate a C4 model diagram (Context or Container level) as C4-PlantUML, projected from a validated ArchiMate model via a fixed ArchiMate→C4 mapping. Use when asked for a C4 diagram, a system-context or container diagram, or a C4 view of an architecture that has an ArchiMate model.
---

# diagram-c4

A C4 diagram here is a **projection of the ArchiMate model**, not a
hand-drawn artefact. `model-archimate` owns the model; this skill filters
and relabels it into C4-PlantUML using the mapping in
`references/archimate-to-c4-mapping.md` — read that file before running.

## Prerequisites

- A validated ArchiMate model (`model-archimate` → `validate.py` clean).
- The model must have an **application layer** — `ApplicationComponent`s,
  and a `Grouping` or `c4=system` component that represents the system in
  focus and composes its containers. A pure business/motivation model has
  no C4 projection (the generator will emit an empty boundary — that's the
  correct answer, not a bug).

## Steps

1. **Confirm the model is valid** (refuse otherwise).

2. **Generate** with `scripts/model_to_c4.py`:

   ```bash
   poetry run python .agents/skills/diagram-c4/scripts/model_to_c4.py \
     MODEL.archimate --system "Payments Platform" \
     --level container [--layout TOP_DOWN] -o OUT.puml
   ```

   - `--system` names the `Grouping`/component in focus. Everything it
     composes (transitively) is "inside"; related elements outside become
     `System_Ext` / `Person`.
   - `--level context` = one box for the system + its neighbours;
     `--level container` = the system opened into `Container` /
     `ContainerDb`.
   - Per-element and per-relationship overrides come from ArchiMate
     `properties` (`c4`, `c4-label`, `c4-technology`) — see the mapping doc.
     Prefer fixing the projection by annotating the **model**, not by
     editing generated `.puml`.

3. **Validate and render via `diagram-plantuml`** (`plantuml -checkonly`,
   then `-tsvg`/`-tpng`). The `<C4/*>` includes resolve offline from the
   bundled stdlib.

4. **Report** the model, system in focus, level, output file(s), any
   mapping `warning:`s, and the render method.

## When the projection looks wrong

The mapping is deliberately fixed and conservative. If a diagram is missing
something or mislabelled:

1. First adjust the **model** — add the missing relationship, set a `c4`
   property, fix the composition into the system boundary.
2. Only if the *convention itself* is wrong, change
   `references/archimate-to-c4-mapping.md` and `model_to_c4.py` together,
   in review.

Never hand-tune the generated `.puml` — it will be overwritten on the next
regenerate and the model/diagram drift apart.
