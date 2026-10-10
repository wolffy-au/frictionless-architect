# modelling-specification

Subsystem 6 of the Frictionless Architecture Platform: the conversational ArchiMate
model-authoring agent (GH #108) -- a natural-language request becomes a structured
candidate delta, validated against the ArchiMate metamodel and configurable Enterprise
Convention Rules before anything touches `architecture/model/`.

- Home of the ported `architecture/model/build.py` / `render_diagrams.py` load/merge/
  validate/render logic (`model_io.py`, `rendering.py`) -- root's `build.py`,
  `render_diagrams.py` and the `model-archimate` skill's `validate.py` are now thin
  wrappers shelling into this package's CLI (ADR-0037, R2).
- Modelled as `art-pkg-modelling-specification` in `architecture/model/`, realised by the
  `packages/modelling-specification` Artifact.

## Development

From `platform/` (one shared lock for every package -- ADR-0002):

```bash
poetry install
poetry run pytest packages/modelling-specification/tests
```

`bash scripts/platform_checks.sh` from the repo root runs the full package gate
(pyright, mypy, pytest with 90% coverage) for every package.

## Layout

- `src/modelling_specification/` -- the package.
- `tests/` -- its tests, mirroring `src/`.
- `specs/` -- this package's feature specs (`ARCHITECTURE.md` §6); see
  `specs/004-conversational-model-authoring/` at the repo root for the full spec set.
