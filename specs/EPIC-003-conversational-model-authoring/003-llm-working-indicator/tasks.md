---

description: "Task list for the LLM working indicator (GH #186)"
---

# Tasks: LLM Working Indicator for Conversational Authoring

**Input**: Design documents from `specs/EPIC-003-conversational-model-authoring/003-llm-working-indicator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (no `contracts/` — no API changes)

**Tests**: Included — this package's existing convention (Constitution Principle II) writes tests alongside the change; `pytest`/`TestClient` for static markup, `behave`/Playwright for the live in-browser interaction.

**Organization**: Grouped by the two P1 user stories in spec.md (US1 = `propose` path, US2 = `propose/resolve-pii` path), after one Foundational phase both stories share.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Maps to spec.md's US1/US2
- File paths are exact and relative to the repository root

## Phase 1: Setup

- [X] T001 Confirm no new runtime dependency is needed — `ui.py`'s existing `_PAGE_TEMPLATE`/`_PAGE` module-level-string pattern (no Jinja2, no static-asset pipeline, no JS framework) is reused as-is; `platform/packages/modelling-specification/pyproject.toml` is unchanged.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The indicator mechanism both user stories wire into, and the test seam both stories' behave scenarios need.

**⚠️ CRITICAL**: Both user story phases below depend on this phase.

- [X] T002 [P] Add a `.msg.thinking` CSS rule to the `<style>` block in `platform/packages/modelling-specification/src/modelling_specification/ui.py` — muted text (reuse `var(--text-muted)`), a short pulsing-opacity animation to make it visibly distinct from a static message, and a `@media (prefers-reduced-motion: reduce)` override that disables the animation.
- [X] T003 Add a `showThinking()` helper to the `<script>` block in `platform/packages/modelling-specification/src/modelling_specification/ui.py`, next to `addMessage`: it calls `addMessage("thinking", "Thinking&hellip;")` (giving the div `class="msg thinking"`, deliberately never `"agent"`, so it is never matched by the existing `.msg.agent` Playwright selectors in `ui_steps.py`) and returns the div so callers can remove it with `.remove()`. Depends on T002 for the CSS class to exist.
- [X] T004 [P] Add an optional `delay: float = 0.0` field to `FakeCompletion.__init__` and sleep on it (`time.sleep(self.delay)`, guarded so `0` sleeps are skipped) at the top of `__call__`, in `platform/packages/modelling-specification/tests/support/fake_llm.py` — `propose`/`propose/resolve-pii` are sync `def` FastAPI routes already run in FastAPI's threadpool, so this does not block the live `uvicorn` test server (research.md).

**Checkpoint**: The indicator can be shown/removed and tests can control LLM timing; both user stories can now proceed.

---

## Phase 3: User Story 1 - See that a request is being worked on (Priority: P1) 🎯 MVP

**Goal**: A visible "Thinking…" indicator appears the instant the architect sends a request, and is replaced by the reply or an error the moment it's ready — the `propose` path (spec.md FR-001, FR-002, FR-004, FR-005, FR-006, FR-007).

**Independent Test**: Send a request with the fake LLM delayed; confirm the indicator is visible while it's in flight, then confirm it's gone and the reply (or error) is shown.

### Tests for User Story 1

- [X] T005 [P] [US1] Add an assertion to `platform/packages/modelling-specification/tests/api/test_ui.py` confirming the served page's static markup wires `showThinking` (e.g. `"showThinking" in page` and the literal `"Thinking"` text) into the script, alongside the existing `_EXPECTED_IDS` checks.
- [X] T006 [US1] Add a new scenario to `platform/packages/modelling-specification/tests/features/conversational_authoring_ui.feature` ("A working indicator is shown while the LLM is proposing a change") and its step(s) to `platform/packages/modelling-specification/tests/features/steps/ui_steps.py`: set `context.fake_llm.delay` long enough to observe it, send a request, assert `#messages .msg.thinking` becomes visible and contains "Thinking" before the reply arrives, then assert it is gone and `#messages .msg.agent` (the real reply) is shown. Depends on T004.

