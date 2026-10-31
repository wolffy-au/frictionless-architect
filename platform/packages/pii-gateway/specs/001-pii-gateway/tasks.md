---
description: "Task list for platform/packages/pii-gateway (GH #136)"
---

# Tasks: PII Anonymization Gateway

**Input**: Design documents from `platform/packages/pii-gateway/specs/001-pii-gateway/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/scrub.md](contracts/scrub.md),
[quickstart.md](quickstart.md)

**Tests**: Included — GH #136's acceptance criteria and spec.md's User Stories both
require unit and integration tests proving a planted PII string never reaches a stubbed
LLM call (SC-001).

**Scope note (2026-10-31 decision)**: `architecture-governance` does not exist in the
codebase yet (`ARCHITECTURE.md` §4: status **build**) — FR-006's wiring is deferred to
that package's own build-out, the same deferral already used for GH #68's
`conversational-authoring` agent. Tasks below wire only `modelling-specification`
(FR-007); `governance-eval` and `conversational-authoring` are built as registered
contexts with no caller yet.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Phase 1: Setup

- [ ] T001 Create `platform/packages/pii-gateway/` skeleton — `pyproject.toml`,
  `README.md`, `src/pii_gateway/__init__.py`, `src/pii_gateway/py.typed`,
  `tests/unit/`, `tests/integration/` — mirroring
  `platform/packages/llm-provider-config`'s layout (plan.md Project Structure)
- [ ] T002 [P] Add `presidio-analyzer`, `presidio-anonymizer`, `pydantic`, `fastapi`,
  `tomli-w` runtime dependencies to `platform/packages/pii-gateway/pyproject.toml`
  (plan.md Technical Context: Primary Dependencies)
- [ ] T003 [P] Register `pii-gateway` in `platform/pyproject.toml`'s `dependencies` list
  and `[tool.poetry.dependencies]` path entry (ADR-0002), then run `poetry lock` from
  `platform/` to refresh `platform/poetry.lock`
- [ ] T004 [P] Add `pii-gateway = { path = "../pii-gateway", develop = true }` to
  `platform/packages/modelling-specification/pyproject.toml`'s
  `[tool.poetry.dependencies]` and its `dependencies` list

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Implement `ScrubAction`/`Resolution` enums plus the `Match`, `ScrubResult`,
  `PendingConfirmation`, `AuditEntry`, `DetectorCategoryConfiguration` pydantic v2 models
  in `platform/packages/pii-gateway/src/pii_gateway/models.py` per data-model.md's class
  diagram — `ScrubResult.text: str`, `ScrubResult.action: ScrubAction`,
  `ScrubResult.matches: list[Match]`, `ScrubResult.pending_confirmation:
  PendingConfirmation | None`; `Match.category: str`, `Match.location: tuple[int, int]`,
  `Match.confidence: float`; `AuditEntry.timestamp: datetime`, `AuditEntry.context: str`,
  `AuditEntry.categories: list[str]`, `AuditEntry.action: ScrubAction`;
  `DetectorCategoryConfiguration.context: str`,
  `.active_categories: set[str]`, `.failure_mode: ScrubAction`
- [ ] T006 [P] Implement `platform/packages/pii-gateway/src/pii_gateway/detectors.py`:
  load Presidio's `AnalyzerEngine`/`AnonymizerEngine` with the `en_core_web_lg` spaCy
  model once at module import, reused across calls, never per-call (research.md R1); add
  custom `PatternRecognizer`s for ADR-0014's named PHI categories that have no built-in
  Presidio recognizer (research.md R2)
- [ ] T007 [P] Implement `platform/packages/pii-gateway/src/pii_gateway/config.py`: a
  `DetectorCategoryConfiguration` TOML store at
  `~/.config/frictionless-architect/pii-gateway.toml` (override via
  `PII_GATEWAY_CONFIG_PATH`), read via `tomllib` / written via `tomli-w`, validated
  through the T005 model (research.md R4); seed defaults per ADR-0014 —
  `redacted_and_proceeded` for every context except `conversational-authoring`, which
  defaults to `flagged_for_review`; an unrecognized context falls back to the global
  default (spec Edge Cases)
- [ ] T008 [P] Implement `platform/packages/pii-gateway/src/pii_gateway/audit.py`:
  append one JSON line per `scrub()` call to
  `~/.local/state/frictionless-architect/pii-gateway-audit.jsonl` (override via
  `PII_GATEWAY_AUDIT_PATH`), metadata-only per FR-011 — timestamp, context, categories,
  action only, never the matched text or surrounding content (research.md R3)
- [ ] T009 Implement `platform/packages/pii-gateway/src/pii_gateway/scrub.py`'s
  `scrub(text: str, *, context: str) -> ScrubResult`: call T006's detectors, map hits to
  `Match`; catch any detector-engine exception as a synthetic `_ENGINE_ERROR` match with
  `confidence: 0.0` and no text (research.md R6, fail-closed); look up `context`'s
  `DetectorCategoryConfiguration` via T007; apply `redacted_and_proceeded` or
  `flagged_for_review` per that config, building a `PendingConfirmation` only for the
  flagged case; record one `AuditEntry` via T008 per call (depends on T005, T006, T007,
  T008)
- [ ] T010 [P] Export `scrub`, `ScrubResult`, `ScrubAction`, `Resolution` from
  `platform/packages/pii-gateway/src/pii_gateway/__init__.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Automated drafting never sends unscrubbed PII/PHI to an LLM (Priority: P1) 🎯 MVP

