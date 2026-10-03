# llm-provider-config

Shared package (not one of the six subsystems) that resolves which LLM
provider, model and credential a given call uses. A thin configuration layer over
`litellm` covering OpenAI, Google Gemini, Anthropic Claude, Ollama and GitHub Copilot.

- Decided in [ADR-0034](../../../docs/adr/0034-shared-packages-and-llm-provider-config.md).
- Settings: a global default plus an optional per-component override.
- Secrets live in the OS keychain via `keyring`, never in a repo file or `.env`.
- First consumer: `controls-compliance-catalog`'s `llm_client.py`
  ([#76](https://github.com/wolffy-au/frictionless-architect/issues/76)).

## Usage

```python
from llm_provider_config import resolve_call
import litellm

call = resolve_call("controls-compliance-catalog.candidate-conversion")
litellm.completion(messages=[...], **call.completion_kwargs())
```

- **Settings** live in `~/.config/frictionless-architect/llm.toml` (override with
  `LLM_PROVIDER_CONFIG_PATH`): a `[default]` provider/model plus optional
  `[components."<id>"]` overrides. They never hold a key, only an optional
  `credential_ref` naming the keyring entry.
- **Keys** come from the OS keychain (`set_api_key`). Where there is no keychain
  backend, or no entry, the provider's environment variable (`OPENAI_API_KEY`,
  `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`) is used as a plaintext escape hatch, with a
  logged warning. Ollama needs no key. GitHub Copilot (`github_copilot/<model>`) needs none either: litellm runs GitHub's device-flow sign-in on first use and caches the token under `~/.config/litellm/github_copilot/`, so sign in once from a terminal before using it from the UI.

### Settings page

`create_settings_router([Component(id=..., label=...)])` returns a FastAPI router serving a
settings page at `/settings/llm` (plus a JSON API under it). Mount it in any subsystem UI,
declaring the components that use an LLM:

```python
app.include_router(create_settings_router([Component(id="my-pkg.feature", label="My feature")]))
```

The page edits the global default, per-component overrides, and API keys (written to the OS
keychain, never returned), and has a "Test connection" button. There is no authentication
(single-user local MVP, ADR-0024), so bind to localhost.

Status: settings model, storage, credential resolution, `resolve_call` and the settings
router are in.

## Development

From `platform/` (one shared lock for every package — ADR-0002):

```bash
poetry install
poetry run pytest packages/llm-provider-config/tests
```

`bash scripts/platform_checks.sh` from the repo root runs the full package gate.

## Layout

- `src/llm_provider_config/` — the package.
- `tests/` — its tests, mirroring `src/`.
- `specs/` — this package's feature specs (`ARCHITECTURE.md` §6).
