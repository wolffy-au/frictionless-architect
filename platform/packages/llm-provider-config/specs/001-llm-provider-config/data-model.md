# Data Model for LLM Provider Configuration

## Provider

- **Description:** The five LLM providers the package supports on day 1
  (`settings.py` `Provider(StrEnum)`).
- **Values:** `openai`, `gemini`, `anthropic`, `ollama`, `github_copilot`.
- **Validation:** Any other value is rejected by Pydantic enum validation (FR-001).

## ProviderSettings

- **Description:** Provider, model, and call parameters for one configuration slot
  (either the global default or one component's override). Never holds a secret.
- **Fields:** `provider` (`Provider`), `model` (string, `min_length=1`), `params` (free-form
  dict, default `{}`), `api_base` (optional string), `credential_ref` (optional string —
  the keyring entry name; defaults to the provider name when unset).
- **Validation:** `extra="forbid"` rejects unknown fields (FR-003); `frozen=True` —
  an instance is replaced, not mutated.

## LlmSettings

- **Description:** The whole settings file's content: one optional global default plus
  per-component overrides.
- **Fields:** `default` (`ProviderSettings | None`), `components` (dict of component id
  → `ProviderSettings`, default `{}`).
- **Validation:** `extra="forbid"` rejects unknown top-level fields.
- **Behaviour:** `resolve(component)` returns the component's override if present, else
  `default`, else raises `NotConfiguredError` (FR-002).

## Component

- **Description:** An AI feature a host package declares when it mounts the settings
  router (`router.py`), not persisted — supplied by the caller at mount time.
- **Fields:** `id` (string, the override key), `label` (string, display name).

## Resolved call (`ResolvedCall`)

- **Description:** Everything `litellm.completion` needs besides the chat messages,
  produced by `resolve_call(component)`.
- **Fields:** `model` (the `"<litellm-prefix>/<model>"` string), `api_key` (optional —
  `None` for keyless providers), `api_base` (optional), `params` (dict, copied from the
  resolved `ProviderSettings`).
- **Behaviour:** `completion_kwargs()` flattens this into the keyword arguments
  `litellm.completion` takes, omitting `api_key`/`api_base` when unset.

## Key source (reporting only, never the key itself)

- **Description:** Where `get_api_key` would find a provider's key, returned by
  `key_source(settings)` for display on the settings page (FR-006).
- **Values:** `not-needed` (Ollama, GitHub Copilot), `keychain`, `environment`,
  `missing`.
