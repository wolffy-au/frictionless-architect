# Tasks: GitHub Roadmap as ArchiMate Implementation & Migration

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [research.md](research.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. Constitution Principle II and the plan require TDD: write each test first, watch it fail, then implement.

**Order**: Outside-in (CLI and acceptance scenarios first, `gh` stubbed behind `run_gh`, then mapping, then file output).

**Rules live elsewhere**: ids, relationships, the Deliverable rule and invariants 1–10 are in [data-model.md](data-model.md); decisions R1–R13 in [research.md](research.md). Tasks cite them rather than restate them.

## Format: `- [ ] T### [P?] [Story?] Description with path`

`[P]` = different file, no dependency on an incomplete task. All commands run from the repo root with `poetry run`.

## Phase 1: Setup

- [X] T001 Create `tests/unit/architecture/conftest.py` with `importer` and `build_mod` fixtures that load `architecture/model/import_gh_roadmap.py` and `architecture/model/build.py` by path via `importlib` (same pattern as `tests/tools/commit_messages/test_check_commit_messages.py`)
- [X] T002 [P] Record trimmed `gh` payloads in `tests/unit/architecture/fixtures/`: `gh_milestones.json` (#1 `policy-to-oscal-mvp`, #2 `multi-user-collaboration`, no issues in #2), `gh_releases.json` (two published releases whose notes name `plat-policy-to-oscal-mvp-1`, one draft, one pre-release), `gh_issues.json` in the GraphQL shape of data-model "Inputs" (#44 and #61 open, #7 closed, all milestone 1; one milestone-less issue whose parent has a milestone). No tokens or personal data
- [X] T003 [P] Add `import_gh_roadmap` to the mypy override module list in `pyproject.toml` beside `build`

## Phase 2: Foundational (blocks every story)

- [X] T004 [P] Write failing tests in `tests/unit/architecture/test_build_layers.py` for R3: a missing `gh-roadmap/` dir is skipped silently; a present layer is merged through `det_id()`; a malformed file is a normal `build.py` error; a duplicate id errors in `add_elements`
- [X] T005 Change `architecture/model/build.py`: add `MODEL_LAYERS = [*VENDORED_MODELS, HERE / "gh-roadmap"]`, iterate it in the loader currently named `load_vendored` (rename to `load_layers`, update its 3 call sites in `main()` and the comment above `VENDORED_MODELS`). Makes T004 pass
- [X] T006 [P] Write failing tests in `tests/unit/architecture/test_import_gh_roadmap.py` for: slug (lower-cased, hyphenated); Work Package slug "cut at a word boundary to at most 40 characters", and a single word longer than 40 is hard-cut at 40; id builders for `plat-`, `del-`, `del-…-unreleased`, `wp-…-gh-<n>` (data-model "Element ids"); `run_gh` failure or unparseable output raises an error naming the failing call and the fix (`gh auth login`) and `main` returns 2; happy-path `fetch_milestones`, `fetch_releases` and `fetch_issues` over stubbed multi-page output (run before T008); 1000 issues over ten pages succeed and `hasNextPage` still true after the 1000-issue cap fails (FR-009, R8); `render_layer` is sorted and byte-identical across two calls with no timestamps (FR-007, invariant 4); `write_layer` writes via `*.tmp` then `os.replace`, and a simulated `os.replace` failure leaves no `*.tmp` and no partial layer (run before T009); `gh` is invoked with an argv list, never `shell=True`
- [X] T007 Create `architecture/model/import_gh_roadmap.py` skeleton: `argparse` (`--repo OWNER/NAME`, `--check`), `GhError`, `run_gh(args) -> str` (`subprocess.run`, argv list), slug and id builders, `main(argv, run_gh=run_gh) -> int` with exit codes 0/1/2 per [importer-cli.md](contracts/importer-cli.md)
- [X] T008 In `architecture/model/import_gh_roadmap.py` add `fetch_milestones`, `fetch_releases` (`gh api --paginate`) and `fetch_issues` (one paginated GraphQL query for `closedAt`, `parent`, `blockedBy`, `milestone`), failing past the 1000-issue cap (R8). Reads `--repo` or `gh repo view` default
- [X] T009 In `architecture/model/import_gh_roadmap.py` add `render_layer(layer) -> dict[str, bytes]` (sorted by kind then number, `yaml.safe_dump` with fixed options, no timestamps; R9, R10) and `write_layer(files, dir)` that writes `*.tmp` beside the layer then `os.replace` only after all three rendered. Print the one-line summary or `unchanged`

**Checkpoint**: layer loads in `build.py`, `gh` failures exit 2, rendering and writing work on an empty layer.

## Phase 3: User Story 1 — See the roadmap as Plateaus, Work Packages and Deliverables (P1) 🎯 MVP

**Goal**: milestones, milestone-assigned issues and published releases become model elements per the Mapping table.

**Independent test**: with the T002 fixtures, `main` writes 2 Plateaus, 1 unreleased Deliverable and 3 Work Packages, and `build.py` validates.

- [X] T010 [US1] Write the failing outside-in test in `tests/unit/architecture/test_import_gh_roadmap.py`: `main(["--repo","o/r"], run_gh=stub)` over the T002 fixtures writes `gh-roadmap/{elements,relationships,views}.yaml` with the counts above and prints the summary line from the CLI contract
- [X] T011 [P] [US1] Write failing unit tests in the same file for the four US1 acceptance scenarios, FR-001–FR-003, FR-006 and data-model invariants 1, 3, 7, 8, 9, 10: closed Work Package realizes a Deliverable never a Plateau; issue without its own milestone creates nothing even if parent or child has one; issue closed between two releases realizes the later release only; issue closed after the latest release stays on the unreleased Deliverable; draft and pre-release skipped; unreleased Deliverable only when a Work Package realizes it; a `bfn-*`/`plat-*` token that does not exactly match an existing element of the right type creates no relationship; hostile titles and descriptions (quotes, colons, `---`, newlines, YAML tags) are escaped and the written files parse back to the same text; no emitted id equals an id in the real first-party `elements.yaml`; an issue whose milestone is missing from the fetched set is dropped
- [X] T012 [US1] In `architecture/model/import_gh_roadmap.py` map milestones to Plateaus: props `gh-number`, `gh-url`, `gh-state`, `gh-due` "(if set)"; `desc` is the milestone `description`; `bfn-*` token in it gives a `Realization` to the matching existing element only
- [X] T013 [US1] Map in-scope issues to Work Packages: in scope "only when it carries a milestone itself"; id `wp-<title-slug>-gh-<n>`; name `GH-<n> <title>`; props `gh-number`, `gh-url`, `gh-state`; issue bodies never imported
- [X] T014 [US1] Map published releases to Deliverables (`del-release-<tag-slug>`, props `gh-tag`, `gh-url`, `gh-published`), ordered by `published_at` then `tag_name`; `Realization` to a `plat-*` id named in the notes only on exact match of an imported Plateau
- [X] T015 [US1] Attach each Work Package to exactly one Deliverable per data-model "Which Deliverable a Work Package realizes" and emit the unreleased Deliverable (`del-<title-slug>-<n>-unreleased`, name `<milestone title> (unreleased)`) with its `Realization` to the Plateau, only when at least one Work Package realizes it
- [X] T016 [US1] Implement the FR-004 derivation filter (skip a link an existing chain implies, judged against the importer's own links only per data-model "Emitted relationships") and add an integration test in `tests/unit/architecture/test_import_gh_roadmap.py` that writes the fixture layer to a temp dir, runs `build.py` over it and asserts `validate.py` exits 0 (invariant 5)
- [X] T017 [US1] Emit `views.yaml`: one view per milestone, `viewpoint: implementation_migration`, `diagram: migration/<plateau id>`, members drawn from the same emitted set (R11). Confirm the overview view in `architecture/model/views.yaml` picks the imported elements up via `include_types` and adjust it only if it does not

**Checkpoint**: US1 independently testable; `build.py` validates the fixture layer.

## Phase 4: User Story 3 — Refresh safely (P1)

**Goal**: one on-demand run that never half-updates and changes nothing when GitHub has not.

**Independent test**: two runs with no GitHub change give no diff; a `gh` failure gives exit 2 and no diff.

- [X] T018 [P] [US3] Write failing tests in `tests/unit/architecture/test_import_gh_roadmap.py`: two `main` runs on the same fixtures leave the files byte-identical (SC-002); closing one issue changes only that issue's `gh-state` and its Deliverable link (SC-003, invariant 6); a failing stub on each of the three fetches, an unparseable payload, and a remaining `hasNextPage` each leave an existing layer untouched and exit 2 (SC-005); across runs: a reopened issue returns to the unreleased Deliverable, a milestone moved retargets only that Realization, a milestone removed removes the element and its links, and a retitled issue gets a new id with the old one gone
- [X] T019 [P] [US3] Write failing tests for `--check`: exit 0 when bytes match, 1 when stale, writes nothing in either case (US3 scenario 2)
- [X] T020 [P] [US3] Write `tests/features/gh_roadmap_import.feature` (SC-002, SC-003: no-change rerun, single-issue close, unreachable GitHub) and `tests/features/steps/gh_roadmap_import_steps.py` wiring it to `main` with the stubbed `run_gh`. Keep wording close to the spec's acceptance scenarios
- [X] T021 [US3] Implement `--check` in `architecture/model/import_gh_roadmap.py`: render in memory, compare to disk, no writes. Make T018–T020 pass, tightening `write_layer` cleanup of temp files if T018 exposes a leak

**Checkpoint**: idempotent, atomic, check-only mode works.

## Phase 5: User Story 2 — See dependencies and hierarchy (P2)

**Goal**: "blocked by" and parent/child links appear when both ends are imported.

**Independent test**: B blocked by A gives A triggers B; a cross-milestone block gives one Plateau → Plateau Triggering.

- [X] T022 [US2] Extend `tests/unit/architecture/fixtures/gh_issues.json` with a blocked-by pair in one milestone, a blocked-by pair across milestones 1 and 2, a parent and child both in scope, a blocker with no milestone, and a two-issue cycle
- [X] T023 [US2] Write failing tests in `tests/unit/architecture/test_import_gh_roadmap.py` for the "Emitted relationships" rows: `Triggering` A→B; `Aggregation` parent→child only when both imported; one de-duplicated `Triggering` Plateau→Plateau with no self-loops; links with an unimported end dropped; cycles emitted as written (R7); the output still validates
- [X] T024 [US2] Implement Triggering and Aggregation derivation in `architecture/model/import_gh_roadmap.py`, reusing the T016 derivation filter

**Checkpoint**: US2 testable alone on the extended fixtures.

## Phase 6: User Story 4 — Coexist with the hand-authored model (P2)

**Goal**: each element has one owner; the retired hand-authored Plateau is gone and nothing dangles. Needs the real layer, so it runs after US1 and US3.

**Independent test**: after the first real import, the first-MVP milestone appears once and no link refers to `plat-runtime-mvp`.

- [X] T025 [US4] After T026, write failing tests in `tests/unit/architecture/test_build_layers.py` (the first needs the committed layer): building the real hand-authored files plus the committed layer yields no `plat-runtime-mvp` anywhere; removing an imported Plateau from a fixture layer makes `build.py` fail naming each dangling hand-authored id (US4 scenario 2)
- [X] T026 [US4] Run the real import and commit the generated layer: `poetry run python architecture/model/import_gh_roadmap.py` against this repo, check the counts against [quickstart.md](quickstart.md) step 1, and add `architecture/model/gh-roadmap/`
- [X] T027 [US4] Edit `architecture/model/elements.yaml`: delete `plat-runtime-mvp` (line ~1560) and `plat-runtime-target` (~1568), which the generated `plat-policy-to-oscal-mvp-1` and `plat-multi-user-collaboration-2` replace. Keep the ADR-0018 narrative by moving it into the renamed Gap's `desc`
- [X] T028 [US4] In the same file rename `gap-runtime-hosted` to follow `gap-<from>-to-<to>` (`gap-policy-to-oscal-mvp-to-multi-user-collaboration`, name and `desc` updated; it was "plat-runtime-mvp -> plat-runtime-target") and add `gap-baseline-to-policy-to-oscal-mvp` (`plat-baseline` → first MVP) with the ADR-0024 solo-use narrative in its `desc`
- [X] T029 [US4] Edit `architecture/model/relationships.yaml` (lines ~877–890): retarget every `plat-runtime-mvp`, `plat-runtime-target` and `gap-runtime-hosted` endpoint to the new ids; add the hand-authored `Triggering` `plat-baseline → plat-policy-to-oscal-mvp-1` and `plat-policy-to-oscal-mvp-1 → plat-multi-user-collaboration-2` (data-model "Gaps and ordering") and an `Association` from each Gap's two Plateaus to that Gap. Enumerate with `grep -rn 'plat-runtime\|gap-runtime' architecture/model/*.yaml` and re-run it to confirm zero hits
- [X] T030 [US4] Edit `architecture/model/views.yaml`: retarget the three `view-runtime-migration` members (~918–920). Run `build.py`; fix until `validate.py` exits 0 and T025 passes
- [X] T031 [US4] Run `poetry run python architecture/model/render_diagrams.py`; confirm `diagrams/migration/overview.*` and one `diagrams/migration/plat-<slug>-<n>.*` per milestone exist (FR-010, SC-004) and the regenerated `frictionless-architect.xml` and diagrams are committed

**Checkpoint**: one owner per element; model validates; diagrams regenerated.

## Phase 7: Polish & cross-cutting

- [X] T032 [P] Write `docs/adr/0035-github-roadmap-as-implementation-migration-layer.md` (MADR, per `docs/adr/README.md`): mapping, id scheme, scope rule, ownership split, link to this spec. Add its row to `docs/adr/README.md` (FR-012)
- [X] T033 [P] Update `ARCHITECTURE.md` §8 and `architecture/model/README.md` (file table: `gh-roadmap/`, `import_gh_roadmap.py`; pipeline diagram; "never hand-edited") per Constitution Principle X. Location confirmed: `ARCHITECTURE.md` §8 is the packaging migration sequence with subsections §8.1 and §8.2, so add a short §8.3 "GitHub roadmap layer" after the §8 Status paragraph, linking ADR-0035 and the migration overview view
- [X] T034 Add the path to the pre-merge coverage run, since `[tool.coverage.run] source = ["src"]` excludes it: append `--cov=architecture/model` to the pytest line in `scripts/pre_merge_checks.sh`, and `omit` the untested `build.py` and `render_diagrams.py` under `[tool.coverage.run]` in `pyproject.toml` with a comment, so the 90% total is not dragged down. Add tests until `import_gh_roadmap.py` reaches 90% (core logic targets 100%)
- [X] T035 Run `quickstart.md` steps 1–6 end to end, including the `GH_TOKEN=invalid` failure check, and fix any discrepancy in the docs
- [X] T036 Run `bash scripts/pre_commit_checks.sh`, then `bash scripts/pre_merge_checks.sh` (behave scenarios included); fix findings. Also run `check_derived.py` on the merged model and confirm no finding involves a `plat-`, `del-` or `wp-` id from the layer
- [X] T037 Post a handoff comment on GH #95 (session handoff rule): what shipped, what is open

## Dependencies

- Phase 1 → Phase 2 → stories. Phase 2 blocks everything.
- **US1** (P1) first. **US3** (P1) builds on US1's output but its tests are independent of US2. **US2** (P2) extends the mapping and fixtures from US1. **US4** (P2) needs US1 and US3 done (it commits the real layer) and is part of the same change per FR-011.
- T025 runs after T026 (it reads the committed layer).
- Within a story: tests before implementation; mapping tasks T012–T015 share one file, so they run in order.
- Polish after all stories; T032/T033 can start once the mapping is stable (after US1).

## Parallel examples

- Setup: T002 ∥ T003.
- Foundational: T004 ∥ T006 (different files), then T005 and T007–T009.
- US1: T010 then T011 (same file; write both before implementing). US3: T018 ∥ T019 ∥ T020 (three files).
- Polish: T032 ∥ T033.

## Implementation strategy

1. **MVP**: Phases 1–3. The importer produces a valid layer from fixtures.
2. Add Phase 4 (US3) so refresh is safe before the layer is ever committed.
3. Add Phase 5 (US2), then Phase 6 (US4) to adopt the real layer and retire the hand-authored plateaus in one change.
4. Polish, then PR.
