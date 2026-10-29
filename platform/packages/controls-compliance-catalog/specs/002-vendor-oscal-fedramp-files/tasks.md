---

description: "Task list for Vendor OSCAL/FedRAMP Files Instead of Submodules"
---

# Tasks: Vendor OSCAL/FedRAMP Files Instead of Submodules

**Input**: Design documents from `platform/packages/controls-compliance-catalog/specs/002-vendor-oscal-fedramp-files/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (all present). No `contracts/` — this feature exposes no external interface.

**Tests**: Not requested in the feature specification. This feature's correctness is verified by the *existing* OSCAL schema-alignment checks and `tests/fixtures/golden-oscal/` golden-fixture tests (Phase 3 tasks run them, unchanged) rather than by writing new tests.

**Organization**: Tasks are grouped by user story (US1, US2 both P1; US3 P2) per `spec.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in each description

## Phase 1: Setup

**Purpose**: Clear the one environment-specific blocker before any git surgery starts.

- [ ] T001 Confirm `sudo` works passwordless on this devcontainer (`sudo -n true`) — needed by T002's submodule deinit on the drvfs-mounted workspace (research.md R7, AGENTS.md's documented chmod-on-write EPERM quirk).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remove the submodule registrations and land each vendored set's files *and* its `PROVENANCE.md` together, in the same task — the upstream commit chosen for a vendored set has exactly one authoritative record (that set's own `PROVENANCE.md`), never a separate note another task would have to look up. Both P1 user stories (US1's removal, US2's provenance) need this in place first, and per spec.md they ship together, not as a follow-up.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Deinit and remove the git submodule registrations for `third_party/oscal`, `third_party/oscal-content`, and `third_party/fedramp-automation`: `git submodule deinit` each path, `git rm --cached` each gitlink, delete their three stanzas from `.gitmodules`, and remove the matching `.git/modules/<name>` entries (`sudo`, per T001). Leave the `third_party/it4it` stanza and submodule untouched (FR-001, FR-012).
- [ ] T003 [P] Choose the upstream commit to vendor `third_party/oscal` from (`usnistgov/OSCAL`), copy its NIST OSCAL schema files (XML/JSON/YAML) into `third_party/oscal/` at their existing upstream-relative subpaths, and write `third_party/oscal/PROVENANCE.md` recording `usnistgov/OSCAL`, that same commit SHA, and the retrieval date in the same step (FR-002, FR-005, SC-004, research.md R1/R2/R8, spec US2 Acceptance Scenario 1).
- [ ] T004 [P] Choose the upstream commit to vendor `third_party/oscal-content` from (`usnistgov/oscal-content`), copy the NIST SP 800-53 rev5 catalog and its LOW/MODERATE/HIGH/PRIVACY baseline profiles (OSCAL JSON) into `third_party/oscal-content/` at their existing upstream-relative subpaths, and write `third_party/oscal-content/PROVENANCE.md` recording that same commit SHA and the retrieval date in the same step (FR-003, FR-005, SC-004, research.md R1/R2/R8, spec US2 Acceptance Scenario 2).
- [ ] T005 [P] Choose the upstream commit to vendor `third_party/fedramp-automation` from (`GoComply/fedramp`), copy the FedRAMP LOW/MODERATE/HIGH resolved baseline catalogs (`FedRAMP_LOW-baseline-resolved-profile_catalog.xml`, `..._MODERATE...`, `..._HIGH...`) into `third_party/fedramp-automation/bundled/catalogs/` — no PRIVACY baseline exists upstream, so none is added — and write `third_party/fedramp-automation/PROVENANCE.md` recording that same commit SHA, the retrieval date, and a note that no PRIVACY baseline exists upstream, in the same step (FR-004, FR-005, SC-004, research.md R1/R2/R8, spec US2 Acceptance Scenario 3).

**Checkpoint**: Submodules gone, vendored files and their `PROVENANCE.md` records present at their existing paths — both P1 user stories can now proceed.

---

## Phase 3: User Story 1 - Drop the three reference-only submodules (Priority: P1) 🎯 MVP

**Goal**: `git submodule status` lists only `it4it`; the vendored files stand in for what the submodules used to provide; existing tests keep passing against them.

**Independent Test**: Run `git submodule status` and confirm only `it4it` remains, then run the existing OSCAL schema-alignment and golden-fixture tests and confirm they pass unchanged.

### Implementation for User Story 1

