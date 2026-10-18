---

description: "Task list for digital-twin-knowledge-graph — Knowledge Graph Read Path (GH #106)"
---

# Tasks: Digital Twin Knowledge Graph — Read Path

**Input**: Design documents from `platform/packages/digital-twin-knowledge-graph/specs/001-knowledge-graph-read-path/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/read-path.md, quickstart.md (all present)

**Tests**: Requested explicitly — spec.md User Story 5 / FR-011 / SC-003 require the ported
flat-`src/` test cases to pass unmodified in their expectations against the new package's code,
and `scripts/platform_checks.sh` gates `platform/packages/*` at 90% line coverage (FR-014). Test
tasks are therefore included throughout, ported from the existing flat-`src/` test files rather
than written from scratch (research.md R7).

**Organization**: Tasks are grouped by user story (spec.md priorities) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5, spec.md priorities)
- Paths are relative to the repo root unless noted otherwise.

## Path Conventions

Monorepo package (ADR-0002, plan.md Project Structure):

- Package root: `platform/packages/digital-twin-knowledge-graph/`
- Source: `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/`
- Tests: `platform/packages/digital-twin-knowledge-graph/tests/{unit,integration}/`
- Reference behavior (read, never modified by this feature — FR-012):
  `src/frictionless_architect/visualizer/{data_loader,sample_parser,namespaces}.py`,
  `src/frictionless_architect/schema/manager.py`,
  `tests/unit/visualizer/{test_data_loader,test_sample_parser,test_namespaces}.py`,
  `tests/unit/schema/test_manager.py`, `tests/integration/test_schema_manager_audit.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Stand up the package skeleton so it is installable and gated like its sibling
`platform/packages/*` packages, before any ported code lands.

- [ ] T001 Create `platform/packages/digital-twin-knowledge-graph/pyproject.toml` (package
      name `digital-twin-knowledge-graph`, `requires-python = ">=3.11,<3.14"`, `version =
      "0.0.0"` frozen placeholder per ADR-0002 Consequences, `[tool.poetry] packages = [{
      include = "digital_twin_knowledge_graph", from = "src" }]`, `[build-system]
      poetry-core>=2.0.0,<3.0.0`); dependencies: `neo4j (>=5.0,<6.0)`, `defusedxml
      (>=0.7.1,<0.8.0)`, `pydantic (>=2.0,<3.0)`, `pydantic-settings (>=2.0,<3.0)` (plan.md
      Technical Context, quickstart.md Prerequisites) — version ranges matched against what
      `platform/poetry.lock` already resolves for `defusedxml` via
      `modelling-specification`'s existing dependency.
- [ ] T002 Create `platform/packages/digital-twin-knowledge-graph/README.md` describing the
      package's purpose (`if-twin-read-path`, GH #106), its public surface (link to
      `specs/001-knowledge-graph-read-path/contracts/read-path.md`), and the explicit
      scope-boundary note that `visualizer/api.py`/`scripts/neo4j_schema.py` are not yet
      cut over (plan.md Summary).
- [ ] T003 Register the new package in `platform/pyproject.toml`: add
      `"digital-twin-knowledge-graph"` to the root `[project].dependencies` list and add
      `digital-twin-knowledge-graph = { path = "packages/digital-twin-knowledge-graph",
      develop = true }` under `[tool.poetry.dependencies]`.
- [ ] T004 Create the package's empty scaffolding: `src/digital_twin_knowledge_graph/` with
      an empty `py.typed` marker (matching `modelling-specification`'s layout), plus empty
      `tests/unit/__init__.py` and `tests/integration/__init__.py`.
- [ ] T005 From `platform/`, run `poetry lock` to refresh the shared `platform/poetry.lock`
      with the new package and its three new dependencies (`neo4j`, `defusedxml`,
      `pydantic-settings`), then `poetry install`.

**Checkpoint**: `cd platform && poetry run python -c "import digital_twin_knowledge_graph"`
succeeds (even with an empty package); `bash scripts/platform_checks.sh` no longer skips this
package for "no src/ yet" but has nothing to type-check or test yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one module every user story's code imports — connection settings — plus the
package's public export surface. MUST complete before any user story's implementation tasks.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [ ] T006 Create `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/config.py`
      with `GraphSettings(BaseSettings)` (`pydantic-settings`): fields `neo4j_uri: str = ""`,
      `neo4j_user: str = ""`, `neo4j_password: str = ""`, reading the
      `FRICTIONLESS_ARCHITECT_NEO4J_URI` / `_NEO4J_USER` / `_NEO4J_PASSWORD` env vars
      (research.md R6, data-model.md Graph Settings) — the same prefix flat-`src/`'s
      `VisualizerSettings` already uses; empty `neo4j_uri` means "no connection configured"
      (data-model.md).
- [ ] T007 [P] Create `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/__init__.py`
      exporting `GraphSettings`, `KnowledgeGraphReadPath`, `ReadPathError`, `SampleParser`,
      `ParsedSample`, `SchemaManager` (contracts/read-path.md Public surface) — placeholder
      imports, filled in as each module lands in the phases below.

**Checkpoint**: `GraphSettings()` instantiates from the environment; the package's public
import surface is declared (even if some names are not yet implemented).

---

## Phase 3: User Story 2 - Parse an ArchiMate exchange file independently of the graph (Priority: P1)

**Goal**: Turn an ArchiMate 3 Exchange Format file into a normalized, in-memory set of
elements, relationships and views, with no live graph connection (spec.md US2).

**Independent Test**: Parse `sample-data/sample-00/Test Model Full.xml` and confirm the
normalized elements/relationships/views match the file's content (quickstart.md "Validate User
Story 2"); parse a malformed or wrong-namespace file and confirm a specific error, not a
generic one.

> **Note on ordering**: User Story 2 (parser) is implemented before User Story 1 (read path)
> despite US1 being listed first in spec.md, because `SampleParser` has no dependency on
> `GraphSettings`/Neo4j and the read path's own tests benefit from a parser-produced
> `ParsedSample` fixture (data-model.md). Both remain independently testable and are still
> delivered within this plan's P1 scope.

### Tests for User Story 2

- [ ] T008 [P] [US2] Port `tests/unit/visualizer/test_namespaces.py` to
      `platform/packages/digital-twin-knowledge-graph/tests/unit/test_namespaces.py`,
      re-targeted at `digital_twin_knowledge_graph.namespaces` — same assertions
      (`ARCHIMATE_NS`, `XSI_NS`, `require_archimate_namespace()` raising
      `ArchimateNamespaceError`), unmodified expectations (FR-011).
- [ ] T009 [P] [US2] Port `tests/unit/visualizer/test_sample_parser.py` to
      `platform/packages/digital-twin-knowledge-graph/tests/unit/test_sample_parser.py`,
      re-targeted at `digital_twin_knowledge_graph.sample_parser` — same assertions covering
      well-formed parsing, duplicate-identifier-last-wins-plus-warning (FR-005), and
      no-root-element/wrong-namespace failures (FR-005), unmodified expectations (FR-011).

### Implementation for User Story 2

- [ ] T010 [P] [US2] Create `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/namespaces.py`,
      ported from `src/frictionless_architect/visualizer/namespaces.py`: `ARCHIMATE_NS =
      "http://www.opengroup.org/xsd/archimate/3.0/"`, `XSI_NS`, `ArchimateNamespaceError`,
      `require_archimate_namespace()` (behaviorally identical, FR-011).
- [ ] T011 [US2] Create `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/sample_parser.py`,
      ported from `src/frictionless_architect/visualizer/sample_parser.py`: `ParsedSample`
      dataclass (`model`, `elements`, `relationships`, `views`, `file_path`, `warnings` —
      data-model.md Parsed Sample) and `SampleParser.parse() -> ParsedSample`, calling
      `require_archimate_namespace()` first (depends on T010); duplicate element/relationship/
      view identifiers keep the last definition and append a warning rather than failing
      (FR-005); no root element or wrong namespace raises a specific error naming the problem
      (FR-005). Preserves today's ArchiMate-typed element/relationship vocabulary as this
      package's working ontology, deferring ADR-0017 reconciliation to a future increment
      (FR-015).
- [ ] T012 [US2] Update `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/__init__.py`
      to export the real `SampleParser`/`ParsedSample` from T011 in place of the T007
      placeholder.

**Checkpoint**: Run `cd platform && poetry run pytest
packages/digital-twin-knowledge-graph/tests/unit/test_namespaces.py
packages/digital-twin-knowledge-graph/tests/unit/test_sample_parser.py -v` and confirm both
pass before moving to the next phase (constitution Quality Gates: tests must pass after the
implementation of every user story, not only at the end). User Story 2 is then fully
functional and testable independently — parsing works with no Neo4j connection involved,
matching quickstart.md's US2 validation snippet.

---

## Phase 4: User Story 1 - Query the knowledge graph without touching Neo4j directly (Priority: P1) 🎯 MVP

**Goal**: A narrow, in-process read interface (`if-twin-read-path`) returning the graph's
elements, relationships and views as plain data, with no `neo4j` driver/session/record type in
its call or result (spec.md US1).

**Independent Test**: Call `KnowledgeGraphReadPath.collect()` against a populated graph and
confirm it returns elements/relationships/views as plain data (quickstart.md "Validate User
Story 1"); with no `neo4j_uri` configured, confirm it returns empty collections, not an error.

### Tests for User Story 1

- [ ] T013 [P] [US1] Port `tests/unit/visualizer/test_data_loader.py` to
      `platform/packages/digital-twin-knowledge-graph/tests/unit/test_read_path.py`,
      re-targeted at `digital_twin_knowledge_graph.read_path` (`DataLoader` →
      `KnowledgeGraphReadPath`, `DataLoaderError` → `ReadPathError`, research.md R5) — same
      assertions: empty-collections-when-unconfigured (FR-003), raises `ReadPathError` (never
      a raw `neo4j` exception type) on connection/query failure (FR-002/FR-003), unmodified
      expectations (FR-011).

### Implementation for User Story 1

- [ ] T014 [US1] Create `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/read_path.py`,
      ported from `src/frictionless_architect/visualizer/data_loader.py` with the rename
      (research.md R5): `KnowledgeGraphReadPath` (constructed from `GraphSettings`, depends on
      T006) and `ReadPathError`. `collect() -> dict[str, list[dict[str, Any]]]` keyed
      `"elements"`/`"relationships"`/`"views"`; returns empty lists for all three keys when
      `settings.neo4j_uri` is falsy (FR-003); wraps any `neo4j` driver/query failure in
      `ReadPathError` via `raise ... from exc`, never re-raising the raw driver exception
      (FR-002/FR-003, contracts/read-path.md Error contract). Add `close()`. Confine all
      `neo4j` imports to this module (research.md R3).
- [ ] T015 [US1] Update `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/__init__.py`
      to export the real `KnowledgeGraphReadPath`/`ReadPathError` from T014 in place of the
      T007 placeholder.

**Checkpoint**: Run `cd platform && poetry run pytest
packages/digital-twin-knowledge-graph/tests/unit/test_read_path.py -v` and confirm it passes
before moving to the next phase (same Quality Gates rationale as Phase 3's checkpoint). User
Stories 1 AND 2 then both work independently. This is the MVP slice per plan.md Summary — the
read path is the one piece every downstream migration step is blocked on (ADR-0005).

---

## Phase 5: User Story 3 - Ingest a model into the graph idempotently (Priority: P2)

**Goal**: Merge a parsed or payload-supplied model into the graph store such that running the
same ingestion again leaves the graph unchanged (spec.md US3).

**Independent Test**: Ingest a sample model twice in a row and confirm the graph's node/edge
counts after the second run equal the counts after the first (quickstart.md "Validate User
Story 3", SC-004).

### Tests for User Story 3

- [ ] T016 [P] [US3] Port `tests/unit/schema/test_manager.py` to
      `platform/packages/digital-twin-knowledge-graph/tests/unit/test_schema_manager.py`,
      re-targeted at `digital_twin_knowledge_graph.schema_manager.SchemaManager` — same
      assertions: `apply_constraints()` is idempotent (`IF NOT EXISTS`), `ingest()` merges by
      type and fails with a `ValueError` naming missing relationship endpoint(s) rather than
      creating a dangling edge (FR-007), `record_schema_version()` stamps a timestamped
      marker, unmodified expectations (FR-011).
- [ ] T017 [P] [US3] Port `tests/integration/test_schema_manager_audit.py` to
      `platform/packages/digital-twin-knowledge-graph/tests/integration/test_schema_manager_audit.py`,
      re-targeted at the new `SchemaManager` — same assertions: `run_audit_checks()` finds
      view/diagram relationship references with no matching graph edge and views with no
      included elements or relationship references (FR-008); re-ingesting the same payload
      leaves node/edge counts unchanged (FR-006, SC-004); needs a real Neo4j instance per
      quickstart.md, unmodified expectations (FR-011).

### Implementation for User Story 3

- [ ] T018 [US3] Create `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/schema_manager.py`,
      ported from `src/frictionless_architect/schema/manager.py`: `SchemaManager(uri, user,
      password)` with `apply_constraints()` (uniqueness constraints on `Element.identifier`,
      `View.identifier`, `Diagram.identifier`, `Viewpoint.identifier`, `SchemaVersion.name`;
      indexes on `Element.type`, `Element.layer`, `ARCHIMATE_RELATIONSHIP.identifier`,
      `ARCHIMATE_RELATIONSHIP.type`, `View.name`, `Diagram.name` — data-model.md Constraints &
      indexes table — all `IF NOT EXISTS`, idempotent); `ingest(payload)` merging
      elements/relationships/views/diagrams via `MERGE`, batched `UNWIND`-style per ADR-0006's
      ported ingestion idea (FR-010, research.md R4), checking relationship endpoint existence
      first and raising `ValueError` naming missing endpoint(s) before any edge write (FR-007);
      `run_audit_checks() -> tuple[list[dict], list[dict]]` returning
      `(missing_relationship_targets, orphan_views)` (FR-008); `record_schema_version(name)`
      stamping a timestamped `SchemaVersion` node (FR-009); `close()`. Confine all `neo4j`
      imports to this module alongside `read_path.py` (research.md R3). Attribute the ported
      business/motivation-layer vocabulary and batched-ingestion idea to ADR-0006 in a code
      comment (FR-010, SC-002).
- [ ] T019 [US3] Update `platform/packages/digital-twin-knowledge-graph/src/digital_twin_knowledge_graph/__init__.py`
      to export the real `SchemaManager` from T018 in place of the T007 placeholder — all four
      public names (`GraphSettings`, `KnowledgeGraphReadPath`, `ReadPathError`, `SampleParser`,
      `ParsedSample`, `SchemaManager`) now resolve to real implementations, matching
      contracts/read-path.md's Public surface exactly.

**Checkpoint**: Run `cd platform && poetry run pytest
packages/digital-twin-knowledge-graph/tests/unit/test_schema_manager.py -v` (plus the
integration test, T017, if a reachable Neo4j instance is available) and confirm both pass
before moving to the next phase (same Quality Gates rationale as Phases 3–4's checkpoints).
User Stories 1, 2 AND 3 then all work independently. The package can seed and read back its
own graph state end-to-end (quickstart.md's full US1→US3 sequence).

---

## Phase 6: User Story 4 - Depend on the package as an in-process library, not a service (Priority: P2)

**Goal**: Confirm the package is consumable as an ordinary Poetry path dependency with no HTTP
boundary (spec.md US4, FR-013).

**Independent Test**: Add the package as a path dependency from another `platform/packages/*`
package and call its read interface directly, with no new router, port or wire format
introduced.

- [ ] T020 [US4] Verify no FastAPI app, router, or CLI entrypoint exists anywhere under
      `platform/packages/digital-twin-knowledge-graph/src/` — confirm the package's only
      public surface is the plain Python import contract (contracts/read-path.md), matching
      the Project Structure's "no FastAPI app of its own" Structure Decision (plan.md). No new
      code; this is a structural check against what Phases 2–5 already produced.
- [ ] T021 [US4] Add `digital-twin-knowledge-graph` as a **permanent** path dependency of
      `modelling-specification` (`platform/packages/modelling-specification/pyproject.toml`,
      `[tool.poetry.dependencies]`: `digital-twin-knowledge-graph = { path =
      "../digital-twin-knowledge-graph", develop = true }`), then add a test inside
      `modelling-specification`'s own `tests/` calling
      `KnowledgeGraphReadPath(GraphSettings()).collect()` directly as an ordinary function
      call. This is the literal scenario spec.md's US4 Acceptance Scenario, FR-013 and SC-006
      describe — "another package in the `platform/` workspace... can call the read interface
      as an ordinary function call" — not an internal self-check against this package's own
      tests. **Decided**: this dependency edge is kept, not reverted — `modelling-specification`
      becomes this package's first real consumer, and plan.md's Structure Decision/deployment
      diagram are updated to document it (not left silently inaccurate). Confirm no new
      router, port, or wire format had to be introduced to make the call work, and run `poetry
      lock` from `platform/` to pick up the new cross-package edge.
- [ ] T022 [P] [US4] Add a temporary smoke test at
      `platform/packages/digital-twin-knowledge-graph/tests/unit/test_package_import.py`
      asserting `from digital_twin_knowledge_graph import GraphSettings,
      KnowledgeGraphReadPath, ReadPathError, SampleParser, ParsedSample, SchemaManager`
      succeeds and each name is importable with no network/HTTP side effect at import time
      (US4's "ordinary function call, no new wire format" requirement, SC-006).

**Checkpoint**: The package is demonstrably a library, not a service — US1–US3's checkpoints
already prove it is callable in-process; T021 proves it cross-package, not just internally;
this phase only confirms no service boundary crept in.

---

## Phase 7: User Story 5 - Build the new package's code equivalent to today's flat-`src/` behavior (Priority: P2)

**Goal**: Confirm the ported test cases pass unmodified in their expectations against the new
package's code, and that flat-`src/`'s own copies and tests remain untouched (spec.md US5,
FR-011, SC-003).

**Independent Test**: Run the new package's test suite (built from the existing modules' test
cases) against the new package's code; it passes with the same assertions those existing tests
already make, with no change to flat-`src/`'s own code or tests.

- [ ] T023 [US5] Run `cd platform && poetry run pytest packages/digital-twin-knowledge-graph/tests/unit -v`
      and confirm all ported tests (T008, T009, T013, T016, T022) pass with the same
      expectations as their flat-`src/` originals (SC-003).
- [ ] T024 [US5] Run `poetry run pytest tests/unit/visualizer/test_data_loader.py
      tests/unit/visualizer/test_sample_parser.py tests/unit/visualizer/test_namespaces.py
      tests/unit/schema/test_manager.py -v` from the repo root and confirm flat-`src/`'s own
      copies and tests pass exactly as before, with no change in behavior or imports (FR-011
      Acceptance Scenario 2) — this is a verification task only; it must not modify any
      flat-`src/` file.
- [ ] T025 [US5] Run `cd platform && poetry run pytest
      packages/digital-twin-knowledge-graph/tests/integration -v` (T017) against a real Neo4j
      instance and confirm it passes with the same assertions as its flat-`src/` original.

**Checkpoint**: All five user stories are independently functional and verified; SC-003 is
satisfied with evidence (test output), not just by inspection.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final gate compliance and documentation, once all five user stories are built and
verified.

- [ ] T026 [P] Run `cd platform && poetry run mypy packages/digital-twin-knowledge-graph/src
      packages/digital-twin-knowledge-graph/tests` and `poetry run pyright
      packages/digital-twin-knowledge-graph` and fix any type errors — `platform/pyproject.toml`
      already runs `mypy --strict`.
- [ ] T027 [P] Run `cd platform && poetry run pytest
      --cov=packages/digital-twin-knowledge-graph/src --cov-fail-under=90
      packages/digital-twin-knowledge-graph/tests` and add coverage for any public surface
      left under 90% (FR-014).
- [ ] T028 Run `bash scripts/platform_checks.sh` from the repo root end-to-end and confirm it
      no longer reports "skipped (no src/ yet)" for this package and passes its lock-check,
      pyright, mypy, and per-package 90%-coverage pytest gates.
- [ ] T029 Run `poetry run python architecture/model/build.py` from the repo root and confirm
      `VALID — no metamodel or referential-integrity violations` — this feature adds no model
      element/relationship, so the count should be unchanged from before this phase (plan.md
      Constitution Check, Principle X: "Model impact: none").
- [ ] T030 [P] Execute quickstart.md's "Validate User Story 1/2/3" snippets manually against a
      real or local Neo4j instance and confirm the documented outputs match, updating
      quickstart.md only if a documented command or snippet no longer matches the implemented
      API shape.
- [ ] T031 Run `bash scripts/pre_commit_checks.sh` from the repo root before committing, per
      AGENTS.md's mandatory fast gate (lock refresh, pymarkdown, ruff, pyright, mypy,
      tests/unit/).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001–T005) — BLOCKS all user stories (T006's
  `GraphSettings` is imported by both the read path and, indirectly, the public `__init__.py`).
- **User Story 2 (Phase 3)**: Depends on Foundational. No dependency on US1/US3 — parsing never
  touches Neo4j.
- **User Story 1 (Phase 4)**: Depends on Foundational (T006). Independent of US2/US3's code,
  though quickstart.md's end-to-end walkthrough chains US1 after US3's ingestion.
- **User Story 3 (Phase 5)**: Depends on Foundational (T006). Independent of US1/US2's code,
  though its integration test (T017) calls the read path (US1) to verify idempotent counts —
  a test-only coupling, not an implementation dependency.
- **User Story 4 (Phase 6)**: Depends on US1, US2, US3's `__init__.py` exports (T012, T015,
  T019) all being real implementations, since T021's cross-package call and T022's smoke test
  both import all six public names.
- **User Story 5 (Phase 7)**: Depends on all ported test tasks (T008, T009, T013, T016, T017,
  T022) existing and passing.
- **Polish (Phase 8)**: Depends on all prior phases.

### User Story Dependencies

- **US2 (P1)**: No dependency on other stories.
- **US1 (P1)**: No dependency on other stories' code (test-only ordering convenience with US3).
- **US3 (P2)**: No dependency on other stories' code; its integration test exercises US1's
  read path as a verification tool.
- **US4 (P2)**: Depends on US1 + US2 + US3 all being real (not placeholder) exports.
- **US5 (P2)**: Depends on every story's ported tests existing and passing.

### Within Each User Story

- Tests MUST be ported and run (and fail against the as-yet-nonexistent module) before the
  corresponding implementation task, per FR-011/SC-003's "prove equivalence" intent.
- `namespaces.py` (T010) before `sample_parser.py` (T011) — the parser calls
  `require_archimate_namespace()`.
- `config.py` (T006) before `read_path.py` (T014) and `schema_manager.py` (T018) — both take
  settings/connection parameters derived from it.
- `__init__.py` export updates (T012, T015, T019) after each story's implementation task.

### Parallel Opportunities

- T001–T002 (pyproject.toml, README.md) can run in parallel; T003–T005 depend on T001 existing.
- T007 (placeholder `__init__.py`) can run in parallel with T006.
- T008 + T009 (US2 tests) in parallel; T013 (US1 test) in parallel with either since different
  files/stories.
- T016 + T017 (US3 tests) in parallel with each other and with US1/US2 test tasks.
- T026 + T027 (mypy/pyright, coverage) and T030 (quickstart manual validation) in parallel in
  Phase 8.

---

## Parallel Example: User Story 2 + User Story 1 (both P1)

```bash
# Launch both P1 stories' test-porting tasks together (different files, no shared state):
Task: "Port test_namespaces.py to tests/unit/test_namespaces.py"
Task: "Port test_sample_parser.py to tests/unit/test_sample_parser.py"
Task: "Port test_data_loader.py to tests/unit/test_read_path.py"
```

---

## Implementation Strategy

### MVP First (User Story 2 then User Story 1)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 2 (parser) — no Neo4j needed to validate.
4. Complete Phase 4: User Story 1 (read path) — **this is the MVP**: the interface every
   downstream migration step (ARCHITECTURE.md §8.2 step 7) is blocked on (ADR-0005).
5. **STOP and VALIDATE**: run quickstart.md's US1/US2 snippets independently.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US2 (parser) → testable with no live graph → demo offline parsing.
3. US1 (read path) → MVP complete → demo against a hand-seeded graph.
4. US3 (ingestion) → the package can now seed its own graph → demo full read-after-write.
5. US4 (library-only check) → confirms no service boundary crept in.
6. US5 (equivalence verification) → confirms SC-003 with test evidence.
7. Polish → gates (mypy/pyright/coverage/`platform_checks.sh`/`build.py`) all green.

### Parallel Team Strategy

With multiple developers, once Foundational (Phase 2) is done: Developer A takes US2 (parser,
Phase 3), Developer B takes US1 (read path, Phase 4) — both are independent of each other.
US3 (Phase 5) can start alongside them, since it only depends on Foundational too. US4/US5
(Phases 6–7) wait on all three finishing their `__init__.py` export updates.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability (spec.md priorities).
- No `architecture/model/` changes in this feature — Constitution Check Principle X already
  records "Model impact: none" (plan.md); T029 is a verification task, not a modification one.
- FR-012's exclusions (no cutover of `visualizer/api.py` / `scripts/neo4j_schema.py`, no
  deletion of flat-`src/` originals) are enforced by omission: no task in this list touches
  those files except T023's read-only verification run.
- `fn-twin-ingest` and `fn-ledger-record` remain out of scope per spec.md's Scope boundary —
  no task here implements either.
- Commit after each phase checkpoint or logical group, per AGENTS.md Conventional Commits
  convention; run `bash scripts/pre_commit_checks.sh` before each commit (T031).
