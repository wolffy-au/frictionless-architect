# ADR-0034: Shared cross-subsystem functionality packages; first instance is LLM provider configuration

- **Status:** Accepted
- **Date:** 2026-10-03
- **Sources:** GH #76 (control conversion playground) follow-up discussion; ADR-0002
  (Poetry monorepo); ADR-0024 (single-user local MVP); ADR-0014 (PII anonymization
  gateway); `platform/packages/controls-compliance-catalog/src/controls_compliance_catalog/llm_client.py`
  (existing single-provider stub, spec `001-oscal-ai-conversion` research.md R2)

## Context

`controls-compliance-catalog`'s `llm_client.py` is a narrow, package-local stub
(one `convert_chunk` call shape, no provider selection) built because no LLM
client existed anywhere in the codebase yet (spec `001-oscal-ai-conversion`
research.md R2). GH #76's one remaining acceptance criterion needs it wired to
a real provider. At the same time, the need is **not specific to this
package**: multiple subsystems will eventually call an LLM, each potentially
wanting a different provider/model, while the user also wants one place to set
sane defaults across the whole tool. Day 1 must cover OpenAI, Google Gemini,
Anthropic Claude, and Ollama.

Two problems compound:

1. **Where does functionality shared by more than one subsystem package live?**
   ADR-0002 establishes the monorepo and path-dependency mechanism for
   first-party packages, but every package named in `ARCHITECTURE.md` so far is
   a subsystem (ADR-0011) or a vendored fork. There is no stated place for a
   small package that exists purely to be depended on by others.
2. **How are provider API keys stored?** `.env`/environment variables put
   plaintext secrets in a file sitting in the repo tree, with no access control
   beyond filesystem permissions — rejected by the maintainer as insufficiently
   secure even for a local MVP.

## Decision

### Shared functionality packages (general pattern)

A capability needed by more than one subsystem package gets its own sibling
package under `platform/packages/<name>/`, built and gated exactly like a
subsystem package (own `pyproject.toml`, `src/`, `tests/`, `README.md`,
`specs/`; shared `platform/poetry.lock`; path-dependency per ADR-0002), but it
is **not** one of the six subsystems (ADR-0011) and carries no subsystem UI
obligation (ADR-0020). Consuming packages add it as a normal path dependency.
There is no single catch-all `common` package — each shared concern gets its
own named package, the same granularity rule already applied to subsystems, so
dependents only pull in what they actually use.

### LLM provider configuration (first instance): `platform/packages/llm-provider-config`

- **Scope:** a thin configuration and credential-resolution layer over
  `litellm` (already the chosen client library, ADR-adjacent to spec `001`
  research.md R2) covering OpenAI, Google Gemini, Anthropic Claude, and Ollama
  on day 1. It resolves "which provider/model/params to use for call X" and
  "what credential goes with it" — it does not wrap or replace `litellm`'s own
  call surface.
- **Settings model:** a global default (provider, model id, and optional
  provider params) plus an optional **per-component override**, keyed by a
  component identifier each consuming package declares (e.g.
  `controls-compliance-catalog.candidate-conversion`). Resolution is
  "component override if present, else global default" — no deeper
  inheritance chain.
- **Non-secret settings storage:** a local, git-ignored config file (not
  `.env`), validated through Pydantic v2 models consistent with the rest of
  the codebase. Exact path/format is implementation detail for the follow-up
  plan, not this ADR.
- **Secrets storage:** provider API keys are **never** written to a repo file,
  `.env`, or an application-managed encrypted blob. They are stored and
  retrieved through the OS's native credential store via the `keyring`
  library (macOS Keychain, Windows Credential Manager, Linux Secret Service),
  consistent with ADR-0024's single-user-local scope — this is revisited if a
  future ADR moves the platform toward multi-user/hosted (ADR-0024
  Consequences already flags that as out of MVP scope). The settings store
  holds only a reference (which keyring entry to look up), never the key
  value itself.
- **UI:** a settings surface for editing global and per-component
  provider/model choices and credentials. Per ADR-0020 (no central dashboard),
  this is a mountable settings page/router the package exposes, which each
  subsystem UI embeds (the same mounted-router pattern already used by the
  controls-compliance-catalog playground), not a new standalone app.
- **Relationship to ADR-0014/ADR-0031:** out of scope here — this ADR governs
  *which provider and credentials* an LLM call uses, not *what content* is
  sent to it. Redaction/PII-gateway behaviour is unaffected and continues to
  be decided per consuming feature (e.g. ADR-0031 for this package's own
  conversion pipeline).

## Consequences

- `controls-compliance-catalog`'s `llm_client.py` is refactored to depend on
  `llm-provider-config` for provider/model/credential resolution instead of
  owning a single hardcoded call shape; its `convert_chunk` contract
  (spec `001-oscal-ai-conversion` research.md R2) stays the call-site contract,
  now backed by a real, configurable provider.
- A new runtime dependency on `keyring` (and whatever backend it needs per OS)
  is added to the shared package; CI/headless environments without a usable OS
  keychain backend need a documented fallback or are explicitly out of scope
  for this package's own test suite (tracked as implementation follow-up).
- `ARCHITECTURE.md` and `architecture/model/` carry the corresponding
  package/capability entries in this same PR, per Principle X.
- If the platform later needs multi-user/hosted secrets (ADR-0024 is revisited),
  the keyring-backed store is swapped for a server-side secret store behind the
  same resolution interface; this ADR's settings/override model is designed to
  not need to change, only the credential backend.

## Alternatives considered

- **`.env` / environment variables for secrets** — rejected by the maintainer:
  plaintext in a file, no access control beyond filesystem permissions, easy
  to accidentally commit.
- **App-managed encrypted-at-rest file/DB (e.g. Fernet with a local master
  key)** — rejected for now: still first-party code responsible for key
  management and a second secret (the master key) to protect; the OS keychain
  already solves this for a single local user with no new crypto code.
  Revisit if/when multi-user requires a server-side store anyway.
- **External secrets manager (Vault / cloud secret manager)** — rejected for
  now: right fit for a shared/hosted deployment, unjustified operational
  overhead for a single-user local MVP (ADR-0024).
- **Settings/config logic embedded directly in `controls-compliance-catalog`**
  — rejected: the need for global-plus-per-component provider settings is
  explicitly cross-subsystem; duplicating it per package the next time another
  subsystem needs an LLM call was the problem this ADR exists to avoid.
- **One catch-all `common`/`shared` package for all cross-cutting
  functionality** — rejected: becomes an undifferentiated dependency magnet
  with unrelated concerns coupled together; one package per shared concern
  keeps dependency graphs legible, matching the existing per-subsystem
  granularity.