- [ ] T006 [US1] Run `git submodule status` and confirm it lists exactly one line, for `third_party/it4it` (FR-001, SC-001).
- [ ] T007 [US1] From `platform/`, run `poetry run pytest` (OSCAL schema-alignment checks and the `tests/fixtures/golden-oscal/` golden-fixture tests) and confirm they pass with no change to test logic, reading the files vendored in T003–T005 (FR-010, SC-003).
- [ ] T008 [US1] Confirm a fresh clone plus `git submodule update --init` no longer attempts to fetch `oscal`, `oscal-content`, or `fedramp-automation`, while the vendored files from T003–T005 are already present (SC-002), per quickstart.md's "Validate the submodule removal" section.

**Checkpoint**: User Story 1 is independently functional and testable — the submodules are gone and nothing downstream broke.

---

## Phase 4: User Story 2 - Preserve provenance for every vendored file set (Priority: P1)

**Goal**: Every vendored set carries a `PROVENANCE.md` naming its upstream repository, exact commit SHA, and retrieval date (written in T003–T005), plus its upstream license file.

**Independent Test**: Confirm each `PROVENANCE.md` exists and names an upstream repository, commit SHA, and retrieval date.

### Implementation for User Story 2

- [ ] T009 [US2] Verify `third_party/oscal/PROVENANCE.md`, `third_party/oscal-content/PROVENANCE.md`, and `third_party/fedramp-automation/PROVENANCE.md` (written in T003–T005) each name their upstream repository, a commit SHA, and a retrieval date, and that the FedRAMP one notes no PRIVACY baseline exists upstream (FR-005, SC-004, spec US2 Acceptance Scenarios 1–3) — this is a read-only confirmation, not a new write.
- [ ] T010 [P] [US2] Retain each upstream license file alongside its vendored set: `third_party/oscal/LICENSE.md`, `third_party/oscal-content/LICENSE.md`, `third_party/fedramp-automation/LICENSE.md` (research.md R5, so `third_party/README.md` and `wiki/oscal-compliance.md`'s existing citations of these paths keep resolving).

**Checkpoint**: Both P1 user stories now work independently — vendoring (US1) and its provenance trail (US2) ship together.

---

## Phase 5: User Story 3 - Keep every referencing document consistent (Priority: P2)

**Goal**: ADR-0030, the wiki pages that cite it, `third_party/README.md`, the golden-fixture provenance metadata, and the `001-oscal-ai-conversion` spec artefacts all describe the vendored-file approach — nobody follows a stale `git submodule update --init` instruction.

**Independent Test**: Grep the tracked documentation tree for any remaining submodule-checkout instruction naming `oscal`, `oscal-content`, or `fedramp-automation`, confirm there are none, and confirm the wiki has been regenerated to match.

### Implementation for User Story 3

- [ ] T011 [US3] Amend `docs/adr/0030-vendor-oscal-reference-content.md` with a new, dated implementation note recording the submodule → selective-file-vendoring switch for `oscal`, `oscal-content`, and `fedramp-automation`, leaving the `it4it`/ADR-0029 decision unchanged (FR-006, research.md R4, spec US3 Acceptance Scenario 1).
- [ ] T012 [US3] Update `third_party/README.md`: remove the submodule-tracking framing for `oscal`, `oscal-content`, and `fedramp-automation`, and describe the vendored paths and their `PROVENANCE.md`/license files in its place (FR-007).
- [ ] T013 [P] [US3] For all 17 `tests/fixtures/golden-oscal/**/*.provenance.yaml` files, verify each `source_repo`/`source_commit` field against the matching vendored set's `PROVENANCE.md` commit SHA (written in T003–T005) — the authoritative source per FR-008 — and correct any that no longer match (FR-008, spec US3 Acceptance Scenario 3).
- [ ] T014 [US3] Update `platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/quickstart.md` line 9 to remove the `git submodule update --init third_party/oscal-content third_party/fedramp-automation` instruction and describe the vendored paths instead (FR-009, spec US3 Acceptance Scenario 4).
- [ ] T015 [P] [US3] Review the `third_party/oscal-content`/`third_party/fedramp-automation` references in `platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/{plan,data-model,research}.md` and confirm each reads correctly as a vendored (not submodule) path; edit only where the wording assumes a submodule checkout (FR-009).
- [ ] T016 [US3] Run the `wiki-librarian` skill to regenerate `wiki/oscal-compliance.md`, `wiki/architecture.md`, `wiki/controls-compliance-catalog.md`, and `wiki/index.md` so they reflect the ADR-0030 note from T011 — never hand-edit these pages (FR-011, research.md R6, spec US3 Acceptance Scenario 2). Depends on T011 and T012.
- [ ] T017 [US3] Grep the tracked documentation tree for `git submodule update --init` naming `oscal`, `oscal-content`, or `fedramp-automation`; confirm no matches remain outside historical/changelog text (SC-005).

**Checkpoint**: All three user stories are independently functional — vendoring, provenance, and documentation consistency are each verifiably done.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final invariant checks and formatting, across all stories.

- [ ] T018 [P] Confirm `third_party/it4it`'s `.gitmodules` stanza and content are unchanged by this feature (FR-012).
- [ ] T019 Run quickstart.md's full validation sequence end-to-end (submodule removal, provenance, tests, documentation consistency) and confirm every expectation holds.
- [ ] T020 [P] Run `pymarkdown` lint over every touched/added Markdown file (`docs/adr/0030-vendor-oscal-reference-content.md`, `third_party/README.md`, the three `PROVENANCE.md` files, and the touched `001-oscal-ai-conversion` artefacts), per this repo's `pre_commit_checks.sh` gate.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on T001 (submodule deinit in T002 needs `sudo` to work) — BLOCKS both User Story 1 and User Story 2.
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion. No dependency on US2 or US3.
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion — T009 verifies the `PROVENANCE.md` files T003–T005 already wrote. Independent of US1's verification tasks (T006–T008) — can run in parallel with Phase 3.
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) completion for T013 (the `PROVENANCE.md` commit SHAs it checks against must exist) and on T011/T012 completing before T016 (wiki regenerates from the updated ADR/README). Otherwise independent of US1/US2.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Parallel Opportunities