### Implementation for User Story 1

- [X] T007 [US1] In `sendRequest()` (`platform/packages/modelling-specification/src/modelling_specification/ui.py`), call `showThinking()` right after the architect's own message is added and before `postPropose(request)` is awaited; remove it (`.remove()`) in the existing `finally` block, before `sendButton.disabled = false`, so it is removed on every exit path (successful reply, non-ok response, or a thrown exception) — not only the happy path. Depends on T003.

**Checkpoint**: User Story 1 is fully functional and independently testable — the core complaint in GH #186 is fixed for the primary `propose` path.

---

## Phase 4: User Story 2 - See the same indicator after resolving a flagged PII/PHI match (Priority: P1)

**Goal**: The same indicator appears for the resubmission after a PII/PHI review is resolved — the `propose/resolve-pii` path (spec.md FR-003 and the same FR-004/005/006/007 behaviour as US1).

**Independent Test**: Trigger a PII/PHI review, resolve it with the fake LLM delayed, and confirm the same indicator appears for that call and clears the same way.

### Tests for User Story 2

- [X] T008 [US2] Add a scenario to `platform/packages/modelling-specification/tests/features/conversational_authoring_ui.feature` ("A working indicator is shown while a resolved PII/PHI request is proposed") and step(s) in `platform/packages/modelling-specification/tests/features/steps/ui_steps.py`: send a request flagged as personal information, set `context.fake_llm.delay`, choose "Redact and continue", and assert the same `#messages .msg.thinking` visibility/removal sequence as T006. Depends on T004; reuses the delay-setting step T006 adds.

### Implementation for User Story 2

- [X] T009 [US2] In the PII-resolution button click handler inside `renderPiiReview()` (`platform/packages/modelling-specification/src/modelling_specification/ui.py`), call `showThinking()` right before `resolvePii(action, editedText)` is awaited and remove it in a `finally` block wrapped around that call, so it is removed whether `resolvePii` resolves (with or without a result) or throws. Depends on T003 and the pattern established in T007.

**Checkpoint**: Both LLM-calling paths GH #186 names are covered.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T010 [P] Run `poetry run pytest packages/modelling-specification/tests` and `poetry run behave packages/modelling-specification/tests/features` from `platform/`, confirming the whole package suite (not just the tasks above) still passes.
- [ ] T011 Walk through `quickstart.md`'s four manual steps against a locally running `./scripts/run-modelling_specification.sh` instance. **Not run**: this sandbox has no configured LLM provider/credentials; the equivalent flow against a stubbed LLM is already covered end-to-end by T006/T008's behave scenarios (T010), which is this test suite's sanctioned way of validating UI behaviour without a real provider. Left for a human to spot-check against a real provider before merge.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — blocks both user stories.
- **User Story 1 (Phase 3)** and **User Story 2 (Phase 4)**: Both depend on Foundational; independent of each other (US2 reuses US1's behave delay step but needs no US1 code change to work).
- **Polish (Phase 5)**: Depends on both user stories being complete.

### Parallel Opportunities

- T002 and T004 (different files, no shared dependency) can run in parallel.
- T005 (test-only, different file from T007) can run in parallel with early US1 implementation work, though it should fail until T007 lands.
- Phase 3 and Phase 4 implementation (T007, T009) touch the same file (`ui.py`) in different functions — safe for one person to do sequentially, not meaningfully parallelizable across two people without a merge.

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 → Phase 2 (Foundational) → Phase 3 (US1).
2. **Stop and validate**: run T005/T006, confirm the indicator works end-to-end for `propose`.
3. This alone already fixes GH #186's primary complaint.

### Full Fix

4. Add Phase 4 (US2) to cover the `propose/resolve-pii` path GH #186 explicitly calls out.
5. Phase 5 (Polish): full package regression + manual quickstart walkthrough.
