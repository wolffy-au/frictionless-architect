---

description: "Task list for the Neo4j Schema Visualiser feature"
---

# Tasks: Neo4j Schema Visualiser

**Input**: plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/api.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the visualiser module, static assets, and configuration wiring for the FastAPI service.

- [ ] T001 [P] Create `src/frictionless_architect/visualizer/__init__.py` with a FastAPI router that mounts the schema visualiser endpoints and exposes the static/template directories.
- [ ] T002 [P] Add `src/frictionless_architect/visualizer/config.py` to read Neo4j credentials, cache paths, sample-data location, and warning text from `.env` (per quickstart).
- [ ] T003 [P] Create `src/frictionless_architect/visualizer/static/schema_visualizer.js` and `.../templates/schema_visualizer.html` to host the cytoscape diagram, table view, refresh button, status message, and non-blocking warning banner mentioned in the spec.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement services that load Neo4j/schema metadata, parse the enhanced sample, cache aggregated JSON, and expose the API payloads before user stories begin.

- [ ] T004 [P] Build `src/frictionless_architect/visualizer/sample_parser.py` to parse `sample-data/sample-00/Test Model Full.xml`, extracting elements, relationships, views, node bounds, and diagram connections.
- [ ] T005 [P] Build `src/frictionless_architect/visualizer/data_loader.py` that connects to Neo4j, collects elements/relationships/views (including schema source file references), merges them with parsed sample data, records `latency_ms`, warnings, and data-source statuses.
- [ ] T006 [P] Implement `src/frictionless_architect/visualizer/cache.py` to persist the aggregated payload into `.cache/visualiser/schema_payload.json` and read it when Neo4j/sample data are unavailable.
- [ ] T007 [P] Implement `src/frictionless_architect/visualizer/api.py` controllers for `/schema-payload`, `/schema-payload/refresh`, and `/schema-payload/status` per the contract, using the loader/cache modules, honoring refresh guards, and surfacing warnings/backoff metadata.

---

## Phase 3: User Story 1 - Schema Exploration (Priority: P1)

**Goal**: Show analysts every schema entity with at least one sample instance, highlight coverage gaps, and keep schema summary visible even when sample data is missing.

**Independent Test**: `/schema-payload` returns element/relationship arrays containing `source_file`, sample instances, coverage warnings, and `warnings` includes "Sample data unavailable" when needed per FR-006.

- [ ] T008 [P] [US1] Create `tests/api/test_schema_payload.py` that asserts `/schema-payload` returns element/relationship metadata, includes sample instance identifiers, and populates `warnings` when `Test Model Full.xml` or Neo4j is unavailable.
- [ ] T009 [US1] Update `src/frictionless_architect/visualizer/static/schema_visualizer.js` to render the schema summary, table of elements, coverage badges, and warning banner text, fetching `/schema-payload` and `/schema-payload/status` per the quickstart workflow.
- [ ] T010 [US1] Refine `schema_visualizer.html` and the JS bundle so selecting a relationship/element highlights the connection and displays source/target identifiers, matching FR-002/FR-005.

---

## Phase 4: User Story 2 - Model Assurance (Priority: P2)

**Goal**: Provide product owners a diagram/table parity view that reuses the same payload, ensuring the same attributes and layouts are shown across views for Principle IX.

**Independent Test**: The diagram/table pulls from the same dataset (identical element/relationship counts and attribute lists) returned by `/schema-payload`.

- [ ] T011 [P] [US2] Create `tests/api/test_schema_view_consistency.py` that validates `/schema-payload` contains matching element/relationship data for both diagram nodes and table rows, including layout bounds from `Test Model Full.xml`.
- [ ] T012 [US2] Extend `schema_visualizer.js` to build the cytoscape diagram from the `views` payload, respecting stored x/y/w/h bounds, and toggle between the diagram and table while showing identical metadata (identifier, label, source file) per FR-003.
- [ ] T013 [US2] Update `templates/schema_visualizer.html` plus CSS to support switching between diagram and table views while keeping the schema list visible and consistent.

---

## Phase 5: User Story 3 - Sample Verification (Priority: P3)

**Goal**: Allow reviewers to refresh the cached payload, see cache freshness, and keep schema overview available during retries.

**Independent Test**: `/schema-payload/status` reports `cache_age_seconds`, `neo4j_status`, `sample_file_status`, and `/schema-payload/refresh` responds with `refresh_started` while respecting the 5-minute retry requirement.

- [ ] T014 [US3] Create `tests/api/test_schema_status.py` asserting `/schema-payload/status` returns freshness/warning metadata and POST `/schema-payload/refresh` returns 202 when idle and 409 if a refresh is running.
- [ ] T015 [US3] Enhance `api.py` so `/schema-payload/refresh` triggers a background rebuild, `/schema-payload/status` reflects cache age/connection state, and both honor the retry/backoff rules from the spec.
- [ ] T016 [US3] Add a refresh control, warning banner state, and status indicator to `schema_visualizer.js`/`schema_visualizer.html` that calls `/refresh` and `/status`, displays “Sample data unavailable,” and keeps the schema list accessible per FR-006.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Document the feature, validate quickstart steps, and highlight the new visualiser in repository docs.

- [ ] T017 [P] Update `specs/002-neo4j-schema-ui/quickstart.md` to capture the commands, env vars, access expectations, and warning text discovered while implementing the feature.
- [ ] T018 [P] Run lint/tests (`ruff`, `pytest tests/api`) and ensure `README.md` or developer docs mention the schema visualiser entry point along with the “Sample data unavailable” warning text.

---

## Dependencies & Execution Order

### Phase Dependencies
- Setup (Phase 1) must finish before Foundational Phase 2.
- Foundational Phase 2 blocks all User Story phases until the loader/cache/API layers exist.
- Each User Story phase (Phase 3–5) depends on Phase 2 but is otherwise independent and can run in parallel once the foundational modules are ready.
- Polish (Phase 6) depends on all user stories completing.

### User Story Dependencies
- US1 (P1) can start once Phase 2 finishes and does not depend on other stories.
- US2 (P2) also follows Phase 2 and can run parallel to US1 provided the API payload is stable.
- US3 (P3) likewise depends on Phase 2; refresh/status endpoints reuse the shared cache layer.

### Within Each User Story
- Tests (if included) should be written first and fail before implementation.
- UI tweaks depend on the JS/static files defined in Phase 1.
- Story-specific implementation (files under `visualizer/`) should not conflict to maintain parallel work.

### Parallel Opportunities
- Setup tasks T001-T003 (distinct files) are marked [P].
- Foundational tasks T004-T007 operate in different modules and can run concurrently.
- Tests for each story can be written while the UI code for that story is in progress.

## Implementation Strategy
1. **MVP First**: Complete Phases 1–2 plus Phase 3 (US1) to verify schema coverage, sample warnings, and base endpoints.
2. **Incremental Delivery**: Add Phase 4 (US2) and Phase 5 (US3) with their tests before finalizing Phase 6.
3. **Parallel Delivery**: With multiple contributors, assign foundational APIs to one developer while another works on UI tests for US1, etc.
