---

description: "Task list for AI-Assisted Policy & Standard Conversion to OSCAL"
---

# Tasks: AI-Assisted Policy & Standard Conversion to OSCAL

**Input**: Design documents from `platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/api.md (all present).

**Tests**: Requested implicitly by FR-012 ("real trestle invocations... not mocked") and plan.md's Testing section — contract tests per endpoint, plus the FR-006/FR-007 golden-dataset tests marked `golden` and excluded from the default run.

**Organization**: Tasks are grouped by user story (US1 P1, US2 P2, US3 P3) per `spec.md`. Written retroactively (`/speckit-converge`-style assessment): most of this feature's pipeline has **not** been built yet — only the tasks marked `[X]` exist in the repo today. This package's actual first delivery was [GH #76](https://github.com/wolffy-au/frictionless-architect/issues/76)'s standalone playground, not this spec's journey API.

**Tracking**: This feature is scoped by [GH #44](https://github.com/wolffy-au/frictionless-architect/issues/44) "Markdown catalogue converter" (milestone `policy-to-oscal-mvp`), which takes an explicit **outside-in** build order: UI with stubs first (#164) → stubbed API validated against the UI (#165) → backend functionality (#166). **#44 and its #164/#165/#166 sub-issues are still open** — nothing below should be read as closing them; only #47 (UML diagrams) is closed on that issue. The Phase 3–5 tasks below are #166's backend work; #164 and #165 (the real Document Author upload UI and its stub) have not started and are not re-created here — track them on GH #44 directly.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in each description

## Phase 1: Setup

**Purpose**: Project initialization (already done before this tasks.md was written).

- [X] T001 Package scaffold already in place: `platform/packages/controls-compliance-catalog/{pyproject.toml,src/controls_compliance_catalog/,tests/}` (ADR-0002 monorepo convention). `.specify` symlink added alongside this tasks.md so this package can run its own `NNN-` spec sequence (matching `schema-visualizer-api`/`digital-twin-knowledge-graph`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure every user story below needs. Two pieces exist; the rest doesn't.

**⚠️ CRITICAL**: No US1–US3 implementation task can begin until T005–T008 are done.

- [X] T002 R2: `ext-llm` wrapper — `convert_chunk(prompt, system) -> str` in `src/controls_compliance_catalog/llm_client.py`, resolving provider/model/credential via `llm-provider-config.resolve_call` (ADR-0034) for component `controls-compliance-catalog.candidate-conversion`, normalizing every failure (missing config, missing credential, provider error, empty response) to one `LlmConversionError` type (FR-014's "one exception type to catch"). Tested: `tests/unit/test_llm_client.py`.
- [X] T003 [P] [GH #76] Control Conversion Playground: a standalone dev-tool UI (not part of this spec's `/oscal/*` journey API — `contracts/api.md`'s "Out of scope for this contract" explicitly excludes any UI) comparing Trestle's deterministic OSCAL→Markdown conversion against the AI prose→Markdown candidate (T002) for one control at a time, free-form and not golden-dataset-backed. This is an exploratory precursor, **not** GH #44's #164 "UI with stubs" step — it has no stubbed backend to validate against and doesn't touch the `/oscal/*` contract. Files: `src/controls_compliance_catalog/playground/{api.py,convert.py,prompts.py,prompts.yaml}`, mounted from `app.py`. Tested: `tests/api/test_playground_api.py`, `tests/unit/playground/{test_convert.py,test_prompts.py}`, `tests/features/*.feature` + `steps/playground_steps.py`, `tests/integration/test_ollama_live.py`, `tests/test_pii_gateway_exemption.py`.
- [ ] T004 GH #44 outside-in sequence (#164, #165): build the real Document Author upload UI with stubbed `/oscal/conversions` values first, validate it, then replace the stub with the real endpoint (T014) once it exists. **Not started** — tracked on GH #44/#164/#165, not reproduced as sub-tasks here, since the formal UI role (Document Author upload flow) is a separate future piece per `contracts/api.md`'s own framing ("later role-specific UIs... call these endpoints; none are built as part of this feature").
- [ ] T005 [P] Create `OscalSettings` in `src/controls_compliance_catalog/config.py`: `FRICTIONLESS_ARCHITECT_` env prefix, `data_dir` (default `.data/oscal/`), LLM model/timeout settings, per `plan.md` Project Structure.
- [ ] T006 [P] Create the domain Pydantic v2 models in `src/controls_compliance_catalog/models.py` per `data-model.md`: `SourceDocumentIdentifier`, `PolicyStandardDocument` (`source_kind: Literal["custom-policy", "regulatory-standard"]`, `content_format: Literal["pdf","docx","xlsx","csv","markdown","text"]`), `NormalizedDocument`, `SourceMapEntry` (`status: Literal["pending","converted","unconvertible"]`), `TrestleEditableMarkdownCatalog` (`status: Literal["converted","conversion_failed","validated","validation_failed"]`), `ValidationReport` (`status: Literal["pass","fail"]`), `ApprovalRecord`, `OscalCatalog`, `OscalProfile`, `ResolvedOscalCatalog`, `LedgerEntry` (`action: Literal["convert","validate","assemble","resolve","approve"]`, `outcome: Literal["success","failure"]`).
- [ ] T007 [P] R3: append-only JSONL forensic ledger in `src/controls_compliance_catalog/ledger.py` — one JSON object per line at `<data_dir>/forensic-ledger.jsonl` (`LedgerEntry` shape, T006); never rewritten or deleted, corrections are new entries only (FR-017). Depends on T005, T006.
- [ ] T008 [P] R7: Trestle workspace layout keyed by Source Document Identifier in `src/controls_compliance_catalog/workspace.py` — one subdirectory per `slug(source_document_id)` under `<data_dir>/workspaces/<slug>/` (Trestle's own `catalogs/`/`profiles/`/`dist/` layout); resubmission under the same identifier reuses and overwrites that workspace, never creates a new one (FR-015). Depends on T005.

**Checkpoint**: Once T005–T008 land, US1–US3 implementation can start.

---

## Phase 3: User Story 1 - Convert a verbatim document into Trestle-editable Markdown (Priority: P1) 🎯 MVP

**Goal**: Submit a verbatim PDF/Word/spreadsheet-CSV/Markdown/text document and get back Trestle-editable Markdown that passes Trestle's own structural/header validation.

**Independent Test**: Submit a verbatim document and confirm the system produces Markdown that passes compliance-trestle's structural/header validation, independent of assembly or resolution.

### Tests for User Story 1

- [ ] T009 [P] [US1] Contract tests for `POST /oscal/conversions` and `GET /oscal/conversions/{source_document_id}` in `tests/api/test_oscal_conversions.py`, covering `201`/`409`/`422` per `contracts/api.md` and Acceptance Scenarios 1–4 (including the `"unconvertible"` source-map case, AS3).

### Implementation for User Story 1

- [ ] T010 [US1] R4: `src/controls_compliance_catalog/normalizer.py` — `normalize(path, content_format) -> NormalizedDocument`: `pypdf` for PDF, `python-docx` for `.docx`, stdlib `csv` for `.csv`, `openpyxl` for `.xlsx`, direct UTF-8 read for Markdown/text; split into `SourceMapEntry` sections (`source_id` `SRC-001`, `SRC-002`, ...; `heading`; `level`; `start_line`/`end_line`; `text_sha256`). Carries an attribution header per R10 (ported from `oscal-document-workbench`'s `extract-legacy-doc.sh`, Apache-2.0 §4). Depends on T006.
- [ ] T011 [US1] R5: `src/controls_compliance_catalog/chunking.py` — pack normalizer sections (T010) into LLM-call chunks up to a configured token budget, never splitting a section mid-body; carry a trailing-context overlap (previous chunk's last heading + excerpt) into the next chunk so a control spanning two sections still resolves to one identifier and one coherent statement (FR-018). Depends on T010.
- [ ] T012 [US1] `src/controls_compliance_catalog/markdown_converter.py` — orchestrate normalize (T010) + chunk (T011) + `llm_client.convert_chunk` (T002, already built) → Trestle Markdown, updating each `SourceMapEntry.status` in place (`pending` → `converted`/`unconvertible`, never silently dropped — US1 AS3). Depends on T010, T011, T002.
- [ ] T013 [US1] R6: `src/controls_compliance_catalog/trestle_ops.py` `validate()` — wrap Trestle's in-process structural/header validation, producing a `ValidationReport` (T006) with `note: "Structural validation only; not an audit opinion."` (FR-003/FR-010/SC-004). Carries an attribution header per R10 (ported from `validate-oscal-package.sh`). Depends on T006.
- [ ] T014 [US1] `POST /oscal/conversions` + `GET /oscal/conversions/{source_document_id}` in `src/controls_compliance_catalog/api.py`: orchestrate normalize→chunk→convert→validate (T012, T013), persist into the T008 workspace, append `convert`/`validate` `LedgerEntry` records (T007). FR-013: a control-identifier collision fails the whole conversion (no partial merge). FR-014: an LLM error/timeout fails the whole conversion (zero partial output). FR-015: resubmission under the same identifier overwrites. Depends on T012, T013, T007, T008.
- [ ] T015 [US1] Golden-dataset test (FR-006, SC-002): `tests/api/test_oscal_golden_dataset.py`, `pytest` marker `golden`, converts the vendored `third_party/oscal-content` NIST SP 800-53 rev5 verbatim text through T014 and judges each produced control a faithful paraphrase (LLM-as-judge, not exact match) against the real vendored OSCAL catalog — 100% of controls must be identified. Excluded from the default `poetry run pytest` run (R8). Depends on T014.

**Checkpoint**: User Story 1 independently functional and testable once T009–T015 land.

---

## Phase 4: User Story 2 - Produce an OSCAL Catalog and Profile from converted Markdown (Priority: P2)

**Goal**: Orchestrate Trestle's import/author/assemble commands into a validated OSCAL Catalog + Profile, gated by Compliance Officer/Auditor approval (FR-011).

**Independent Test**: Supply already-valid Trestle Markdown (bypassing AI conversion) and confirm the system produces an OSCAL Catalog and Profile.

### Tests for User Story 2

- [ ] T016 [P] [US2] Contract tests for `POST /oscal/conversions/{id}/approve` and `POST /oscal/assemblies` in `tests/api/test_oscal_assemblies.py`, covering `200`/`403`/`404`/`422`/`502` per `contracts/api.md` and Acceptance Scenarios 1–2.

### Implementation for User Story 2

- [ ] T017 [US2] `src/controls_compliance_catalog/approval.py` — FR-011 approval-gate logic: a `regulatory-standard` document always re-requires approval on every conversion; a `custom-policy` document stays approved across later re-conversions of the same identifier once `approved: true`. Reads `ApprovalRecord` as a read-side projection over the latest `approve` `LedgerEntry` for that identifier (R9) — never an independent store that could drift from the ledger. Depends on T006, T007.
- [ ] T018 [US2] R6: `trestle_ops.py` import + author/assemble — orchestrate Trestle's import and author/assemble commands into an OSCAL Catalog + Profile from validated Markdown (FR-004). Normalizes Trestle's own errors into this feature's error types so failures stay specific/actionable, never a partial or corrupt file (FR-009, FR-010). Depends on T013.
- [ ] T019 [US2] `POST /oscal/conversions/{source_document_id}/approve` in `api.py`: record a Compliance Officer/Auditor approval (`{approved_by}` body), append an `approve` `LedgerEntry`; `404` if no `validated` conversion exists yet. Depends on T017.
- [ ] T020 [US2] `POST /oscal/assemblies` in `api.py`: check the T017 approval gate and the T013 `validated` status before assembling via T018; append an `assemble` `LedgerEntry`. `403` if the gate isn't satisfied, `422` if the conversion isn't `validated`, `502` on Trestle assembly failure. Depends on T017, T018, T019.

**Checkpoint**: User Stories 1 and 2 both independently functional once their phases land.

---

## Phase 5: User Story 3 - Resolve a Profile into a fully resolved Catalog (Priority: P3)

**Goal**: Orchestrate Trestle's profile-resolve command into a fully resolved OSCAL Catalog.

**Independent Test**: Supply an existing valid Catalog and Profile pair and confirm a resolved Catalog is produced, independent of where that pair came from.

### Tests for User Story 3

- [ ] T021 [P] [US3] Contract test for `POST /oscal/resolutions` in `tests/api/test_oscal_resolutions.py`, covering `201`/`422`/`502` per `contracts/api.md` and Acceptance Scenarios 1–2.

### Implementation for User Story 3

- [ ] T022 [US3] R6: `trestle_ops.py` profile-resolve — orchestrate Trestle's `profile-resolve` command into a fully resolved OSCAL Catalog from a Profile and its source Catalog (FR-005). Fails clearly, with no artefact written, if the referenced Catalog hasn't been assembled yet (US3 AS2). Depends on T018.
- [ ] T023 [US3] `POST /oscal/resolutions` in `api.py`: append a `resolve` `LedgerEntry`; `422` if the Catalog/Profile pair doesn't exist yet, `502` on Trestle resolution failure (FR-010). Depends on T022.
- [ ] T024 [US3] Golden-dataset test (FR-007, SC-003): resolve the golden LOW/MODERATE/HIGH/PRIVACY profiles against the golden catalog through T023 and compare to FedRAMP's vendored pre-resolved baselines (`third_party/fedramp-automation`) — 100% of controls must be reproduced, to the same faithfulness standard as T015. Marked `golden`, excluded from the default run. Depends on T023.

**Checkpoint**: All three user stories independently functional once their phases land.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting checks once US1–US3 exist. Two are already satisfied.

- [X] T025 FR-016's documented exception to ADR-0014's redaction rule (verbatim document content sent to the LLM as-is) is recorded in `docs/adr/0031-fr016-no-redaction-for-policy-documents.md`, Status: Accepted.
- [ ] T026 FR-009 cross-cutting check: once T014/T018/T022 all exist, confirm the Catalog, Profile, and Resolved-Catalog outputs stay distinct paths/records across all three endpoints — no output silently substitutes for another.
- [ ] T027 [P] Run `quickstart.md`'s full validation sequence end-to-end (US1 conversion → US2 approve+assemble → US3 resolve → golden-dataset run → failure-mode checks) once Phases 3–5 land.
- [ ] T028 [P] Run `bash scripts/platform_checks.sh` (pyright, mypy, pytest at 90% coverage) and `bash scripts/pre_commit_checks.sh` once all tasks above land.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Done (T001).
- **Foundational (Phase 2)**: T002, T003 done; T005–T008 **block** all of Phase 3–5 and are not started. T004 (GH #44's UI steps) tracked externally, not blocking the backend phases below.
- **User Story 1 (Phase 3)**: Depends on Foundational (T005–T008) completion. No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational completion and on US1's `trestle_ops.validate()` (T013) for a `validated` Markdown input — can be built in parallel with the rest of US1 once T013 lands, but functionally sits downstream of US1.
- **User Story 3 (Phase 5)**: Depends on US2's assemble path (T018) for a Catalog/Profile pair to resolve.
- **Polish (Phase 6)**: Depends on US1–US3 all being complete (except T025, already done).

### Parallel Opportunities

- T005, T006, T007, T008 (Foundational) — T007/T008 each depend on T005/T006 but not on each other, so once T005/T006 land they can proceed in parallel.
- T009 (US1 contract test) can be written in parallel with T010–T013 (different files), per TDD — write it first, expect it to fail.
- T016 (US2) and T021 (US3) contract tests are independent of each other and of T009.
- T027, T028 (Polish) are independent of each other.

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (done) → Phase 2 Foundational (T005–T008, not started) → Phase 3 (US1).
2. **Stop and validate**: run quickstart.md's "Validate User Story 1" against T014; this alone proves the net-new capability (spec.md: "Nothing upstream of this exists today").

### Incremental Delivery

1. Foundational (T005–T008) → unblocks everything.
2. US1 (Phase 3) → MVP: verbatim document → validated Trestle Markdown.
3. US2 (Phase 4) → adds the approval-gated Catalog/Profile assembly.
4. US3 (Phase 5) → adds Profile resolution.
5. Polish (Phase 6) → cross-cutting checks and the full gate suite.

### Outside-in note (GH #44)

T004 (the real Document Author upload UI, stubbed then wired to live endpoints) is explicitly **not** sequenced here — GH #44 puts it *before* the backend (T005–T024) in its own outside-in ordering, but this package's actual history ran backend-first after the T002/T003 exploration. Whoever picks this up next should treat GH #44/#164/#165 as the open item they are, not assume T005–T024 above supersedes them.

---

## Notes

- `[P]` tasks touch different files with no completed-task dependency between them.
- `[Story]` labels map tasks to spec.md's user stories for traceability.
- T002 and T003 are already built and tested; every other task above (except T001, T025) is open. Do not mark T004–T024 done without the corresponding code and tests actually existing — this tasks.md was deliberately written to reflect that gap, not to paper over it.
- Model impact: none — see `plan.md`'s "Model Impact" section (`ext-llm`, `store-ledger`, `fn-oscal-conversion`, `fn-oscal-validation`, `fn-oscal-profile-resolve` already exist in `architecture/model/`; this feature implements them without adding, changing, or retiring any element, relationship, or view id).
