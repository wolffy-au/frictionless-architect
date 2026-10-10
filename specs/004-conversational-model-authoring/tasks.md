---

description: "Task list for Conversational ArchiMate Model Authoring (GH #108)"
---

# Tasks: Conversational ArchiMate Model Authoring

**Input**: Design documents from `specs/004-conversational-model-authoring/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`,
`quickstart.md`, [ADR-0037](../../docs/adr/0037-conversational-model-authoring-architecture.md)
(filed, Status: Proposed)

**Tests**: Included. `plan.md`'s Constitution Check (Principle II) commits to TDD order —
validation-module unit tests before FastAPI contract tests before behave — and the new
package carries its own 90% coverage gate via `scripts/platform_checks.sh`.

**Organization**: Tasks are grouped by user story (spec.md: US1/US2 both P1, US3 P2) to
enable independent implementation and testing of each.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

New package `platform/packages/modelling-specification/` (own `pyproject.toml`, `src/`,
`tests/`), mirroring `controls-compliance-catalog` (ADR-0002, plan.md Project Structure).
Root paths (`architecture/model/*`, `.claude/skills/model-archimate/scripts/validate.py`)
become thin wrappers per R2.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the new platform package before any logic is ported into it.

- [ ] T001 Create `platform/packages/modelling-specification/` package skeleton: `pyproject.toml`, `src/modelling_specification/__init__.py`, `tests/unit/__init__.py`, `tests/api/__init__.py`, `README.md`, `specs/` (pointer to `specs/004-conversational-model-authoring/`), matching `platform/packages/controls-compliance-catalog`'s layout (plan.md Project Structure)
- [ ] T002 [P] Author `platform/packages/modelling-specification/pyproject.toml`: `fastapi`, `uvicorn`, `pyarchimate` (runtime dependency, R3), `rapidfuzz` (runtime dependency, R3), `pyyaml`, a path dependency on `llm-provider-config`, `litellm` (plan.md Primary Dependencies)
- [ ] T003 [P] Add `platform/packages/modelling-specification` to the `platform/` Poetry workspace and refresh `platform/poetry.lock`
- [ ] T004 [P] Configure `ruff`/`pyright`/`mypy` strict for the new package consistent with `scripts/platform_checks.sh`'s per-package gate

