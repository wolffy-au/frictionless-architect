---

description: "Task list for the LLM provider configuration package (retroactive, ADR-0034)"
---

# Tasks: LLM Provider Configuration

**Input**: Design documents from `platform/packages/llm-provider-config/specs/001-llm-provider-config/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included — this is retroactive documentation of an already-built, already-tested
package; each task cites the existing test(s) that cover it rather than describing tests
still to write.

**Organization**: Grouped by the five user stories in spec.md (US1–US5), after one
Foundational phase they all depend on.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Maps to spec.md's US1–US5
- File paths are exact and relative to the repository root

## Phase 1: Setup

- [X] T001 Package scaffold: `platform/packages/llm-provider-config/pyproject.toml`
  (dependencies `litellm`, `keyring`, `pydantic`, `tomli-w`, `fastapi`), `src/llm_provider_config/`,
  `tests/unit/`, `README.md`, added to the shared `platform/poetry.lock` (ADR-0002).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The settings model and storage every user story resolves against.

**⚠️ CRITICAL**: All user story phases below depend on this phase.

- [X] T002 [P] `Provider` enum (`openai`, `gemini`, `anthropic`, `ollama`, `github_copilot`)
  and `KEYLESS_PROVIDERS` in `platform/packages/llm-provider-config/src/llm_provider_config/settings.py`
  (FR-001). Covered by `tests/unit/test_settings.py::test_unknown_provider_is_rejected`.
- [X] T003 [P] `ProviderSettings` model (`provider`, `model: str = Field(min_length=1)`,
  `params: dict = {}`, `api_base: str | None`, `credential_ref: str | None`), `extra="forbid"`,
  `frozen=True` in `settings.py` (FR-003). Covered by
  `tests/unit/test_settings.py::test_empty_model_is_rejected`,
  `test_secret_fields_are_not_part_of_the_model`.
- [X] T004 [US1][US4] `LlmSettings` model (`default`, `components: dict[str, ProviderSettings]`)
  and `resolve(component)` — override if present, else default, else `NotConfiguredError`
  (FR-002) in `settings.py`. Covered by
  `tests/unit/test_settings.py::test_resolve_uses_the_component_override_when_present`,
  `test_resolve_falls_back_to_the_global_default`, `test_resolve_raises_when_nothing_applies`,
  `test_resolve_ignores_other_components_overrides_without_a_default`.
- [X] T005 [P] Settings file read/write — `default_config_path()`
  (`$LLM_PROVIDER_CONFIG_PATH` else `~/.config/frictionless-architect/llm.toml`),
  `load_settings()` (missing file → empty `LlmSettings`), `save_settings()` (best-effort
  `0600`, parent dirs created) in
  `platform/packages/llm-provider-config/src/llm_provider_config/store.py` (FR-004, FR-012).
  Covered by `tests/unit/test_store.py` (all cases, including
  `test_save_survives_a_filesystem_that_refuses_chmod` for drvfs-style mounts).

**Checkpoint**: Settings can be resolved and persisted; every user story below builds on this.

---

## Phase 3: User Story 1 - Choose a provider and model once for every AI feature (Priority: P1) 🎯 MVP

**Goal**: One global default, used by every AI feature that doesn't override it (spec.md
FR-002, FR-003, FR-011).

**Independent Test**: Save a default through the settings page, then ask for the call
details of any component; they name the chosen provider, model and parameters.

- [X] T006 [US1] `PUT /default` route — loads current settings, replaces `default`, keeps
  existing `components` — in
  `platform/packages/llm-provider-config/src/llm_provider_config/router.py`
  (`_settings_routes`). Covered by
  `tests/unit/test_router.py::test_default_and_override_round_trip`.
- [X] T007 [US1] `GET /state` route returns `default` (via `_describe`, with `key_source`,
  never the key) and the provider list in `router.py`. Covered by
  `tests/unit/test_router.py::test_state_starts_empty`.
- [X] T008 [US1] Reject an unsupported provider, empty model or unknown field on save, with
  no change to stored state — FastAPI/Pydantic validation on `ProviderSettings` (FR-003,
  FR-011, SC-004). Covered by
  `tests/unit/test_router.py::test_invalid_settings_are_rejected`.
- [X] T009 [US1] `resolve_call(component)` turns the resolved `ProviderSettings` into
  `ResolvedCall` (`model`, `api_key`, `api_base`, `params`) in
  `platform/packages/llm-provider-config/src/llm_provider_config/resolve.py` (FR-013).
  Covered by `tests/unit/test_resolve.py::test_openai_call_carries_prefixed_model_key_and_params`,
  `test_each_provider_gets_its_litellm_prefix`.

**Checkpoint**: A saved global default resolves for any component with no override.

---

## Phase 4: User Story 2 - Store an API key without it touching the repository (Priority: P1)

**Goal**: Keys go to the OS keychain, never a file or a response (FR-004, FR-005, FR-009,
SC-002).

**Independent Test**: Store a key, then read every service response and the settings
file; the key appears in none of them, yet an AI feature can still use it.

- [X] T010 [US2] `set_api_key`/`get_api_key`/`delete_api_key` over `keyring`, keyed by
  `SERVICE_NAME` + `credential_ref`-or-provider-name, in
  `platform/packages/llm-provider-config/src/llm_provider_config/credentials.py`. Covered by
  `tests/unit/test_credentials.py::test_keychain_entry_is_returned`,
  `test_credential_ref_selects_a_different_keychain_entry`, `test_delete_removes_the_keychain_entry`.
- [X] T011 [US2] `PUT /keys/{provider}` (`422` for a keyless provider) and
  `DELETE /keys/{provider}` (`404` when absent) routes in `router.py` (`_key_routes`)
  (FR-009). Covered by
  `tests/unit/test_router.py::test_key_is_stored_in_keychain_and_never_returned`,
  `test_ollama_key_is_refused`, `test_copilot_key_is_refused_and_needs_none`.
- [X] T012 [US2] `key_source(settings)` reports `not-needed`/`keychain`/`environment`/`missing`
  without ever returning the key, used by `/state` (FR-006). Covered by
  `tests/unit/test_router.py::test_key_source_reports_environment`.
- [X] T013 [US2] Settings file never carries key material — `ProviderSettings` has no key
  field, only `credential_ref` (FR-004, SC-002). Covered by
  `tests/unit/test_store.py::test_saved_file_contains_no_secret_material`.
- [X] T014 [US2] Reject a blank key — `KeyBody.api_key: str = Field(min_length=1)` in
  `router.py` (FR-009).

**Checkpoint**: Keys round-trip through the keychain only; nothing persisted carries one.

---

## Phase 5: User Story 3 - Run on a machine with no credential store (Priority: P2)

**Goal**: A labelled environment-variable fallback keeps AI features working headless
(FR-007, FR-008, FR-010, SC-003, SC-005).

**Independent Test**: Remove the credential store, set only the environment variable,
and resolve a call; it succeeds and a warning that a plaintext key was used is logged.

- [X] T015 [US3] `ENV_VARS` table (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`)
  and the keychain-first-then-environment fallback with a logged warning in
  `get_api_key` (`credentials.py`) (FR-007). Covered by
  `tests/unit/test_credentials.py::test_environment_fallback_is_used_and_warned_about_when_the_entry_is_absent`,
  `test_environment_fallback_works_when_no_keychain_backend_exists`,
  `test_keychain_wins_over_the_environment`.
