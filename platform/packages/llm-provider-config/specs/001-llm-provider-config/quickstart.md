# Quickstart: LLM Provider Configuration

## Prerequisites

1. Python 3.12 and the platform's dependencies (`cd platform && poetry install`).
2. An OS credential-store backend for the full path (macOS Keychain, Windows
   Credential Manager, or a Linux Secret Service implementation). Without one, the
   package still works via the environment-variable fallback (US3) — skip straight to
   "Headless / no-keychain path" below.
3. (Optional, for a real provider round-trip) A reachable Ollama at
   `http://localhost:11434`, or an API key for OpenAI/Gemini/Anthropic.

## Mount the settings router

```python
from fastapi import FastAPI
from llm_provider_config import Component, create_settings_router

app = FastAPI()
app.include_router(create_settings_router([
    Component(id="my-pkg.my-feature", label="My feature"),
]))
```

Run it:

```bash
poetry run uvicorn my_pkg.app:app --reload --port 8100
```

Bind to `localhost` only — the page has no authentication (ADR-0024).

## Validate the primary path (US1, US2)

1. Open `http://127.0.0.1:8100/settings/llm`. The "Global default" section is empty
   (`GET /state` returns `default: null`).
2. Pick a provider and model, click **Save**. `GET /state` now returns that default
   for every component with no override (FR-002, SC-001).
3. Paste an API key into that provider's field under "API keys" and click **Store**.
   The page shows "Stored in keychain." — check the response of `GET /state` and the
   settings file (`cat ~/.config/frictionless-architect/llm.toml`): neither contains
   the key (FR-005, SC-002).
4. Click **Test connection** on the default. It reports success or a readable failure
   message, never a raw exception (FR-015).

## Validate the headless / no-keychain path (US3)

```bash
unset LLM_PROVIDER_CONFIG_PATH
export OPENAI_API_KEY=sk-...   # or GEMINI_API_KEY / ANTHROPIC_API_KEY
poetry run python -c "
from llm_provider_config import resolve_call
print(resolve_call('my-pkg.my-feature').completion_kwargs())
"
```

With no keychain entry stored, this resolves the key from the environment variable
and logs a warning (FR-007, SC-003). Store a key through the settings page afterward
and re-run: the stored key now wins (US3 AC2).

## Validate a per-component override (US4)

1. Declare a second component when mounting the router (or reuse one already
   declared) and save an override for it on the settings page.
2. `resolve_call("that-component-id")` returns the override; every other component
   still resolves to the global default (US4 AC1).
3. Remove the override; the component falls back to the default (US4 AC2).

## Run the test suite

```bash
cd platform
poetry run pytest packages/llm-provider-config/tests
```

A real-Ollama live check exists in the first consumer package, not here: see
`controls-compliance-catalog/tests/integration/test_ollama_live.py`
(`RUN_OLLAMA_TESTS=1`). See `contracts/api.md` for the full request/response shape of
each endpoint exercised above.
