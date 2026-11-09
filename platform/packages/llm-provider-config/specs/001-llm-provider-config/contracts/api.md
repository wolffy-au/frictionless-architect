# API Contract: LLM Provider Configuration Settings Router

`create_settings_router(components, prefix="/settings/llm")` returns this contract as a
mountable `APIRouter`; a host app chooses the prefix and the component list (FR-014,
US5). All paths below are relative to that prefix. Errors use FastAPI's standard
`HTTPException` shape (`{"detail": "..."}`); endpoint-specific status codes are noted
per route. Secrets are never present in any request or response body (FR-005, SC-002)
— see `README.md`'s "Usage" section for a worked example of mounting the router.

## GET (prefix itself)

- **Purpose**: Serve the settings HTML page (US1–US5).
- **Response (200, `text/html`)**: The page; JS calls the JSON API below.

## GET /state

- **Purpose**: Everything the page renders in one call (US1, US2, US5).
- **Response (200)**: `config_path` (string); `providers` (list of `{id, needs_key,
  env_var}`); `default` (`ProviderSettings` + `key_source`, or `null`); `components`
  (list of `{id, label, override}`, `override` shaped like `default` or `null`).
  Never includes a key value (FR-006).

## PUT /default

- **Purpose**: Save the global default (US1 AC2).
- **Body**: `ProviderSettings` (`provider`, `model`, optional `params`/`api_base`/
  `credential_ref`).
- **Response (200)**: `{"status": "saved"}`.
- **Errors**: `422` (FastAPI validation) for an unsupported provider, empty model, or
  unknown field (US1 AC3, FR-003).

## PUT /components/{component_id}

- **Purpose**: Save a per-component override (US4 AC1).
- **Body**: `ProviderSettings`, same shape as `/default`.
- **Response (200)**: `{"status": "saved"}`.
- **Errors**: `404` if `component_id` was not declared to `create_settings_router`
  (US4 AC3).

## DELETE /components/{component_id}

- **Purpose**: Remove an override so the component inherits the default (US4 AC2).
- **Response (200)**: `{"status": "removed"}`.
- **Errors**: `404` if `component_id` is unknown.

## PUT /keys/{provider}

- **Purpose**: Store an API key in the OS keychain (US2 AC1).
- **Body**: `{"api_key": "<non-empty string>"}`.
- **Response (200)**: `{"status": "stored"}`. The key is never echoed back.
- **Errors**: `422` if `provider` needs no key (US2 AC4) or the value looks like a
  secret reference (`os.environ/...`); `503` if no usable OS keychain exists, naming
  the environment variable to set instead (US3 AC4, FR-010).

## DELETE /keys/{provider}

- **Purpose**: Remove a stored key (US2 AC3).
- **Response (200)**: `{"status": "removed"}`.
- **Errors**: `404` if there is no stored key to remove.

## POST /test

- **Purpose**: A one-word completion call against the resolved settings for a
  component, or the global default when `component` is omitted (US4 AC4).
- **Body**: `{"component": "<id>" | null}`.
- **Response (200)**: `{"ok": bool, "message": str}` — configuration errors
  ("not configured", "no API key") and provider failures are reported in `message`,
  never as an HTTP error status; provider error detail stays server-side in the log
  (CWE-209, FR-015).
- **Errors**: `404` if `component` names an undeclared component.
