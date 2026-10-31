# pii-gateway

Shared package (not one of the six subsystems) that scrubs PII/PHI from content
before it reaches an LLM provider. Backed by Presidio
(`presidio-analyzer`/`presidio-anonymizer`) over spaCy's `en_core_web_lg` NER model.

- Decided in [ADR-0014](../../../docs/adr/0014-pii-anonymization-gateway.md)
  (mandatory scope and default failure-mode) and
  [ADR-0043](../../../docs/adr/0043-pii-gateway-detector-library-presidio.md)
  (detector/anonymization engine).
- Required callers: `modelling-specification`'s spec drafting (`fn-spec-generator`,
  wired in this feature). `architecture-governance`'s ADR/evaluation drafting
  (`fn-governance-eval`) and the conversational-modelling agent's prompts
  (`fn-conversational-authoring`, GH #68) are registered contexts with the contract
  ready, but not wired yet — deferred to those packages' own build-out.
- Exempt: policy/regulatory-standard document conversion
  (`fn-ai-markdown-conversion`, `fn-policy-quality-feedback`) continues to call the
  LLM provider directly (ADR-0031).

## Setup

Presidio's pip packages don't bundle a spaCy model; install `en_core_web_lg`
explicitly once per environment before importing this package:

```bash
poetry run python -m spacy download en_core_web_lg
```

## Usage

```python
from pii_gateway import scrub

result = scrub("Contact Jane Doe at jane@example.com", context="spec-generator")
# result.text == "Contact <PERSON> at <EMAIL_ADDRESS>"
# result.action == "redacted_and_proceeded"
```

- **Contract**: `scrub(text: str, *, context: str) -> ScrubResult`. Every caller gets
  auto-redact-and-proceed on a detected match except the
  `conversational-authoring` context, which gets flag-for-review — call
  `result.pending_confirmation.resolve(Resolution.REDACT | ALLOW | EDIT)` once the
  architect responds; an abandoned turn simply discards it (nothing persisted).
- A detector-engine error is treated the same as a detected match (fails closed) —
  never a silent pass-through of unscrubbed content.
- **Audit**: every call appends one metadata-only JSON line to
  `~/.local/state/frictionless-architect/pii-gateway-audit.jsonl` (override with
  `PII_GATEWAY_AUDIT_PATH`) — never the matched text or surrounding content.
- **Config**: `~/.config/frictionless-architect/pii-gateway.toml` (override with
  `PII_GATEWAY_CONFIG_PATH`) holds which detector categories are active and the
  failure-mode, per caller context.

### Settings page

`create_settings_router([...context ids...])` returns a FastAPI router serving a
settings page at `/settings/pii-gateway` (plus a JSON API under it). Mount it in any
subsystem UI, or standalone:

```python
app.include_router(create_settings_router(["spec-generator", "governance-eval", "conversational-authoring"]))
```

The page toggles which detector categories are active and the failure-mode, per
context, taking effect on the next `scrub()` call with no redeploy. There is no
authentication (single-user local MVP, ADR-0024), so bind to localhost.

## Development

From `platform/` (one shared lock for every package — ADR-0002):

```bash
poetry install
poetry run pytest packages/pii-gateway/tests
```

`bash scripts/platform_checks.sh` from the repo root runs the full package gate.

## Layout

- `src/pii_gateway/` — the package.
- `tests/` — its tests, mirroring `src/`.
- `specs/` — this package's feature specs (`ARCHITECTURE.md` §6).
