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

## Run the authoring service and UI

Needs an LLM provider configured for the component
`modelling-specification.conversational-authoring` (see
[`llm-provider-config`](../llm-provider-config/README.md); the app also mounts the
`/settings/llm` page).

```bash
./scripts/run-modelling_specification.sh   # from the repo root
```

This runs `modelling_specification.app:app` with `uvicorn` from `platform/` on
`http://127.0.0.1:8001`. Open `/authoring/` for the split-screen UI (chat pane above a
live render pane); the OpenAPI docs are at `/docs`. Standalone for now: the portal
does not mount it yet.

### Endpoints

All under `/authoring`; request and response shapes are in
[`contracts/api.md`](../../../specs/EPIC-003-conversational-model-authoring/contracts/api.md).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/sessions` | Start a session, returns `session_id` |
| `POST` | `/sessions/{session_id}/propose` | Turn a request into a candidate delta; validated, flagged, a clarifying message, or (for a "what should I do about X" request) 2-3 structured options to pick from (ADR-0041) |
| `POST` | `/sessions/{session_id}/propose/select` | Pick one of the most recent `propose` call's suggested options, turning it into the session's pending candidate delta (ADR-0041) |
| `POST` | `/sessions/{session_id}/deltas/{delta_id}/decide` | Apply, merge, reject, accept a pattern, keep direct or override |
| `GET` | `/sessions/{session_id}/deltas/{delta_id}/preview` | SVG preview of a pending delta, nothing written |
| `GET` | `/sessions/{session_id}/deltas/{delta_id}/state` | Current / Transition / Target classification |
| `GET` | `/views` | Renderable views for the picker |
| `GET` | `/render` | Render a view by `object_id` or `description` |
| `GET` / `PUT` | `/config` | Read or set `auto_render` |
| `GET` | `/` | The split-screen UI |

A worked end-to-end walkthrough is in
[`quickstart.md`](../../../specs/EPIC-003-conversational-model-authoring/quickstart.md).

## Command line

From the repo root, the same logic the root wrappers call:

```bash
poetry run --directory platform python -m modelling_specification.cli build
poetry run --directory platform python -m modelling_specification.cli render [--check] [--no-svg]
poetry run --directory platform python -m modelling_specification.cli validate <model.xml> [--json]
```

- `build` -- load the model YAML, write `frictionless-architect.xml` and validate it.
- `render` -- regenerate the diagrams; `--check` fails if committed ones are stale,
  `--no-svg` writes `.puml` only.
- `validate` -- run the metamodel checks on a model file; exits non-zero when it is not clean.

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
  `specs/EPIC-003-conversational-model-authoring/` at the repo root for the full spec set.
