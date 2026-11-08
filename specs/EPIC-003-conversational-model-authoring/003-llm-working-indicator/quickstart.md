# Quickstart: LLM Working Indicator for Conversational Authoring

No API contract changes (see plan.md's Project Structure) — `contracts/api.md` under the
parent epic already covers `propose` and `propose/resolve-pii` unchanged. This guide is a
manual + automated validation walkthrough for the indicator itself.

## Prerequisites

```bash
cd platform && poetry install
```

An LLM provider configured for `modelling-specification.conversational-authoring`
(see `wiki/llm-provider-config.md`), or rely on the automated checks below, which stub it.

## Manual validation

```bash
./scripts/run-modelling_specification.sh   # from the repo root
```

Open `http://127.0.0.1:8001/authoring/`.

1. Type a request and click Send. **Expected**: a "Thinking…" message appears in the chat
   immediately, and the Send button is disabled — both before any reply is visible.
2. Wait for the reply. **Expected**: the "Thinking…" message is gone, replaced by the
   agent's actual reply (or delta summary), and Send is enabled again.
3. Send a request containing something the PII gateway flags (e.g. an email address).
   Choose "Redact and continue". **Expected**: a second "Thinking…" message appears while
   the resolved request is sent, then is replaced by its reply the same way.
4. Misconfigure the LLM provider (or stop it) and repeat step 1. **Expected**: "Thinking…"
   is replaced by the existing error message, not left stuck in the chat.

## Automated validation

```bash
cd platform
poetry run pytest packages/modelling-specification/tests/api/test_ui.py
poetry run behave packages/modelling-specification/tests/features/conversational_authoring_ui.feature
```

The behave scenario exercises step 1 above with a deliberately slowed fake LLM
(`context.fake_llm.delay`, see research.md), so the indicator's presence while waiting,
not just its eventual removal, is actually asserted.