**Checkpoint**: Package scaffold exists, installable via `cd platform && poetry install`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Port the shared validation/render logic (R2), stand up the Enterprise
Convention Rule surface and business-layer wiring ADR-0037 requires, and scaffold the
in-memory session store every user story needs.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Port `architecture/model/build.py`'s YAML load/merge/validate logic into `platform/packages/modelling-specification/src/modelling_specification/model_io.py` (R2) — this becomes the one load path for both the CLI `build` command and the router's in-memory validate-before-write (R9)
- [ ] T006 Port `architecture/model/render_diagrams.py`'s view→PlantUML→SVG logic into `platform/packages/modelling-specification/src/modelling_specification/rendering.py` (R2), adding a single-view render mode (FR-013) that `render_diagrams.py` does not have today
- [ ] T007 [P] Implement `platform/packages/modelling-specification/src/modelling_specification/cli.py` with `build`/`render`/`validate` subcommands dispatching to `model_io.py`/`rendering.py`
- [ ] T008 Rewrite `architecture/model/build.py` as a thin wrapper shelling into `poetry run --directory platform python -m modelling_specification.cli build` (R2) — ADR-0001's root-never-imports-a-platform-package boundary stays intact
- [ ] T009 [P] Rewrite `architecture/model/render_diagrams.py` as a thin wrapper shelling into the platform CLI's `render` subcommand (R2)
- [ ] T010 [P] Rewrite `.claude/skills/model-archimate/scripts/validate.py` as a thin wrapper shelling into the platform CLI's `validate` subcommand (R2, spec.md Assumption 1 — the skill and the running agent share one validation implementation, never two)
- [ ] T011 Create `architecture/model/conventions.yaml` with the Enterprise Convention Rule schema from data-model.md: `id` (string), `kind` (enum `naming|altitude|allowed-subset|interposed-pattern`), `scope` (list of ArchiMate types or `*`), `params` (kind-specific — for `interposed-pattern`: `{source_type, relationship_type, target_type, intermediary_types[]}`), `enabled` (bool, default `true`); seed one `interposed-pattern` rule from the `sw-neo4j → art-tech-neo4j-volume → store-akg` precedent (R6)
- [ ] T012 [P] Unit test: `architecture/model/conventions.yaml` round-trips through `yaml.safe_load`/`safe_dump` with no information loss (data-model.md Invariant 5) in `platform/packages/modelling-specification/tests/unit/test_conventions_schema.py`; a malformed entry fails the load naming the offending `id`, never silently skipped (data-model.md, FR-007's "never silently" posture)
- [ ] T013 [P] [Model] Add `DataObject do-convention-rules` to `architecture/model/elements.yaml` and `Aggregation store-frameworks → do-convention-rules` to `architecture/model/relationships.yaml` (plan.md Model impact, same pattern as `do-metamodel`)
- [ ] T014 [Model] Add `ValueStream vs-intent-to-model`, `Outcome outcome-architect-authored-model`, `BusinessProcess process-conversational-authoring` to `architecture/model/elements.yaml` (plan.md Model impact, R12)
- [ ] T015 [Model] Add the business-layer relationships to `architecture/model/relationships.yaml` (plan.md Model impact): `Serving coa-executable-governance → vs-intent-to-model`, `Association stk-architecture → vs-intent-to-model`, `Realization vs-intent-to-model → outcome-architect-authored-model`, `Serving cap-conversational-governance → vs-intent-to-model`, `Realization process-conversational-authoring → cap-conversational-governance`, `Realization fn-conversational-authoring → process-conversational-authoring`, `Serving process-conversational-authoring → role-ea`, `Serving process-conversational-authoring → role-sa`
- [ ] T016 [Model] Add `Access fn-conversational-authoring → do-convention-rules` (Read) to `architecture/model/relationships.yaml` (plan.md Model impact)
- [ ] T017 Run `poetry run python architecture/model/build.py` and confirm `VALID` with the updated element/relationship counts (quickstart.md step 1 precondition); regenerate `diagrams/strategy/` and `diagrams/business/` views affected by T014–T016
- [ ] T018 Register the `llm-provider-config` component `modelling-specification.conversational-authoring` (R4, quickstart.md Prerequisites)
- [ ] T019 Implement the in-memory `CandidateDelta` session store in `platform/packages/modelling-specification/src/modelling_specification/authoring/state.py`: fields `session_id`, `elements[]`, `relationships[]`, `status` (`proposed → validated/flagged → applied/discarded`, data-model.md lifecycle), keyed by `session_id`, process-memory only, nothing persisted (R8, Clarification 2)
- [ ] T020 Implement `platform/packages/modelling-specification/src/modelling_specification/router.py` FastAPI router skeleton mounted per ADR-0020, with `POST /authoring/sessions` issuing a `session_id` (contracts/api.md)

**Checkpoint**: Foundation ready — `poetry run python architecture/model/build.py` is VALID, the platform package has one shared validation/render implementation, and a session can be created. User story implementation can now begin.

---

## Phase 3: User Story 1 - Propose and see a validated change (Priority: P1) 🎯 MVP

**Goal**: An architect describes a change in natural language; a clean candidate delta
validates and applies, and the affected element renders live without a manual file edit or
render step.

**Independent Test**: Describe a single well-formed change in conversation and confirm a
diagram reflecting it appears without any manual file edit or render command (spec.md).

### Tests for User Story 1 ⚠️

- [ ] T021 [P] [US1] Unit test for `model_io.py`'s in-memory merge + validate: whole-model validation with the delta applied, not delta-in-isolation (FR-002) in `platform/packages/modelling-specification/tests/unit/test_model_io.py`
- [ ] T022 [P] [US1] Contract test `POST /authoring/sessions` and `POST /authoring/sessions/{id}/propose` clean-path response shape (`{"delta_id", "status": "validated", "elements": [...], "relationships": [...]}`) in `platform/packages/modelling-specification/tests/api/test_propose.py`, mocking `litellm.completion` per plan.md Testing (no live network)
- [ ] T023 [P] [US1] Contract test `POST /authoring/sessions/{id}/deltas/{id}/decide` with `{"action": "apply"}` in `platform/packages/modelling-specification/tests/api/test_decide.py`
- [ ] T024 [P] [US1] Behave scenarios for US1 Acceptance Scenarios 1–3 (`acceptance-author`) in `tests/features/conversational_authoring_propose.feature`

### Implementation for User Story 1

- [ ] T025 [US1] Implement NL-to-delta proposal in `platform/packages/modelling-specification/src/modelling_specification/authoring/delta.py`, calling `llm-provider-config`/`litellm` with component `modelling-specification.conversational-authoring` (FR-001, R4)
- [ ] T026 [US1] Implement `platform/packages/modelling-specification/src/modelling_specification/validation/metamodel.py`: builds the in-memory `pyArchimate.Model` via `model_io.py` with the candidate delta merged in, runs the ported relationship-matrix + referential-integrity checks against the whole resulting model (FR-002, R9)
- [ ] T027 [US1] Implement `POST /authoring/sessions/{session_id}/propose` in `router.py`, wiring `delta.py` + `metamodel.py`; return `502` with no `CandidateDelta` created when the LLM call fails or returns an unparseable delta (contracts/api.md)
- [ ] T028 [US1] Implement `decide` action `apply` for a clean (`validated`) delta in `router.py`/`delta.py`: writes the delta via `model_io.py` to `architecture/model/*.yaml`, regenerates via the ported `build.py` logic (FR-001, contracts/api.md)
- [ ] T029 [US1] Implement `GET /authoring/config` and `PUT /authoring/config` for the `auto_render` toggle — a configurable choice, not hardcoded (FR-011)
- [ ] T030 [US1] Implement view resolution in `rendering.py`: given `object_id` or `description`, resolve to a `views.yaml` id; when the description matches more than one plausible view, return the ambiguous set rather than guessing; when none match, signal "no match" rather than guessing (FR-016, data-model.md `ViewRequest`)
- [ ] T031 [US1] Implement `GET /authoring/render` wiring T030's resolution into the response: `200 {"view_id", "svg"}` on an unambiguous resolve (FR-013), `300 {"ambiguous_candidates": [...]}` when T030 found more than one plausible view, `404` when none resolve (contracts/api.md) — independent of the `auto_render` setting
- [ ] T032 [US1] Wire the `decide` `apply` action to call `GET /authoring/render` server-side and inline its result when `auto_render: true`, immediately after apply with no manual step (FR-012)

**Checkpoint**: User Story 1 is fully functional and independently testable — propose → validate → apply → render (auto or on-request).

---

## Phase 4: User Story 2 - Reject invalid, duplicate, or non-idiomatic proposals with an explanation (Priority: P1)

**Goal**: Invalid, duplicate, and non-idiomatic proposals are never applied, auto-corrected,
or dropped silently; each requires an explicit architect decision, and an override is
recorded as a traceable decision.

**Independent Test**: Describe a metamodel-breaking change, a duplicate, and a direct
relationship where the model convention interposes an intermediary; confirm all three
produce an explanation and none is applied without an explicit decision (spec.md).

### Tests for User Story 2 ⚠️

- [ ] T033 [P] [US2] Unit test for `validation/duplicates.py`'s match rule: `rapidfuzz.fuzz.token_sort_ratio ≥ 80` on `name`/`description`, `type` matches only on exact equality, a Duplicate Candidate exists only when `matched_fields[]` has ≥2 entries (R5, data-model.md Invariant 3) in `tests/unit/test_duplicates.py`
- [ ] T034 [P] [US2] Unit test for `validation/patterns.py`: a Pattern Suggestion is raised only when a `conventions.yaml` `interposed-pattern` rule matches the proposed `(source_type, relationship_type, target_type)` shape exactly; no match (Edge Case 4) raises nothing (R6, data-model.md Invariant 4) in `tests/unit/test_patterns.py`
- [ ] T035 [P] [US2] Unit test for `validation/conventions.py`: one case per `kind` — a `naming` rule rejects a non-matching `name`, an `altitude` rule rejects a `banned_terms` hit, an `allowed-subset` rule rejects a type outside `allowed_types` for its `scope`; a disabled (`enabled: false`) rule never fires (FR-003, R13) in `tests/unit/test_conventions.py`
- [ ] T036 [P] [US2] Unit test for `authoring/overrides.py`'s Override Decision Record drafting: fields `id`, `overridden_objection` (`rejection|duplicate|pattern`), `objection_detail`, `rationale` (string or `null`), `applied_delta_summary`, `timestamp` (ISO 8601) (R7, data-model.md Override Decision Record) in `tests/unit/test_overrides.py`
- [ ] T037 [P] [US2] Contract test `decide` actions `reject`, `merge`/`keep-both`/`reject` (duplicate), `accept-pattern`/`keep-direct` (pattern), and `override` in `tests/api/test_decide_objections.py`
- [ ] T038 [P] [US2] Behave scenarios for US2 Acceptance Scenarios 1–4 (`acceptance-author`) in `tests/features/conversational_authoring_reject.feature`

### Implementation for User Story 2

- [ ] T039 [US2] Implement `validation/duplicates.py` per the R5 threshold above (FR-005), flagging regardless of the existing element's Current/Transition/Target state (Edge Case 3)
- [ ] T040 [US2] Implement `validation/patterns.py` loading `conventions.yaml` `interposed-pattern` rules and matching proposed direct relationships against them (FR-008); no established pattern is not itself grounds to flag (Edge Case 4)
- [ ] T041 [US2] Implement `validation/conventions.py` per R13: a `naming`/`altitude`/`allowed-subset` rule in `conventions.yaml` produces a `validation_result.findings[]` entry when violated, in the same shape metamodel findings use (FR-003); a malformed rule entry fails the load naming the offending `id` (data-model.md, FR-007's "never silently" posture)
- [ ] T042 [US2] Implement `validation/fixes.py` per R14: given a metamodel finding, return the nearest legal relationship type for the same endpoint-type pair from pyArchimate's relationship matrix; given a convention finding, return the value implied by the violated rule's own `params` — deterministic, no LLM call (FR-004)
- [ ] T043 [US2] Wire `metamodel.py` + `duplicates.py` + `patterns.py` + `conventions.py` + `fixes.py` into the `propose` endpoint's flagged response: `validation_result.findings[]` (each naming the violated rule and a `proposed_fix` from T042, FR-004), `duplicates[]`, `pattern_suggestions[]` (contracts/api.md flagged shape)
- [ ] T044 [US2] Implement `decide` actions `reject`, duplicate `keep-both`/`merge`/`reject` (on `merge`, change the existing element, not a new one), and pattern `accept-pattern`/`keep-direct` in `router.py`/`delta.py` — never silently applying (FR-006, FR-007, FR-008)
- [ ] T045 [US2] Implement `authoring/overrides.py`: on `decide` action `override`, auto-draft a `Status: Proposed` ADR stub under `docs/adr/` carrying `overridden_objection`, `objection_detail`, `rationale` (optional — recorded as `null` and never blocked or re-prompted when absent, R11), `applied_delta_summary` naming only what was actually written in the same apply (data-model.md Invariant 6), `timestamp` (FR-014, R7); `decide`'s response includes the stub's ADR number as `override_decision_id`
- [ ] T046 [US2] Implement FR-015: a later `propose` request in the same conversation touching an element/relationship already in the pending `CandidateDelta` amends/extends it (`authoring/delta.py` + `state.py`), rather than starting an independent delta against the last-applied state
- [ ] T047 [US2] Implement FR-017: after the architect rejects the agent's proposed fix for an already-rejected change, the next interaction asks the architect to restate/refine rather than auto-retrying a different fix or dropping the request (`authoring/delta.py`)
- [ ] T048 [US2] Implement the `409` error when `decide` targets a `delta_id` not in `flagged`/`validated` status (contracts/api.md)

**Checkpoint**: User Stories 1 AND 2 both work independently — nothing invalid, duplicate, or non-idiomatic reaches `architecture/model/` without an explicit, traceable decision.

---

## Phase 5: User Story 3 - Track and query Current/Transition/Target state (Priority: P2)

**Goal**: Every applied change is classified Current, Transition, or Target, and that
classification is queryable afterward.

**Independent Test**: Apply a change while specifying its state, then ask the agent what
state that change belongs to, independent of any other feature in this spec (spec.md).

### Tests for User Story 3 ⚠️

- [ ] T049 [P] [US3] Unit test for `authoring/state.py`: `state_classification` is required on `apply`, `null` while `proposed` (data-model.md Invariant 2), and queryable by applied element/relationship id in `tests/unit/test_state.py`
- [ ] T050 [P] [US3] Contract test `GET /authoring/sessions/{id}/deltas/{id}/state` in `tests/api/test_state.py`
- [ ] T051 [P] [US3] Behave scenarios for US3 Acceptance Scenarios 1–2 (`acceptance-author`) in `tests/features/conversational_authoring_state.feature`

### Implementation for User Story 3

- [ ] T052 [US3] Implement FR-009 in the `decide` `apply` path: require `state_classification` (`Current|Transition|Target`); when ambiguous, return `422 {"needs": "state_classification"}` rather than guessing (US3 Scenario 2), resubmitted as `{"action": "apply", "state_classification": "..."}`
- [ ] T053 [US3] Implement `GET /authoring/sessions/{session_id}/deltas/{delta_id}/state` (FR-010): a lookup over applied `CandidateDelta.state_classification` values, not a separate store (data-model.md)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Clean-up and the acceptance criteria's project-wide gates (GH #108).

- [ ] T054 [P] Remove `pyarchimate`/`rapidfuzz` from root `pyproject.toml` now that `build.py`/`render_diagrams.py`/`validate.py` are thin wrappers (R2, R3) — root's copies were dev/test-only and are no longer needed once nothing at root imports them directly
- [ ] T055 Confirm `.claude/skills/model-archimate/scripts/validate.py` produces the same findings the router's `validate` call would for the same model (quickstart.md step 8, spec.md Assumption 1)
- [ ] T056 [P] Run `poetry run pytest tests/unit` (root) and `cd platform && poetry run pytest packages/modelling-specification` (90% gate, `scripts/platform_checks.sh`)
- [ ] T057 Run `bash scripts/pre_commit_checks.sh` and `bash scripts/platform_checks.sh` (GH #108 acceptance criteria)
- [ ] T058 Execute `quickstart.md` steps 1–9 end to end against a running `uvicorn modelling_specification.router:app`
- [ ] T059 Confirm `poetry run python architecture/model/build.py` reports `VALID` after all `architecture/model/` changes in this feature (GH #108 acceptance criteria)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user stories — T005/T006 (ported
  logic) and T019/T020 (session store, router skeleton) are load-bearing for every endpoint
  that follows; T011–T016 (conventions.yaml, business-layer model wiring) are load-bearing
  for US2's pattern checks and the feature's traceability, respectively.
- **User Stories (Phase 3–5)**: All depend on Foundational completion.
  - US1 (P1) has no dependency on US2/US3 — it is the propose→validate→apply→render loop
    on a clean delta.
  - US2 (P1) extends the `propose`/`decide` endpoints US1 builds (T027, T028) with
    rejection/duplicate/pattern/override branches — implement after US1's endpoints exist,
    though its own validation modules (T039, T040, T041) can be built in parallel with US1.
  - US3 (P2) extends the `decide` `apply` path (T028) with state classification — implement
    after US1's apply path exists.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (plan.md Constitution Check,
  Principle II).
- Validation modules before the endpoints that call them.
- `propose` before `decide` (a delta must exist before it can be decided).

### Parallel Opportunities

- T002–T004 (Setup) in parallel.
- T007, T009, T010, T012, T013 (Foundational, different files) in parallel.
- All of a story's test tasks marked `[P]` in parallel, before that story's implementation.
- US2's validation-module tests/implementation (T033–T035, T039–T041) can proceed in
  parallel with US1's implementation once Foundational is done, since they touch different
  files (`duplicates.py`, `patterns.py`, `conventions.py` vs. `delta.py`, `metamodel.py`) —
  but US2's `decide`-wiring tasks (T043–T048) depend on US1's `propose`/`decide` endpoints
  (T027, T028) existing first.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for model_io.py in-memory merge+validate in tests/unit/test_model_io.py"
Task: "Contract test POST /authoring/sessions/{id}/propose in tests/api/test_propose.py"
Task: "Contract test POST /authoring/sessions/{id}/deltas/{id}/decide in tests/api/test_decide.py"
Task: "Behave scenarios for US1 in tests/features/conversational_authoring_propose.feature"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (critical — blocks all stories; includes the ADR-0037
   business-layer model wiring and the ported validation/render logic).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run `quickstart.md` step 1 — propose and apply a clean change,
   confirm it renders.

### Incremental Delivery

1. Setup + Foundational → foundation ready, model build still VALID.
2. Add US1 → propose/validate/apply/render loop works end to end (MVP!).
3. Add US2 → nothing invalid/duplicate/non-idiomatic can reach the model without an
   explicit, traceable decision.
4. Add US3 → every applied change carries a queryable Current/Transition/Target
   classification.
5. Polish → gates green, skill parity confirmed, root dependencies trimmed.

## Notes

- `[P]` tasks touch different files with no dependency on an incomplete task.
- `[Model]` tags on T013–T016 mark `architecture/model/` YAML edits specifically, since
  they are shared foundational data rather than package code.
- Every FR-xxx and R-xxx citation above traces to `spec.md` / `research.md` respectively;
  no task invents a requirement not already in those documents (constitution Principle XI).
- Commit after each task or logical group, per this repo's Conventional Commits convention.
