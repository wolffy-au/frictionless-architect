# Quickstart: PII Anonymization Gateway

Validation guide for the scenarios in [spec.md](spec.md); call shape and sequences are
in [contracts/scrub.md](contracts/scrub.md), entity detail in [data-model.md](data-model.md).

## Prerequisites

```bash
cd platform
poetry install
```

## User Story 1 — auto-redact on the automated drafting path

```bash
poetry run python - <<'PY'
from pii_gateway import scrub

result = scrub("Contact Jane Doe at jane@example.com", context="governance-eval")
assert "Jane Doe" not in result.text
assert "jane@example.com" not in result.text
assert result.action == "redacted_and_proceeded"

clean = scrub("The event-sourcing pattern decouples writes from reads.", context="spec-generator")
assert clean.text == "The event-sourcing pattern decouples writes from reads."
assert clean.action == "passed_through_unchanged"
print("User Story 1: OK")
PY
```

Expected: both assertions pass — no planted PII reaches the text a stubbed LLM call
would receive (SC-001), and ordinary prose is untouched (SC-002).

## User Story 2 — flag-for-review on the conversational-authoring path

```bash
poetry run python - <<'PY'
from pii_gateway import scrub

result = scrub("My SSN is 123-45-6789", context="conversational-authoring")
assert result.action == "flagged_for_review"
assert result.pending_confirmation is not None

resolved_text = result.pending_confirmation.resolve("redact")
print("User Story 2: OK ->", resolved_text)
PY
```

Expected: the call returns a pending confirmation rather than a silently redacted
pass-through (SC-004); abandoning the turn without calling `resolve(...)` leaves nothing
persisted (User Story 2 Scenario 3) — there is no cleanup step to run, which is itself
the thing to verify.

## User Story 3 — operator changes behavior without a code change

```bash
# Start the settings router standalone, or mounted by the portal (ADR-0020). A minimal
# standalone app wraps create_settings_router(...) (contracts/scrub.md's settings-router
# contract) the same way llm_provider_config does for its own settings page:
poetry run python - <<'PY' &
from fastapi import FastAPI
from pii_gateway.router import create_settings_router

app = FastAPI()
app.include_router(create_settings_router(["governance-eval", "spec-generator", "conversational-authoring"]))
import uvicorn
uvicorn.run(app, port=8001)
PY

curl -s http://localhost:8001/settings/pii-gateway/state | head -c 400
curl -s -X PUT http://localhost:8001/settings/pii-gateway/contexts/governance-eval \
  -H 'content-type: application/json' \
  -d '{"active_categories": ["PERSON", "EMAIL_ADDRESS"], "failure_mode": "flagged_for_review"}'
```

Expected: the next `scrub(..., context="governance-eval")` call applies the new
failure-mode immediately (SC-003), with no redeploy.

## Integration check — consumer wiring and exemption

```bash
cd platform
poetry run pytest packages/modelling-specification/tests/integration/test_pii_scrubbing.py
poetry run pytest packages/controls-compliance-catalog/tests/ -k "markdown_conversion or quality_feedback"
```

Expected: the first proves a planted PII string never reaches the stubbed LLM call
(FR-007); the second confirms `fn-ai-markdown-conversion`/`fn-policy-quality-feedback`
still bypass the gateway entirely (FR-008, ADR-0031). `architecture-governance` has no
equivalent check yet — FR-006's wiring is deferred to that package's own build-out
(spec.md Assumptions).

## Gate check

```bash
bash scripts/pre_merge_checks.sh
bash scripts/platform_checks.sh
```
