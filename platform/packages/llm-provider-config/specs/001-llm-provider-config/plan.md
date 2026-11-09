# Implementation Plan: LLM Provider Configuration

**Branch**: `n/a` (retroactive plan for the shipped package, matching `spec.md`) | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `platform/packages/llm-provider-config/specs/001-llm-provider-config/spec.md`

**Note**: This plan is retroactive — it describes the package as already built and tested
(ADR-0034), not a design to be implemented. Where the spec and the code agree, this plan
restates the shape briefly rather than re-deriving it; `spec.md`'s own closing Assumption
says to raise any disagreement as a finding instead of silently changing either.

## Summary

Resolve which LLM provider, model, and credential an AI feature call uses, from one
optional global default plus optional per-component overrides (ADR-0034), over `litellm`.
Settings (non-secret) live in a local TOML file outside the repo tree; API keys live in
the OS keychain via `keyring`, with a logged plaintext environment-variable fallback for
headless machines (ADR-0034 Implementation status, 2026-10-03). A mountable FastAPI
router (`create_settings_router`) serves an HTML settings page and JSON API so any
subsystem can offer the UI with one declaration and no settings code of its own.

## Technical Context

**Language/Version**: Python 3.12 (package range `>=3.11,<3.14` per the package's
`pyproject.toml`).

**Primary Dependencies**: `litellm` (the only LLM client this package resolves calls
for — ADR-0034/ADR-0044), `keyring` (OS credential store), `pydantic` v2 (settings
validation), `tomli-w` (TOML serialization; `tomllib` from the stdlib reads it back),
`fastapi` (the mountable settings router).

**Storage**: A local TOML file, `$LLM_PROVIDER_CONFIG_PATH` or
`~/.config/frictionless-architect/llm.toml` by default (`store.py`) — never inside the
repo tree, and holding no secret, only an optional `credential_ref` naming a keyring
entry. API keys live in the OS keychain (`credentials.py`); where no keychain backend is
usable, the provider's conventional environment variable is read as a logged plaintext
fallback.

**Testing**: `pytest` (`tests/unit/`, mirroring `src/llm_provider_config/`) against a
fake `litellm.completion`, an in-memory `keyring` backend, and a `FailKeyring` backend
that simulates "no usable keychain" (`tests/unit/conftest.py`). The real-Ollama,
opt-in live check (`RUN_OLLAMA_TESTS=1`) lives in the first consumer,
`controls-compliance-catalog/tests/integration/test_ollama_live.py`, not in this
package's own test tree. `scripts/platform_checks.sh` gates the package (pyright, mypy,
pytest at 90% coverage).

**Target Platform**: Runs wherever a consuming subsystem's FastAPI app runs (Linux
server today); the settings page is unauthenticated and must be bound to localhost
(ADR-0024, single-user local MVP).

**Project Type**: Monorepo shared package — `platform/packages/llm-provider-config`
(ADR-0034's "shared functionality package" category, not one of the six subsystems,
ADR-0011). Depended on by any package that calls an LLM; first consumer is
`controls-compliance-catalog`'s `llm_client.py` (component id
`controls-compliance-catalog.candidate-conversion`, GH #76).

**Performance Goals**: Resolution (`resolve_call`) is a settings-file read plus a
keychain/environment lookup — no network call — so it is well inside Principle IV's
200ms bar. "Test connection" makes one real provider round-trip and is user-initiated,
not a hot path.

**Constraints**: Never write an API key to the settings file, a repo file, or `.env`
(FR-004/FR-005); reject a secret-reference value such as `os.environ/NAME` passed as a
literal key, since `litellm`'s `get_secret` would otherwise resolve it to an arbitrary
environment variable (`credentials.py` `InvalidCredentialError`, CVE-2026-108575);
provider-error detail from a failed connection test stays in the server log, never the
HTTP response (CWE-209, FR-015). No authentication on the settings page (ADR-0024).

**Scale/Scope**: Single user, local machine (ADR-0024); five providers on day 1
(OpenAI, Gemini, Anthropic, Ollama, GitHub Copilot); one global default plus
per-component overrides keyed by an arbitrary number of host-declared component ids.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Principle | Assessment |
|---|---|
| I. Code Quality | One module per concern (`settings`/`credentials`/`resolve`/`store`/`router`), each with a single, named responsibility; no shared mutable state. No violation. |
| II. Testing Standards | Real `keyring` backends (in-memory and failing) exercise both the keychain and environment-fallback paths instead of mocking the credential layer directly; a fake `litellm.completion` isolates the provider network call. No violation. |
| III. UX Consistency | The settings page reuses the same plain-HTML/vanilla-JS pattern as the rest of the codebase's embedded-page UIs (no new framework); its JSON API follows the existing error-response convention (`HTTPException` with a `detail` message). No violation. |
| IV. Performance | `resolve_call` is a local file + keychain read, no I/O-bound wait beyond that; "Test connection" is the one network call and is explicitly user-initiated. No violation. |
| V. Security Practices | FR-004/FR-005: no key ever reaches the settings file, a repo file, `.env`, a response body, or a log line (SC-002). Every plaintext environment-variable use is logged as a warning (FR-007/SC-003). Secret-reference values are rejected on both store and use (`InvalidCredentialError`). Provider error detail is logged, never returned (CWE-209). No violation. |
| VI. State Management | Settings resolution is a pure function of stored state (`LlmSettings.resolve`): override if present, else default, else `NotConfiguredError` — no hidden intermediate state. No violation. |
| VII–IX | Not implicated — no architecture-model accuracy, durability/interoperability, or cross-platform concern beyond ordinary OS-keychain availability, which the environment-variable fallback already covers. N/A. |
| X. Decision Traceability | Decided by ADR-0034 (package + settings/credential design) and ADR-0044 (the `litellm` dependency's own model element). See Model Impact below. |
| XI. Concise Spec Artefacts | This plan restates `spec.md`'s requirements only where needed for Technical Context/Constitution Check; ADR-0034's "Implementation status" section remains the one place implementation choices (file paths, env var names) are recorded in detail. |

**Gate result**: PASS, no violations, no Complexity Tracking entries needed.

## Model Impact

**None** — `sub-llm-provider-config` (`ApplicationComponent`) and `sw-litellm`
(`SystemSoftware`, wired to it by a `Serving` relationship) already exist in
`architecture/model/elements.yaml`, added for this exact package by ADR-0034 and
ADR-0044. This plan documents the package's existing implementation without adding,
changing, or retiring any element, relationship, or view id.

## Project Structure

### Documentation (this feature)

```text
platform/packages/llm-provider-config/specs/001-llm-provider-config/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── api.md            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (`platform/packages/llm-provider-config/`)

```text
src/llm_provider_config/
├── __init__.py          # Public re-exports
├── settings.py          # Provider enum, ProviderSettings/LlmSettings models, resolve()
├── credentials.py       # Keyring-first, env-fallback key lookup; secret-reference rejection
├── resolve.py           # resolve_call(): settings + credential -> litellm.completion kwargs
├── store.py             # TOML settings file read/write, outside the repo tree
└── router.py            # create_settings_router(): HTML page + JSON API

tests/
└── unit/                # mirrors src/llm_provider_config/, one test module per production module
```

**Structure Decision**: One flat module per concern, matching the package's small
surface area — no `api/`, `services/`, or `models/` subpackages, since each module
already has a single responsibility and the package has no internal layering to
express. The settings router is consumed by mounting it in a host app
(`app.include_router(create_settings_router(...))`), not by this package running its
own `app.py` — it has no standalone entry point, consistent with ADR-0034's "mountable
router" decision.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