- [X] T016 [US3] `MissingCredentialError`, naming both remedies, when neither source has a
  key (FR-008). Covered by
  `tests/unit/test_credentials.py::test_missing_everywhere_raises_with_both_remedies_named`.
- [X] T017 [US3] `503` on `PUT /keys/{provider}` naming the environment variable when no
  keychain backend exists, instead of a stored-key error (FR-010). Covered by
  `tests/unit/test_router.py::test_key_without_keychain_points_at_env_var`.
- [X] T018 [US3] Reject a secret-reference value (`os.environ/...`) passed as a literal key,
  on both store and use — `InvalidCredentialError`, CVE-2026-108575 — in `credentials.py`.
  Covered by `tests/unit/test_credentials.py::test_set_refuses_a_secret_reference`,
  `test_get_refuses_a_secret_reference_already_in_the_keychain`,
  `test_get_refuses_a_secret_reference_in_the_environment`,
  `test_a_refused_reference_is_still_a_missing_credential`, and
  `tests/unit/test_router.py::test_secret_reference_key_is_refused_and_not_stored`.

**Checkpoint**: The package works end to end with only an environment variable set.

---

## Phase 6: User Story 4 - Override the provider for one feature and test it (Priority: P2)

**Goal**: A per-component override plus a connection test that never crashes the caller
(FR-002, FR-015).

**Independent Test**: Save an override for one component; that component resolves to it,
others keep the default, and "Test connection" reports success or the provider's failure.

