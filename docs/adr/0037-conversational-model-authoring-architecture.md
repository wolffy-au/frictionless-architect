# ADR-0037: Conversational model authoring — package, validation, conventions, overrides, business wiring

- **Status:** Proposed
- **Date:** 2026-10-10
- **Sources:** `specs/EPIC-003-conversational-model-authoring/plan.md` §Constitution Check
  (Principle X), `specs/EPIC-003-conversational-model-authoring/research.md` (R1, R2, R3, R5,
  R6, R7, R12)

<!-- adr-auditor 2026-10-29: evidence supports Accepted: implemented (platform/packages/modelling-specification,
     architecture/model/conventions.yaml, root build.py/render_diagrams.py shell into its CLI) and cited
     as settled by EPIC-003 plan/tasks and ADR-0039. Held at Proposed until a human attests it (ADR-0012).
     The pyarchimate-in-root Consequences claim was corrected in this ADR (F3, human decision). -->

<!-- 2026-11-01: item 8 (lifting the add-only restriction) added after auditing this feature
     against a real authoring transcript. Items 1-7 were already implemented; item 8 is not.
     Add-only was never itself a decided scope: no clarification session in spec.md raised
     it and no ADR covered it, so there is nothing to supersede -- it is added here rather
     than as a new record because this ADR is still Proposed/unratified and already the one
     filed for this feature's load-bearing choices. Status stays Proposed. -->

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
5. **Metamodel validation library**: pyArchimate is the fixed source of ArchiMate 3.2
   metamodel rules (item 3 above); promoted from a root dev/test-only dependency to a
   runtime dependency of `modelling-specification`, since the running agent needs it at
   request time, not just at build/test time (`research.md` R3).
6. **Duplicate-detection library**: `rapidfuzz.fuzz.token_sort_ratio`, threshold 80, matches
   `name`/`description` for the duplicate-candidate surfacing in item 4 above; `type`
   matches only on exact equality, and a candidate exists only when ≥2 of the 3 fields
   match (`research.md` R5). Also promoted to a runtime dependency alongside pyArchimate
   (`research.md` R3).
7. **Business-layer/ValueStream wiring**: a new `vs-intent-to-model` ValueStream and
   `process-conversational-authoring` BusinessProcess, served by the existing
   `coa-executable-governance` course of action and `stk-architecture` stakeholder — the same
   1:1 stream↔outcome, stream↔course-of-action shape as the other four outcome streams. The
   already-built `fn-conversational-authoring` ApplicationFunction realizes this process,
   resolving the business-layer owner this feature's ApplicationFunction previously lacked.
8. **Lifting the add-only restriction**: the original scope (`spec.md` FR-001, the
   `SYSTEM_PROMPT` in `delta.py`) only ever let a Candidate Delta add new elements,
   relationships and views — never edit, rename or remove an existing one. That limit was
   inherited unexamined from GH #108's "propose a candidate model delta" framing, not a
   deliberated decision. This lifts it: a Candidate Delta may also describe an edit (field
   changes on an existing element/relationship) or a removal of an existing element or
   relationship, carried through the same propose → validate → decide → apply flow, checked
   against the same whole-resulting-model metamodel/referential-integrity gate
   (`merge_candidate`) plus enterprise conventions, and still requiring an explicit `decide`
   action before anything is written (Principle VII, FR-002/004 unchanged). A removal that
   would leave a dangling relationship end, or drop an element/relationship a view still
   references, is a `build_error` finding, same as any other broken reference — never
   silently cascaded.

## Consequences

- Root's `pyproject.toml` drops `rapidfuzz` once the three wrapper scripts no longer hold
  their own logic; the new platform package carries it, and `pyarchimate`, as runtime
  dependencies (`research.md` R3). Root still lists `pyarchimate` because four `.claude/skills`
  scripts (`check_derived.py`, `viewpoints.py`, `model_to_puml.py`, `model_to_c4.py`) import it
  and can be run directly from root's venv. The platform renderer runs the last two under the
  platform venv, so it does not depend on root's copy. Whether to drop it from root by moving
  the other skill scripts behind the platform CLI is left open. Corrected 2026-10-29: this
  record originally said root would drop both.
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
- **Model impact**: items 5 and 6 now cross ADR-0044's "subject of its own ADR decision"
  bar, so `sw-pyarchimate` and `sw-rapidfuzz` (`SystemSoftware`) are added to
  `architecture/model/`, each wired to `fn-conversational-authoring` with a `Serving`
  relationship. Diagrams including that function are regenerated in the same change.
- Item 8: Candidate Delta's JSON shape (`SYSTEM_PROMPT`, `CandidateDelta`) grows further
  optional keys for edits/removals, alongside the existing elements/relationships/views/
  view_membership_edits keys. `append_delta`'s additive-only YAML writer does not cover an
  edit or removal; a second, scoped writer is needed in `model_io.py`, following the
  precedent already set for view-membership edits.
- Item 8: `spec.md` FR-001 and the activity diagram's "(add-only: no edit, rename or
  remove)" label (commit `6b5762c`) become stale the moment this ships and need updating in
  the same change.
- Item 8: removing an element/relationship an existing view's `members:` references, or an
  `include_types` sweep would otherwise pick up, needs the same view-reconciliation
  `model_io.py` already does for membership edits — not a new mechanism, but a new call site.

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
- **Metamodel validation library** — hand-rolling an ArchiMate 3.2 metamodel rules engine:
  rejected, duplicates a maintained, spec-conformant rule set for no gain. A different
  ArchiMate parsing library: not evaluated — pyArchimate already underlies `build.py`/
  `render_diagrams.py`/the skill's `validate.py`, and switching would fork the single-
  implementation goal item 2 sets.
- **Duplicate-detection library** — plain Levenshtein ratio: rejected, more sensitive to
  word-order differences than architect-authored names/descriptions tolerate.
  Embedding-similarity: rejected, a new ML dependency unjustified for matching short
  strings (`research.md` R5).
- **Business wiring** — folding conversational authoring into `vs-governed-delivery`'s
  `vss-baseline` stage: rejected, contradicts the already-settled spec decision (Assumption
  6) that this gets its own ValueStream. A multi-stage `vs-intent-to-model` mirroring the
  other four streams' `vss-*` sub-stages (e.g. propose/validate/apply): considered and
  rejected — those streams' stage boundaries each represent a real multi-day/role hand-off
  (baseline → specify → build → release; escalate → decide → record), while propose /
  validate / apply-or-override happens within one conversational turn performed by a single
  process, with no comparable hand-off to decompose into stages.
- **Lifting add-only** — a new standalone ADR instead of amending this one: considered;
  rejected because no prior ADR ever decided add-only in the first place, so there is
  nothing to supersede, and this ADR is still `Proposed`/unratified and already the one
  record for this feature's load-bearing choices. Leaving add-only in place and only
  shipping the narrower view-membership-edit exception (already implemented): rejected —
  the audited transcript this gap analysis was run against showed real architect workflows
  (splitting a context, correcting a misnamed element) that need a true edit/remove path,
  not just a view-membership carve-out.
