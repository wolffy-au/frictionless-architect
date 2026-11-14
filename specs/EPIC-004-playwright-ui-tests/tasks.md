---

description: "Task list for EPIC-004: Browser-Level Tests for the HTML UIs"
---

# Tasks: Browser-Level Tests for the HTML UIs

**Input**: Design documents from `specs/EPIC-004-playwright-ui-tests/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md` — all present.

**Tests**: Browser-level tests are this feature's deliverable, not an optional add-on;
tasks for them are listed directly under each story, not as an optional sub-section.

**Organization**: Tasks are grouped by user story (`spec.md`) to enable independent
implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Make `playwright` available to the toolchain this feature extends (ADR-0053).

- [X] T001 Add `playwright` to the root `pyproject.toml`'s `tests` dependency group
  (`[dependency-groups]` → `tests`), mirroring `platform/pyproject.toml`'s existing `tests`
  group entry (research.md → "Reuse the existing behave + Playwright pattern").
- [X] T002 Refresh the root `poetry.lock` for the `pyproject.toml` change in T001 (depends on
  T001).
- [X] T003 [P] In `scripts/pre_merge_checks.sh`, delete the dead `frontend/` stub block (the
  one that checks for a nonexistent `frontend/` directory and always prints "Skipping…") and
  add a `poetry run playwright install --with-deps chromium` step immediately before the
  existing root `poetry run behave tests/features/` call (ADR-0053 Decision and
  Consequences).

**Checkpoint**: `playwright` is installable and the merge gate script no longer contains the
no-op UI step.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Give root-level `behave` scenarios the same live-server + Playwright capability
`controls-compliance-catalog`/`modelling-specification` already have, so User Story 1's new
visualiser scenario (the only new root-level `@ui` scenario this feature adds) has
somewhere to run.

**⚠️ CRITICAL**: No user story task below can run until this phase is complete.

- [X] T004 Extend `tests/features/environment.py` (root) to add a conditional live-`uvicorn`
  + Playwright Chromium setup/teardown for `@ui`-tagged scenarios only, mirroring
  `platform/packages/controls-compliance-catalog/tests/features/environment.py`'s pattern
  (background-thread `uvicorn.Server` on an OS-assigned free port, `sync_playwright()`
  browser launch/teardown in `before_scenario`/`after_scenario` gated on the `@ui` tag, so
  non-`@ui` scenarios in this same file are unaffected and don't pay for a browser launch;
  this is what gives FR-003's "live instance, not a static fixture" requirement a real
  harness to run against). Depends on T001 (needs `playwright` importable).

**Checkpoint**: A root-level `@ui`-tagged scenario can boot a live app and drive it with
Playwright, exactly like the existing platform-package harness.

---

## Phase 3: User Story 1 - Catch broken UI changes before they merge (Priority: P1) 🎯 MVP

**Goal**: Every in-scope UI surface (playground, LLM provider config page, visualiser) has
an automated browser-level test that fails on a JS console error or a broken main
interaction, per `spec.md`'s Acceptance Scenarios 1-3.

**Independent Test**: Deliberately break a UI's main interaction (e.g. disable a button's
click handler) on a branch, run the merge gate, confirm it fails naming the page and error;
revert and confirm it passes (`spec.md` US1 Independent Test).

### Implementation for User Story 1

- [X] T005 [P] [US1] Add a minimal placeholder HTML route to
  `src/frictionless_architect/visualizer/` (new module, e.g. `placeholder_page.py`) per
  `contracts/visualiser-placeholder-page.md` and `data-model.md`: a `GET /` response with
  (a) a fixed page title, e.g. "Schema Visualiser", (b) visible status text confirming the
  page rendered, and (c) a value derived from the existing `/schema-payload` JSON endpoint
  (using the sample-data fallback per `VisualizerSettings.neo4j_uri`'s existing default, no
  live Neo4j required — FR-004). Include a short comment noting the page is superseded once
  GH #74 ships (ADR-0053 Consequences) and is not meant to accrete features.
- [X] T006 [US1] Mount the new placeholder route in `src/frictionless_architect/app.py`
  (depends on T005).
- [X] T007 [US1] Add `tests/features/visualiser_ui.feature` (root, tagged `@ui`) with
  scenarios covering: the placeholder page loads with no JavaScript console error (FR-001,
  Acceptance Scenario 1) and its schema-summary value renders correctly from the sample-data
  fallback (FR-002, Acceptance Scenario 2). Depends on T004 (harness) and T006 (route
  mounted).
- [X] T008 [US1] Implement the step definitions for `visualiser_ui.feature` in
  `tests/features/steps/visualiser_ui_steps.py`: launch the live app + Playwright browser via
  the T004 harness, navigate to the placeholder page, assert zero console errors, and assert
  the rendered status text / schema-summary value matches the sample-data fallback. Rely on
  Playwright's default action/navigation timeout (no custom override) so a stuck page fails
  with a clear error rather than hanging indefinitely. Depends on T007.
- [X] T009 [US1] Implement the one-retry-before-failure policy (FR-008, Clarifications
  Session 2026-11-14 Option B) in `tests/features/environment.py`'s `@ui` scenario hook: on
  first failure, retry the scenario exactly once before reporting it; a second consecutive
  failure is reported as a real failure, never retried further. Depends on T004.