**Goal**: `modelling-specification`'s spec-drafting path is scrubbed before any content
reaches the LLM provider; ordinary prose passes through unchanged.

**Independent Test**: Call `scrub()` directly with a planted PII/PHI string and assert it
never appears in the output; call it again with ordinary prose and assert it's unchanged.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [ ] T011 [P] [US1] Unit test: `scrub()` redacts name/email/phone/physical-address PII
  and the call proceeds (FR-002, auto-redact default) in
  `platform/packages/pii-gateway/tests/unit/test_scrub.py`
- [ ] T012 [P] [US1] Unit test: `scrub()` redacts a PHI-specific identifier per
  ADR-0014's language and the call proceeds (FR-003) in
  `platform/packages/pii-gateway/tests/unit/test_scrub.py`
- [ ] T013 [P] [US1] Unit test: `scrub()` on text with no PII/PHI returns it
  byte-for-byte identical (FR-004, SC-002) in
  `platform/packages/pii-gateway/tests/unit/test_scrub.py`
- [ ] T014 [P] [US1] Unit test: a span matching more than one category produces one
  `Match` per category sharing the same `location`, with redaction applied once (spec
  Edge Cases) in `platform/packages/pii-gateway/tests/unit/test_scrub.py`
- [ ] T015 [P] [US1] Unit test: every `scrub()` call appends exactly one metadata-only
  `AuditEntry` with no matched text or surrounding content (FR-011) in
  `platform/packages/pii-gateway/tests/unit/test_audit.py`
- [ ] T016 [P] [US1] Integration test: `modelling_specification.authoring.delta
  .propose_delta()` called with a planted PII string in `request` never includes it in
  the `messages` passed to a stubbed `litellm.completion` (FR-007, SC-001) in
  `platform/packages/modelling-specification/tests/integration/test_pii_scrubbing.py`
- [ ] T017 [P] [US1] Test or code-comment check confirming `fn-ai-markdown-conversion`/
  `fn-policy-quality-feedback` (`controls-compliance-catalog`) still call the LLM
  provider directly with no `pii_gateway` import anywhere in that path (FR-008,
  ADR-0031 exemption) in
  `platform/packages/controls-compliance-catalog/tests/test_pii_gateway_exemption.py`

### Implementation for User Story 1

- [ ] T018 [US1] Wire `pii_gateway.scrub(stripped, context="spec-generator")` into
  `platform/packages/modelling-specification/src/modelling_specification/authoring/
  delta.py`'s `propose_delta()` before building `messages`, using the returned text
  (depends on T009, T016)
- [ ] T019 [US1] Update `delta.py`'s module docstring to cite ADR-0014/FR-007 alongside
  its existing ADR-0034 citation

**Checkpoint**: User Story 1 fully functional and independently testable —
`modelling-specification`'s drafting path is scrubbed end-to-end.

---

## Phase 4: User Story 2 - A detected match asks the architect first when they're already there (Priority: P2)

**Goal**: The `conversational-authoring` context defaults to flag-for-review rather than
auto-redact, with a turn-scoped, never-persisted pending-confirmation lifecycle, ready
for GH #68 to depend on once built.

**Independent Test**: Call `scrub()` with `context="conversational-authoring"` and a
planted PII string; assert a pending confirmation is returned, not a silent redaction.

### Tests for User Story 2 ⚠️

- [ ] T020 [P] [US2] Unit test: `scrub()` with `context="conversational-authoring"` and
  a detected match returns `action=flagged_for_review` with `pending_confirmation` set,
  never an auto-redacted pass-through (FR-005, SC-004) in
  `platform/packages/pii-gateway/tests/unit/test_scrub.py`
- [ ] T021 [P] [US2] Unit test: `PendingConfirmation.resolve()` for each `Resolution`
  value (`redact`/`allow`/`edit`) returns the content to proceed with (User Story 2
  Scenario 2) in `platform/packages/pii-gateway/tests/unit/test_models.py`
- [ ] T022 [P] [US2] Unit test: an unresolved `PendingConfirmation` holds no reference
  outside the `ScrubResult` that returned it, and nothing beyond the one `AuditEntry`
  already recorded is written anywhere — proving turn-abandonment leaves nothing
  persisted (2026-10-31 clarification, User Story 2 Scenario 3) in
  `platform/packages/pii-gateway/tests/unit/test_scrub.py`

### Implementation for User Story 2

- [ ] T023 [US2] Implement `Resolution` enum (`redact`/`allow`/`edit`) and
  `PendingConfirmation.resolve()` in
  `platform/packages/pii-gateway/src/pii_gateway/models.py` (depends on T005)
