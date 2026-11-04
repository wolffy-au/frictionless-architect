# ADR-0045: The tool is multi-tenant — packages are consumed as dependencies, never assumed co-located with a model

- **Status:** Accepted
- **Date:** 2026-11-04
- **Sources:** none (forward-looking decision, not a back-fill)

## Context

The platform is going to be reused outside this repo, against a completely different
ArchiMate model belonging to an unrelated organisation, by installing the relevant
platform packages (`modelling-specification` at minimum) as a dependency in a separate
repo that holds only that org's own `elements.yaml`/`relationships.yaml`/`views.yaml`.

That use case was blocked by hardcoded assumptions that this exact checkout is the only
place the tool ever runs:

1. `model_io.py`'s `HERE`/`OUT`/`THIRD_PARTY` were derived from
   `Path(__file__).resolve().parents[5]`, hardcoding the model directory to
   `architecture/model/` inside this repo.
2. `model_io.py`'s build-time viewpoint-conformance check imported
   `.claude/skills/model-archimate/scripts/viewpoints.py` via a `sys.path` hack, and that
   script in turn read two reference data files from `.claude/skills/model-archimate/
   reference/` — neither of which ships with the `modelling-specification` package.
3. `rendering.py` shelled out, per diagram, to `.claude/skills/diagram-archimate/scripts/
   model_to_puml.py` and `.claude/skills/diagram-c4/scripts/model_to_c4.py` by repo-relative
   file path — again, not part of the installable package.
4. Paths and names specific to this repo's own model were fixed in code: the `it4it`
   vendored directory, the `frictionless-architect` model name and the C4 system in focus,
   `docs/adr/` for override stubs, and `rendering.py`'s own `architecture/model` path and
   its model path relative to the repo root.

None of this is specific to *this org's* model data; it is generic ArchiMate/C4
projection and viewpoint-checking logic that happened to live in Claude Code skill
scripts rather than in the Python package those skills already delegate their primary
logic to (ADR-0037's thin-wrapper pattern).

## Decision

1. The model root is env-configured: `FRICTIONLESS_MODEL_DIR`, read once by `model_io.py`,
   which every other module derives its paths from. Unset, a checkout of this repo uses its
   own `architecture/model/` and an installed copy uses `architecture/model/` under the
   current directory. When set, the project root is the model directory's parent.
   `FRICTIONLESS_THIRD_PARTY_DIR`, `FRICTIONLESS_MODEL_NAME` and `FRICTIONLESS_ADR_DIR`
   override the rest; their defaults follow the project root, so setting the model
   directory alone cannot merge this repo's vendored models into another model.
   Vendored models are discovered as `third_party/*/elements.yaml`, and the
   `first_party_only` convention rules exclude their directory-name id prefixes.
   C4 diagrams are skipped for another model unless `FRICTIONLESS_C4_SYSTEM` names its
   system. Unset, all of this resolves to this repo's existing behaviour.
2. Viewpoint conformance checking (`viewpoints.py` + its two reference data files) and
   ArchiMate/C4 PlantUML projection (`model_to_puml.py`/`model_to_c4.py`, renamed
   `puml.py`/`c4.py`) move from `.claude/skills/*/scripts` into the `modelling_specification`
   package itself, as real importable modules and bundled package data. The package is
   now self-contained: installing it (e.g. as a Poetry git dependency with
   `subdirectory = "platform/packages/modelling-specification"`) is sufficient, with no
   dependency on this repo's `.claude/skills/` tree.
3. `rendering.py` locates the puml/c4 generators via Python's module system
   (`python -m modelling_specification.puml`/`.c4`), not a repo-relative file path, so the
   same subprocess + thread-pool concurrency it already relies on for render speed works
   unchanged whether the package is this checkout's own `platform/` or an installed
   dependency elsewhere.
4. The three original `.claude/skills/*/scripts` files (`viewpoints.py`, `model_to_puml.py`,
   `model_to_c4.py`) become thin wrappers shelling into the platform CLI, mirroring the
   pattern `validate.py` already used — this repo's own documented skill workflows are
   unaffected.

**Model impact:** none — this is a tooling/packaging change; no element, relationship, or
view in `architecture/model/` changes.

## Consequences

- A separate repo for a different model can depend on `modelling-specification` (and
  whichever other platform packages it needs) directly from this repo's git URL, holding
  only its own model YAML and its own `.env` (Neo4j, LLM provider config, etc.) — no fork
  of this codebase or its git history.
- `check_derived.py` (a `model-archimate` skill script) is deliberately **not** moved: it
  has no caller in the automated build/render pipeline (confirmed by inspection) and is a
  manual advisory tool; its overlap with `model_io.py`'s `_check_derived_goal_edges` is
  already acknowledged as deliberate in that function's own docstring.
- Creating the actual new work-org repo is out of scope of this decision — it is a
  separate repo belonging to an unrelated organisation.
- Future platform packages that grow a similar "real logic lives in a Claude Code skill
  script" split should be audited against this same test before being declared reusable.

## Alternatives considered

- **Split `architecture/model/` into its own repo** — rejected. The model and the tool
  evolve together constantly (schema changes, new element types, convention rules often
  land in the same PR as model edits); a repo split turns that into cross-repo version
  bumps and breaks atomic review/CI for no benefit, since this repo's own model and tool
  are not actually independent of each other.
- **Have each new consuming repo vendor its own copy of the three `.claude/skills/*`
  script directories** — rejected. Works immediately but duplicates ~1,300 lines of logic
  that will silently drift from this repo's copy over time, defeating the point of
  "install as a dependency."