- [X] T019 [US4] `PUT /components/{component_id}` (`404` for an unknown component) and
  `DELETE /components/{component_id}` routes in `router.py` (`_settings_routes`).
  Covered by `tests/unit/test_router.py::test_default_and_override_round_trip`,
  `test_unknown_component_is_rejected`.
- [X] T020 [US4] `resolve_call` honours a component override over the default. Covered by
  `tests/unit/test_resolve.py::test_component_override_beats_the_default`,
  `test_unconfigured_component_raises`, `test_missing_credential_surfaces`.
- [X] T021 [US4] `POST /test` — a one-word `litellm.completion` call against the resolved
  settings (global default when `component` is omitted), returning `{ok, message}` for
  every outcome (not-configured, missing credential, provider failure, success); provider
  error detail stays in the server log, never the response (CWE-209) — `_test_route` in
  `router.py` (FR-015). Covered by
  `tests/unit/test_router.py::test_connection_test_reports_not_configured`,
  `test_connection_test_reports_missing_credential`,
  `test_connection_test_success_and_failure`,
  `test_default_connection_test_ignores_component_overrides`.

**Checkpoint**: Overrides and the connection test both work independently of the default.

---

## Phase 7: User Story 5 - Mount the settings page in any subsystem (Priority: P3)

**Goal**: A host package adds the settings page/API by declaring its own components, with
no settings code of its own (FR-014).

**Independent Test**: Mount the router with two declared components and confirm the page
lists exactly those.

- [X] T022 [US5] `create_settings_router(components, prefix="/settings/llm")` builds an
  `APIRouter` scoped to the given components and prefix, serving the HTML page at the
  prefix itself (`router.py`). Covered by
  `tests/unit/test_router.py::test_page_is_served_with_prefix`.
- [ ] T023 [US5] **Gap found, not fixed here**: no test mounts the router with *more than
  one* declared component and asserts `/state`'s `components` list contains exactly the
  declared set (no extras, no omissions) — every existing `test_router.py` case uses the
  single-component `COMPONENT` fixture (`tests/unit/test_router.py:12,20`). The code
  (`known = {c.id: c for c in components}`, and `/state`'s `components` built directly
  from the passed-in sequence) looks correct by inspection, but US5's own stated
  Independent Test ("declare two components, confirm the page lists exactly those") is not
  exercised. Add a test with ≥2 components to close this before marking US5 fully verified.

**Checkpoint**: A host can mount the page/API with its own component list — T023 is the one
open item.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T024 [P] Module docstrings state the ADR-0034 decision each module implements
  (`settings.py`, `credentials.py`, `resolve.py`, `store.py`, `router.py`).
- [X] T025 [P] `tests/unit/test_llm_provider_config_package.py` asserts the public
  `__all__` re-export surface (`__init__.py`) stays in sync with what consumers actually
  import (`resolve_call`, `LlmSettings`, `Component`, `create_settings_router`, etc.).
- [X] T026 First consumer wired: `controls-compliance-catalog`'s `llm_client.py` calls
  `resolve_call("controls-compliance-catalog.candidate-conversion")` instead of owning a
  single hardcoded call shape (ADR-0034 Consequences).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — blocks every user story.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on Foundational only; independent of US1.
- **User Story 3 (Phase 5)**: Depends on Foundational and on `credentials.py` existing
  (Phase 4's T010), since it extends the same lookup with the environment fallback.
- **User Story 4 (Phase 6)**: Depends on Foundational (component resolution, T004) and on
  US2's key lookup (T010) for the connection test's credential path.
- **User Story 5 (Phase 7)**: Depends on Foundational; independent of US1–US4's specific
  routes, since it only concerns how the router is parameterised and mounted.
- **Polish (Phase 8)**: Depends on all user stories.

### Parallel Opportunities

- T002/T003 (different concerns, same file but non-overlapping classes) and T005
  (different file) can be reviewed in parallel.
- T024/T025 are independent, different-file polish tasks.

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 → Phase 2 (Foundational) → Phase 3 (US1).
2. **Stop and validate**: a saved global default resolves for any component.
3. This alone already lets one AI feature run against a configured provider.

### Full Package (as shipped)

4. Phases 4–7 (US2–US5) add key storage, the headless fallback, overrides with a
   connection test, and the mountable multi-component router.
5. Phase 8 (Polish): close T023, then re-run `scripts/platform_checks.sh`.
