# llm-provider-config

Shared package (not one of the six subsystems) that resolves which LLM
provider, model and credential a given call uses. A thin configuration layer over
`litellm` covering OpenAI, Google Gemini, Anthropic Claude and Ollama.

- Decided in [ADR-0034](../../../docs/adr/0034-shared-packages-and-llm-provider-config.md).
- Settings: a global default plus an optional per-component override.
- Secrets live in the OS keychain via `keyring`, never in a repo file or `.env`.
- First consumer: `controls-compliance-catalog`'s `llm_client.py`
  ([#76](https://github.com/wolffy-au/frictionless-architect/issues/76)).

Status: skeleton only — no settings model, credential resolution or UI yet.

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
