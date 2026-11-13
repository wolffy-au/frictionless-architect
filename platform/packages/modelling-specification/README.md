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

### What the chat pane shows for each `propose` outcome

`renderProposeResponse` (in `ui.py`'s embedded JS) branches on the response `status`:

- `"message"` -- the LLM's question or remark. The response carries the raw `message`
  and `message_html`, the same text rendered from Markdown and sanitised server-side
  (GH #185); the chat pane shows `message_html`. Apply stays disabled, there is no delta.
- While a `propose` or `propose/resolve-pii` call is in flight, the chat pane shows a
  "Thinking..." message that clears on reply or failure (GH #186).
- `"options"` -- a "what should I do about X" request (ADR-0041): each of the 2-3
  suggested ways forward renders with its rationale, `convention_refs`, the elements/
  relationships it would add and any validation findings/duplicates/pattern suggestions
  it would raise, each behind a "Pick this option" button wired to `propose/select`.
- `"pii_review_required"` (ADR-0014 amendment) -- `scrub()` flagged a PII/PHI match in
  the request before the LLM call was made: each match's category and confidence is
  shown with Redact/Allow/Edit actions wired to `propose/resolve-pii`; the LLM call
  happens only once the architect resolves it.
- anything else (`"validated"`/`"flagged"`) -- the single concrete delta: corrected
  notes, validation findings, duplicate and pattern-suggestion callouts (with
  Reject/Override actions when flagged), and a live preview; "Looks good -- no
  objections" when there is nothing to flag.

### Endpoints

All under `/authoring`; request and response shapes are in
[`contracts/api.md`](../../../specs/EPIC-003-conversational-model-authoring/contracts/api.md).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/sessions` | Start a session, returns `session_id` |
| `POST` | `/sessions/{session_id}/propose` | Turn a request into a delta, a message, or options to pick from |
| `POST` | `/sessions/{session_id}/propose/select` | Pick a suggested option, turning it into the pending delta |
| `POST` | `/sessions/{session_id}/propose/resolve-pii` | Resolve a flagged PII/PHI match; proceed with the LLM call |
| `POST` | `/sessions/{session_id}/deltas/{delta_id}/decide` | Apply, merge, reject, override, or resolve a finding |
| `GET` | `/sessions/{session_id}/deltas/{delta_id}/preview` | SVG preview of a pending delta, nothing written |
| `GET` | `/sessions/{session_id}/deltas/{delta_id}/state` | Current / Transition / Target classification |
| `GET` | `/views` | Renderable views for the picker |
| `GET` | `/render` | Render a view by `object_id` or `description` |
| `GET` / `PUT` | `/config` | Read or set `auto_render` |
| `GET` | `/` | The split-screen UI |

- For a "what should I do about X" request, `propose` returns 2-3 structured options
  instead of a single delta, each with its own rationale and validation result
  (ADR-0041); `propose/select` turns the chosen one into the session's pending
  candidate delta.
- `resolve-pii`'s `resolution` is `redact`, `allow` or `edit` -- `edit`'s replacement
  text is itself re-scrubbed, never assumed clean (ADR-0014 amendment).

A worked end-to-end walkthrough is in
[`quickstart.md`](../../../specs/EPIC-003-conversational-model-authoring/quickstart.md).

`propose`'s request text is scrubbed of PII/PHI by
[`pii-gateway`](../pii-gateway/README.md) (context `"conversational-authoring"`) before
it reaches the LLM provider (ADR-0014).

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

## Using this package against a different model (ADR-0045)

Every path resolves from `model_io.py` at import. With nothing set, a checkout of
this repo uses its own model, and an installed copy reads `architecture/model/`
under the current directory. These env vars override that:

| Variable | Meaning | Default when `FRICTIONLESS_MODEL_DIR` is set |
| --- | --- | --- |
| `FRICTIONLESS_MODEL_DIR` | Directory holding the model YAML and optional `conventions.yaml` | -- |
| `FRICTIONLESS_THIRD_PARTY_DIR` | Directory of vendored models (ADR-0029) | `third_party/` beside the model directory |
| `FRICTIONLESS_MODEL_NAME` | Model name and built file name (`<name>.xml`) | `frictionless-architect` |
| `FRICTIONLESS_C4_SYSTEM` | Element the C4 diagrams are drawn around | none: C4 diagrams are skipped |
| `FRICTIONLESS_ADR_DIR` | Where override ADR stubs are written | `docs/adr/` beside the model directory |

- `FRICTIONLESS_MODEL_DIR` holds `elements.yaml`, `relationships.yaml`, `views.yaml`;
  `diagrams/` is written here.
- `FRICTIONLESS_THIRD_PARTY_DIR`: each subdirectory with an `elements.yaml` is merged in,
  except ones named as a standalone model meant to be pointed at directly instead
  (e.g. `sample-azure`) -- see `model_io.py`'s `_STANDALONE_THIRD_PARTY_MODELS`.
- `FRICTIONLESS_MODEL_NAME`: path separators and a leading dot are rejected.

Each directory variable must name an existing directory, or the package refuses to start.
Paths in generated files and CLI output are relative to the model directory's parent.
The `puml`/`c4` modules print to stdout and never write files themselves; redirect
their output, or let `render` place it.
This repo's vendored models and C4 system never apply to another model.

A different repo can depend on this package through Poetry git dependencies, then run
its own YAML through the `build`/`render`/`validate` CLI below. Nothing from this repo's
model, history or `.claude/skills/` is needed. The three sibling packages must be listed
too: they are `path` dependencies here and are not on PyPI.

```toml
[tool.poetry]
package-mode = false

[tool.poetry.dependencies]
modelling-specification = { git = "<this repo>", subdirectory = "platform/packages/modelling-specification" }
llm-provider-config = { git = "<this repo>", subdirectory = "platform/packages/llm-provider-config" }
digital-twin-knowledge-graph = { git = "<this repo>", subdirectory = "platform/packages/digital-twin-knowledge-graph" }
pii-gateway = { git = "<this repo>", subdirectory = "platform/packages/pii-gateway" }
```

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
