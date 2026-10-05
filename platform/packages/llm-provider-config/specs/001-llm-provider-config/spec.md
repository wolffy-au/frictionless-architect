# Feature Specification: LLM Provider Configuration

**Feature Branch**: `n/a` (retroactive spec for the shipped package; this package's spec number is `001`, separate from the root `specs/001-governance-platform`)

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Spec for the existing `llm-provider-config` package: settings, credential store, router, HTML page for choosing an LLM provider and entering its API key, and the headless environment-variable fallback. It stores API keys, so it must satisfy constitution Principle V (never commit secrets, validate all input, environment variables for configuration)."

Decision record: [ADR-0034](../../../../../docs/adr/0034-shared-packages-and-llm-provider-config.md). Single-user local MVP: [ADR-0024](../../../../../docs/adr/0024-single-user-local-mvp.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose a provider and model once for every AI feature (Priority: P1)

A platform operator wants AI features (first consumer: policy-to-OSCAL conversion) to use a chosen LLM provider and model without editing code or environment files. They set one global default (provider, model, optional endpoint and parameters) and every AI feature uses it.

**Why this priority**: Without a resolved provider and model no AI feature can run at all. Everything else refines this.

**Independent Test**: Save a default through the settings page, then ask for the call details of any component; they name the chosen provider, model and parameters.

**Acceptance Scenarios**:

1. **Given** no settings exist, **When** an AI feature asks which provider to use, **Then** it is told nothing is configured, with no guessed default.
2. **Given** a global default is saved, **When** any component asks, **Then** it receives that provider, model, endpoint and parameters.
3. **Given** an unsupported provider, an empty model or an unknown setting, **When** the operator saves, **Then** the save is rejected and nothing changes.

---

### User Story 2 - Store an API key without it touching the repository (Priority: P1)

An operator pastes an API key into the settings page. It goes to the operating system's credential store. It is never written to a file in the repo, never shown again and never returned by the service.

**Why this priority**: The package handles secrets, so this is the constitution's Principle V obligation and the reason this spec exists.

**Independent Test**: Store a key, then read every service response and the settings file; the key appears in none of them, yet an AI feature can still use it.

**Acceptance Scenarios**:

1. **Given** a provider that needs a key, **When** the operator stores one, **Then** it is saved to the credential store and the page confirms "stored" without echoing it.
2. **Given** a stored key, **When** the operator views the state, **Then** only where the key would come from (credential store, environment or missing) is shown, never the key.
3. **Given** a stored key, **When** the operator removes it, **Then** it is deleted from the credential store.
4. **Given** a provider that needs no key (Ollama, GitHub Copilot), **When** a key is submitted, **Then** it is refused.
5. **Given** the settings are saved, **When** the file is inspected, **Then** it contains no key material.

---

### User Story 3 - Run on a machine with no credential store (Priority: P2)

On a headless machine, CI runner or devcontainer there is no usable credential store. The operator supplies the provider's conventional environment variable instead and AI features still work, with the weaker protection made visible.

**Why this priority**: The platform's own devcontainer and CI have no keychain, so without this fallback nothing runs there.

**Independent Test**: Remove the credential store, set only the environment variable, and resolve a call; it succeeds and a warning that a plaintext key was used is logged.

**Acceptance Scenarios**:

1. **Given** no stored key but the provider's environment variable is set, **When** a call is resolved, **Then** the environment key is used and a warning is logged.
2. **Given** both a stored key and the environment variable, **When** a call is resolved, **Then** the stored key wins.
3. **Given** neither source has a key, **When** a call is resolved, **Then** it fails with a message naming both remedies.
4. **Given** the operator tries to store a key where no credential store exists, **When** they submit, **Then** they are told to set the environment variable on the server instead.

---

### User Story 4 - Override the provider for one feature and test it (Priority: P2)

An operator wants one AI feature (for example candidate conversion) on a different provider or model than the default, and wants to check that a configuration works before relying on it.

**Why this priority**: Useful tuning, but the default alone already delivers a working system.

**Independent Test**: Save an override for one component; that component resolves to it, others keep the default, and "Test connection" reports success or the provider's failure.

**Acceptance Scenarios**:

1. **Given** an override for a component, **When** that component asks, **Then** it gets the override; every other component gets the default.
2. **Given** an override, **When** the operator removes it, **Then** the component falls back to the default.
3. **Given** an override for a component the host has not declared, **When** it is submitted, **Then** it is rejected as unknown.
4. **Given** a saved configuration, **When** the operator runs "Test connection", **Then** a one-word reply from the provider reports success, and any failure (not configured, missing key, provider error) is reported as a readable message, not a crash.

---

### User Story 5 - Mount the settings page in any subsystem (Priority: P3)

A subsystem developer adds the settings page and its API to their own application by declaring which components use an LLM, without writing any settings code.

**Why this priority**: Reuse across subsystems; the first consumer already works without it.

**Independent Test**: Mount the router with two declared components and confirm the page lists exactly those.

**Acceptance Scenarios**:

1. **Given** a host declares components, **When** the page loads, **Then** it lists only those components, under the host's chosen path prefix.

---

### Edge Cases

- A settings file that is missing means "nothing configured", not an error.
- A settings file that is malformed or contains unknown fields is rejected, not partly applied.
- A key submitted blank is rejected.
- A filesystem that refuses permission changes (for example a mounted Windows drive) must not stop settings from saving; the file holds no secrets either way.
- Removing a key that does not exist reports "no stored key", not a crash.
- Ollama with no endpoint set uses the local default endpoint.
- The page is unauthenticated (ADR-0024): exposing it beyond localhost would let anyone replace stored keys or point calls at another endpoint. The spec treats localhost-only as a deployment rule, not something the package enforces.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support the providers OpenAI, Google Gemini, Anthropic Claude, Ollama and GitHub Copilot, and reject any other.
- **FR-002**: The system MUST hold one optional global default and optional per-component overrides, resolving a component to its override if present, else the default, else a clear "not configured" error.
- **FR-003**: Each configuration MUST carry a provider and a non-empty model, and MAY carry an endpoint, free-form call parameters and a named credential reference. Unknown fields MUST be rejected.
- **FR-004**: The system MUST never write an API key to the settings file, a repository file or a `.env` file, and MUST keep the settings file outside the repository tree by default.
- **FR-005**: The system MUST store API keys in the operating system's credential store and MUST NOT return a stored key from any endpoint or page.
- **FR-006**: The system MUST report, for each configuration, only the source of its key: credential store, environment, missing or not needed.
- **FR-007**: When the credential store has no usable entry or backend, the system MUST fall back to the provider's conventional environment variable and MUST log a warning on each such use because the key is plaintext. A stored key MUST take precedence.
- **FR-008**: When no key can be found, the system MUST fail with a message naming both ways to supply one.
- **FR-009**: The system MUST refuse to store a key for a provider that needs none, and MUST reject a blank key.
- **FR-010**: When a key cannot be stored because no credential store exists, the system MUST tell the operator which environment variable to set instead.
- **FR-011**: The system MUST validate every input it accepts (settings, keys, provider names, component identifiers) and reject invalid input without changing stored state.
- **FR-012**: The settings location MUST be overridable by an environment variable, and settings files SHOULD be written readable by the owner only where the filesystem allows.
- **FR-013**: The system MUST turn a resolved configuration into the arguments the LLM client needs (model, key, endpoint, parameters), using a local default endpoint for Ollama.
- **FR-014**: The system MUST offer a mountable settings page and JSON API, under a host-chosen path, that edits the default, overrides and keys and lists only the components the host declares.
- **FR-015**: The system MUST offer a connection test that returns success or a readable failure message and never raises to the caller.
- **FR-016**: The system MUST NOT authenticate callers (single-user local MVP, ADR-0024); documentation MUST state that the page is to be bound to localhost.

### Key Entities

- **Provider settings**: provider, model, optional endpoint, call parameters, optional credential reference. Never a secret.
- **LLM settings**: one optional default plus overrides keyed by component identifier.
- **Component**: an AI feature a host declares, with an identifier and a label.
- **API key**: a secret held only in the credential store (or a plaintext environment variable on headless machines).
- **Resolved call**: the model name, key, endpoint and parameters one AI call needs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After saving a default, an operator can run a successful connection test in under 2 minutes on a machine with a credential store.
- **SC-002**: 0 responses, pages, log lines or settings files contain a stored API key, verified by automated tests over every endpoint and the saved file.
- **SC-003**: Every use of a plaintext environment key produces a logged warning (100% of such uses).
- **SC-004**: 100% of invalid inputs (unknown provider, empty model, blank key, unknown component, unknown field) are rejected with no change to stored settings.
- **SC-005**: On a machine with no credential store, AI features work with only the environment variable set, with no code or file changes.
- **SC-006**: A host can mount the settings page for its components with one declaration and no further settings code.

## Assumptions

- Single-user, local use only (ADR-0024); multi-user access control, per-user keys and hosted secret management are out of scope until RBAC lands.
- The operating system provides a credential store on developer machines; headless machines use environment variables and accept the weaker protection.
- A plaintext environment variable is an accepted escape hatch, not a recommended steady state.
- GitHub Copilot signs in through its own device flow and caches its token outside this package; the package holds no Copilot credential.
- Out of scope: rotating or expiring keys, usage and cost tracking, retry or fallback between providers, and any provider beyond the five listed.
- Built behaviour is the source for this retroactive spec; where a requirement here and the code disagree, raise it as a finding rather than silently changing either.