- [X] T010 [US1] Confirm (no code change expected) that
  `platform/packages/controls-compliance-catalog/tests/features/` and
  `platform/packages/modelling-specification/tests/features/`'s existing `@ui`-tagged
  scenarios already satisfy FR-001/FR-002 for the playground and LLM provider config page —
  run `poetry run behave` in `platform/` and confirm both pass, completing SC-001 for all
  three in-scope surfaces end to end.
- [X] T011 [US1] Deliberately break the visualiser placeholder's rendered interaction
  (e.g. make the schema-summary value render a hardcoded wrong string), run `poetry run
  behave tests/features/ --tags=@ui`, confirm it fails naming the page and the broken
  value, then revert the breakage and confirm it passes (SC-002). Depends on T007-T009.

**Checkpoint**: All three in-scope UI surfaces have at least one passing browser-level test
(SC-001); a deliberately broken interaction on any of them is caught before merge (SC-002).

---

## Phase 4: User Story 2 - Make the merge gate's UI step do something (Priority: P2)

**Goal**: The merge gate's UI step executes real browser-level tests and reports a genuine
pass/fail result, never "Skipping…" (FR-006); the fast gate still runs none of them (FR-005).

**Independent Test**: Run the merge gate on a clean branch and confirm the UI step executes
real checks and reports pass/fail rather than printing "Skipping…" (`spec.md` US2
Independent Test).

### Implementation for User Story 2

- [ ] T012 [US2] Run `scripts/pre_merge_checks.sh` end to end and confirm: the dead
  `frontend/` block from T003 is gone, the new Playwright install step runs before `behave`,
  the root `behave tests/features/` call now executes `visualiser_ui.feature` (T007-T009),
  and `scripts/platform_checks.sh`'s existing fan-out still executes the platform packages'
  `@ui` scenarios (T010) — confirm no step in the script prints "Skipping…" for UI tests
  (FR-006, SC-003). Depends on T003, T009, T010.
- [ ] T013 [US2] Run `scripts/pre_commit_checks.sh` and confirm it invokes neither `behave`
  nor any `@ui`-tagged scenario, so the fast gate's typical runtime is unaffected by this
  feature (FR-005, SC-005).

**Checkpoint**: The merge gate's UI step is a real gate (User Stories 1 AND 2 both verified
working together).

---

## Phase 5: User Story 3 - Reproduce a failing UI test locally (Priority: P3)

**Goal**: A contributor who has never run the UI tests before can get the full suite running
locally from documentation alone, and a local failure identifies the failing page and check.

**Independent Test**: Follow only the documented steps on a machine that has never run these
tests before, and confirm the full UI test suite runs to completion locally (`spec.md` US3
Independent Test).

### Implementation for User Story 3

- [ ] T014 [P] [US3] Update `TECHNICAL.md`'s "Testing Layout" section to document the
  one-time Playwright setup (`poetry run playwright install --with-deps chromium`, run once
  for root and once inside `platform/`) and how `@ui`-tagged scenarios fit into the existing
  `behave` layout, linking to `specs/EPIC-004-playwright-ui-tests/quickstart.md` for the
  exact run commands rather than duplicating them (FR-007, Principle XI — no restated
  content).
- [ ] T015 [US3] Validate `quickstart.md` end to end on a shell with no prior Playwright
  setup: follow its "One-time setup" and "Run the tests" sections exactly as written, confirm
  the suite completes with no undocumented manual step (SC-004), and confirm a deliberately
  broken interaction (quickstart.md → "Verifying the merge gate actually catches a
  regression") names the failing page and check in the output (Acceptance Scenario 2 of
  US3). Depends on T007-T011.

**Checkpoint**: All three user stories are independently functional; the suite is fully
reproducible from documentation alone.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final whole-feature verification, not new behaviour.

- [ ] T016 Run `bash scripts/pre_commit_checks.sh` and fix any lint/type issues introduced by
  T005-T009 and T014.
- [ ] T017 Run `bash scripts/pre_merge_checks.sh` in full (including Snyk, coverage-gated
  pytest, and behave) and confirm a clean pass with all three in-scope UI surfaces reporting
  a real result.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on T001 (Setup) — blocks all of User Story 1's new
  root-level scenario work.
- **User Story 1 (Phase 3)**: Depends on Foundational (T004) and Setup (T001), except T005
  (the placeholder-page route itself, a `src/` file unrelated to the test harness), which
  may start as soon as Setup begins — see Parallel Opportunities.
- **User Story 2 (Phase 4)**: Depends on Setup (T003) and User Story 1 (T009, T010) — it
  verifies the gate script runs what US1 built.
- **User Story 3 (Phase 5)**: Depends on User Story 1 (T007-T011) — it documents and
  validates what US1 built; independent of US2.
- **Polish (Phase 6)**: Depends on all of the above.

### Parallel Opportunities

- T003 can run in parallel with T001/T002 (different file).
- T005 can start in parallel with T001-T004 (different file; only needs T006 to mount the
  route once both are ready).
- T014 can run in parallel with T012/T013 (different file).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1) — all three UI surfaces now have passing browser-level
   smoke tests.
3. **STOP and VALIDATE**: deliberately break one surface's interaction, confirm `poetry run
   behave tests/features/` (root) and `platform/`'s behave suite catch it.

### Incremental Delivery

1. Setup + Foundational → root `@ui` harness ready.
2. User Story 1 → SC-001/SC-002 satisfied (MVP).
3. User Story 2 → SC-003/SC-005 satisfied (the merge gate step is real).
4. User Story 3 → SC-004 satisfied (documented, reproducible locally).
5. Polish → full gate verification.