- [ ] T024 [US2] Confirm T007's seeded config gives `conversational-authoring` a
  `flagged_for_review` default distinct from every other context's
  `redacted_and_proceeded` default (FR-005, ADR-0014) — no caller to wire yet (GH #68
  deferral, spec.md Assumptions)

**Checkpoint**: Both the auto-redact and flag-for-review paths are independently
verified; GH #68 has a tested contract to depend on once built.

---

## Phase 5: User Story 3 - An operator changes detector behavior without touching code (Priority: P3)

**Goal**: An operator can toggle a detector category or change a context's failure-mode
action through a running settings page, taking effect on the next call with no redeploy.

**Independent Test**: Change a setting through the router's API, then call `scrub()`
again and assert the new behavior applies.

### Tests for User Story 3 ⚠️

- [ ] T025 [P] [US3] Contract test: `GET {prefix}/state` returns each registered
  context's `active_categories` and `failure_mode` (contracts/scrub.md settings-router
  contract) in `platform/packages/pii-gateway/tests/unit/test_router.py`
- [ ] T026 [P] [US3] Contract test: `PUT {prefix}/contexts/{context_id}` updates that
  context's config and the next `scrub()` call applies it immediately, with no restart
  (FR-009, SC-003) in `platform/packages/pii-gateway/tests/unit/test_router.py`
- [ ] T027 [P] [US3] Contract test: turning a detector category off for a context stops
  that category's matches from being flagged on the next call (User Story 3 Scenario 1)
  in `platform/packages/pii-gateway/tests/unit/test_router.py`

### Implementation for User Story 3

- [ ] T028 [US3] Implement `create_settings_router(contexts: Sequence[str], prefix: str
  = "/settings/pii-gateway") -> APIRouter` in
  `platform/packages/pii-gateway/src/pii_gateway/router.py`, mirroring
  `llm_provider_config/router.py`'s state/PUT/HTML-page shape (research.md R5,
  contracts/scrub.md)
- [ ] T029 [US3] Mount `pii_gateway`'s settings router in
  `platform/packages/portal/src/portal/app.py` alongside `llm_provider_config`'s,
  registering the `spec-generator`, `governance-eval` and `conversational-authoring`
  contexts (ADR-0020)

**Checkpoint**: Operator can change detector-category/failure-mode behavior through a
running settings page with no code change.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T030 [P] Write `platform/packages/pii-gateway/README.md` documenting the
  `scrub()` contract, the settings surface, and which callers are required to use it
  (FR-010)
- [ ] T031 [P] Confirm `platform/packages/pii-gateway` is picked up by
  `scripts/platform_checks.sh`'s per-package mypy+pytest sweep (90% coverage gate);
  add it explicitly if the sweep doesn't auto-discover new packages
- [ ] T032 Run quickstart.md's three validation scenarios end-to-end against the built
  package
- [ ] T033 Run `bash scripts/pre_merge_checks.sh` and `bash scripts/platform_checks.sh`,
  fixing anything the coverage or lint/type gates surface

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phase 3–5)**: All depend on Foundational completion; US1/US2/US3 are
  independently testable and can proceed in priority order or in parallel.
- **Polish (Phase 6)**: Depends on the user stories being complete.

### Within Each User Story

- Tests are written first and must fail before implementation.
- US1's T018/T019 depend on T009 (Foundational) and T016 (its own test).
- US2's T023 depends on T005 (Foundational); T024 depends on T007 (Foundational).
- US3's T028 depends on T007 (config) and T009 (scrub); T029 depends on T028.

### Parallel Opportunities

- T002–T004 (Setup) run in parallel — different files.
- T006–T008 (Foundational) run in parallel once T005's models exist — different files.
- All test tasks within one user story phase marked [P] run in parallel — different
  test functions, no shared state until implementation lands.
- US1, US2 and US3 can be staffed in parallel once Phase 2 completes, since none
  depends on another's implementation tasks.

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Unit test scrub() PII redaction in tests/unit/test_scrub.py"
Task: "Unit test scrub() PHI redaction in tests/unit/test_scrub.py"
Task: "Unit test scrub() pass-through unchanged in tests/unit/test_scrub.py"
Task: "Unit test multi-category match handling in tests/unit/test_scrub.py"
Task: "Unit test audit entry recorded in tests/unit/test_audit.py"
Task: "Integration test modelling-specification wiring in tests/integration/test_pii_scrubbing.py"
Task: "ADR-0031 exemption check in controls-compliance-catalog/tests/"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run quickstart.md's User Story 1 scenario and
   `platform/packages/modelling-specification`'s integration test independently.
5. This is GH #136's mandatory core (ADR-0014) — ship it before US2/US3.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. User Story 1 → `modelling-specification` scrubbed end-to-end (MVP).
3. User Story 2 → flag-for-review contract ready for GH #68.
4. User Story 3 → operator settings surface live.
5. Polish → README, gate checks, quickstart validation.
