# Research Tasks

Retroactive: these are the decisions already made and shipped (ADR-0034), recorded in
the format this phase expects rather than as open unknowns. No `NEEDS CLARIFICATION`
items remain in Technical Context.

## Settings storage format and location

**Decision:** A local TOML file at `$LLM_PROVIDER_CONFIG_PATH` or
`~/.config/frictionless-architect/llm.toml` by default, validated through the
`LlmSettings` Pydantic model (`extra="forbid"`), written best-effort `0600`.

**Rationale:** Keeps settings outside the repo tree (FR-004) without inventing a new
format; `tomllib`/`tomli-w` are already used elsewhere in the codebase's config layer.
Pydantic's `extra="forbid"` gives FR-003's "unknown fields MUST be rejected" for free.

**Alternatives considered:** JSON (no comments, no real advantage over TOML here);
embedding settings in an existing app's own config file (rejected — this package is
shared across subsystems, ADR-0034, so it needs a location independent of any one
consumer).

## Secret storage and the headless fallback

**Decision:** OS keychain via `keyring` first (`SERVICE_NAME` +
`credential_ref`-or-provider-name as the keyring username); where no backend is usable
or the entry is absent, fall back to the provider's conventional environment variable
(`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`), logged as a warning each use.
A stored key always wins over the environment variable when both are set.

**Rationale:** ADR-0034 rejected `.env`/plaintext files outright (Security Practices).
The OS keychain is the correct store for a single local user with no new crypto code to
maintain; the environment-variable fallback is the only way the package still works on
the project's own CI/devcontainer, which has no keychain backend.

**Alternatives considered:** App-managed encrypted file (Fernet-style) — rejected, a
second secret (the master key) to protect; external secrets manager (Vault/cloud) —
rejected as unjustified operational overhead for ADR-0024's single-user local MVP.

## Rejecting secret references passed as literal keys

**Decision:** Reject any key value starting with `os.environ/` on both store and use
(`InvalidCredentialError`).

**Rationale:** `litellm` resolves an `api_key` value shaped like `os.environ/NAME` to
that environment variable internally (`get_secret`, CVE-2026-108575). Without this
check, a key submitted through the settings page could make the server read an
arbitrary environment variable it was never meant to expose.

**Alternatives considered:** None — this is a security fix for a specific, named CVE,
not a design trade-off.

## Provider-to-litellm model string mapping

**Decision:** A fixed `Provider -> litellm` prefix table (`openai`, `gemini`,
`anthropic`, `ollama_chat`, `github_copilot`); Ollama gets a default local API base
(`http://localhost:11434`) when none is set.

**Rationale:** `litellm` dispatches on a `"<prefix>/<model>"` string; five providers on
day 1 (FR-001) is small enough for a static table rather than a provider-plugin
mechanism, which would be unjustified complexity for a fixed, known set.

**Alternatives considered:** A provider-plugin/registry abstraction — rejected, no
second provider implementation pattern exists yet to generalize from (Principle I,
avoid speculative abstraction).

## Settings-page delivery shape

**Decision:** A mountable `APIRouter` (`create_settings_router`) serving one HTML page
(vanilla JS, no framework/build step) plus a JSON API beneath the same prefix, mounted
by whichever host app declares the LLM-using components.

**Rationale:** ADR-0020 rules out a central dashboard; the existing
`controls-compliance-catalog` playground already established the "mounted router"
pattern this package reuses, keeping the UI approach consistent across packages
(Principle III).

**Alternatives considered:** A standalone settings service/app — rejected, adds a
process and a port for a page every consumer already has a FastAPI app to mount it in.
