# ADR-0037: Conversational model authoring — package, validation, conventions, overrides, business wiring

- **Status:** Proposed
- **Date:** 2026-10-10
- **Sources:** `specs/004-conversational-model-authoring/plan.md` §Constitution Check
  (Principle X), `specs/004-conversational-model-authoring/research.md` (R1, R2, R6, R7, R12)

## Context

GH #108 adds a conversational agent that proposes ArchiMate model deltas from natural
language, validates them before they touch `architecture/model/`, and renders the result
live. `plan.md`'s Constitution Check (Principle X, Decision Traceability) names five
decisions as load-bearing and requires an ADR before `/speckit-tasks` can run: where the new
code lives, how it shares validation logic with the existing `build.py`/`render_diagrams.py`/
skill `validate.py` without forking it, where Enterprise Convention Rules are configured,
how an architect's override of a flagged objection is recorded, and how the feature wires
into the business layer (ValueStream/Outcome/Process). `plan.md` provisionally cited this as
"ADR-0036"; that number was taken by `develop`'s unrelated element-id-prefix-scheme ADR
during this branch's rebase, so this record files as ADR-0037 instead (see `plan.md`
references, corrected alongside this ADR).

## Decision

1. **Package location**: a new `platform/packages/modelling-specification` package (own
   `pyproject.toml`, `src/`, `tests/`, `specs/`), matching the `controls-compliance-catalog`
   pattern (ADR-0002, ADR-0011). The model already names this package
   `art-pkg-modelling-specification` as subsystem 6's home.
2. **Validation-module incorporation**: `architecture/model/build.py`'s YAML load/merge/
   validate logic and `render_diagrams.py`'s view-render logic move into the new package
   (`model_io.py`, `rendering.py`). Root's `build.py`, `render_diagrams.py` and the
   `model-archimate` skill's `validate.py` become thin wrappers that shell into the
   platform venv's CLI (`poetry run --directory platform python -m modelling_specification.cli
   build|render|validate`). This gives one implementation instead of three while keeping
   ADR-0001's root-never-imports-a-platform-package boundary — root only shells out, as
   before, just applied uniformly to all three entry points.
3. **Enterprise Convention Rule config surface**: a new `architecture/model/conventions.yaml`
   holds organisation-specific authoring rules (interposed-element shapes, naming/altitude
   conventions) as inspectable/editable data, aggregated under `store-frameworks` (same
   pattern as `do-metamodel`). ArchiMate 3.2 metamodel rules stay fixed, sourced from
   pyArchimate; only the enterprise/domain layer is externally configurable.
4. **Override Decision Record mechanism**: when an architect overrides a flagged objection
   (metamodel-pass but convention-fail, or a confirmed non-duplicate), the override is
   auto-drafted as a `Status: Proposed` ADR stub under `docs/adr/` — not appended to
   `store-ledger`. An override is an architecture-governance decision (Principle X), not
   controls/compliance evidence; reusing `store-ledger` would couple architecture decisions
   to evidence-grade retention semantics they don't need. `adr-auditor` already sweeps for
   exactly this kind of undocumented decision.
5. **Business-layer/ValueStream wiring**: a new `vs-intent-to-model` ValueStream and
   `process-conversational-authoring` BusinessProcess, served by the existing
   `coa-executable-governance` course of action and `stk-architecture` stakeholder — the same
   1:1 stream↔outcome, stream↔course-of-action shape as the other four outcome streams. The
   already-built `fn-conversational-authoring` ApplicationFunction realizes this process,
   resolving the business-layer owner this feature's ApplicationFunction previously lacked.

## Consequences

- Root's `pyproject.toml` drops `pyarchimate`/`rapidfuzz` once the three wrapper scripts no
  longer hold their own logic; the new platform package carries them as runtime
  dependencies instead (`research.md` R3).
- CI and the vendored/generated YAML layers (ADR-0029, ADR-0035) keep running the same
  deterministic, non-conversational pipeline — now with one home instead of three — so this
  decision does not introduce a second code path for model build/render/validate.
- Enterprise Convention Rules become a second configuration file architects can edit
  (`conventions.yaml`), alongside `elements.yaml`/`relationships.yaml`; `tasks.md` must
  include its schema and seed content (the `sw-neo4j → art-tech-neo4j-volume → store-akg`
  interposed-element precedent).
- Override stubs add to the ADR log's volume over time; `adr-auditor`'s existing sweep is
  the control against them going stale or unreviewed, not a new mechanism.
- Follow-up: `plan.md`'s two "ADR-0036" references are corrected to "ADR-0037" in the same
  change that files this record, so the plan and the filed ADR agree.

## Alternatives considered

- **Package location** — `src/frictionless_architect/`: rejected, it is the pre-migration
  flat layout (`ARCHITECTURE.md` §8); new subsystem code does not join it.
- **Validation incorporation** — leave `build.py`/`render_diagrams.py` as the
  implementation and have the new package shell out to them: rejected, neither has an
  in-memory-validate-without-write or single-view-render mode today, and bolting those on
  as root CLI flags still leaves the model-loading code split across two homes. A second
  pyArchimate-based implementation inside the package: rejected, duplicates root's logic.
- **Convention Rule surface** — hardcoding the one known interposed-element shape in
  Python: rejected, not configurable, fails the spec's "organisation-specific/editable"
  requirement.
- **Override mechanism** — appending to `store-ledger` as a new `art-override-decision`
  artifact: rejected, conflates architecture-decision traceability with controls evidence.
  A dedicated override-records table/file: rejected, a second traceability mechanism
  alongside the ADR log for no gain.
- **Business wiring** — folding conversational authoring into `vs-governed-delivery`'s
  `vss-baseline` stage: rejected, contradicts the already-settled spec decision (Assumption
  6) that this gets its own ValueStream.