- T003, T004, T005 (Foundational file copies + provenance) — different `third_party/` subdirectories, can run in parallel once T002 has removed the submodule registrations.
- T010 (US2 license retention) can run in parallel with T009 (US2 provenance verification) — different files.
- T013, T015 (US3) — different files from T011/T012/T014, can run in parallel.
- T018, T020 (Polish) — different files/concerns, can run in parallel.
- Phase 3 (US1) and Phase 4 (US2) can be worked in parallel once Phase 2 is done, though spec.md's US2 rationale means both should land in the same PR before merging.

---

## Parallel Example: Foundational Phase

```bash
# After T002 (submodule deinit) completes, launch the three file-copy-and-provenance tasks together:
Task: "Vendor NIST OSCAL schema files + PROVENANCE.md into third_party/oscal/"
Task: "Vendor NIST SP 800-53 rev5 catalog + baselines + PROVENANCE.md into third_party/oscal-content/"
Task: "Vendor FedRAMP resolved baseline catalogs + PROVENANCE.md into third_party/fedramp-automation/bundled/catalogs/"
```

## Parallel Example: User Story 2

```bash
# Once Foundational is done, launch both US2 tasks together:
Task: "Verify all three PROVENANCE.md files written in T003-T005"
Task: "Retain upstream LICENSE.md files for all three vendored sets"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 together)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks both P1 stories).
3. Complete Phase 3: User Story 1, and Phase 4: User Story 2, in parallel or either order.
4. **STOP and VALIDATE**: both P1 stories are what spec.md calls the MVP — the migration is functionally complete and provenance-traceable even before documentation catches up.

### Incremental Delivery

1. Setup + Foundational → vendored files and their `PROVENANCE.md` records in place, submodules gone.
2. User Story 1 + User Story 2 (ship together, per spec.md's US2 rationale) → MVP: a traceable, tested vendoring migration.
3. User Story 3 → documentation (ADR, README, wiki, specs) catches up to match.
4. Polish → final invariant checks and lint.

---

## Notes

- `[P]` tasks touch different files with no completed-task dependency between them.
- `[Story]` labels map tasks to spec.md's user stories for traceability.
- No test-writing tasks: this feature's verification is running the *existing* test suite (T007) and the quickstart.md validation steps (T006, T008, T019), not authoring new tests.
- Each vendored set's upstream commit SHA has exactly one authoritative record — its own `PROVENANCE.md`, written in the same task as its files (T003–T005) — so no other task needs a separate scratch note to track it.
- Commit after each phase checkpoint, not after every individual task — the submodule-removal-plus-vendoring step (T002–T005) is not meaningfully separable into smaller commits.
