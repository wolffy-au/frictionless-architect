# Quickstart: validate conversational authoring end to end

Prerequisites: `poetry install` at repo root (for the skill/`build.py` side); `cd platform &&
poetry install` for the new package; an LLM provider configured via `llm-provider-config`
(`poetry run python -m llm_provider_config.cli set ...` or the mounted `/settings/llm` UI,
ADR-0034) for component `modelling-specification.conversational-authoring`. Contract:
[api.md](contracts/api.md). Model: [data-model.md](data-model.md).

## 1. Propose and apply a clean change (US1, SC-001)

```bash
cd platform
poetry run uvicorn modelling_specification.router:app --port 8100 &
curl -s -X POST localhost:8100/authoring/sessions | jq .session_id
curl -s -X POST localhost:8100/authoring/sessions/$SID/propose \
  -d '{"request": "add an application function fn-example under sub-modelling"}'
curl -s -X POST localhost:8100/authoring/sessions/$SID/deltas/$DID/decide -d '{"action":"apply"}'
```

Expect: `status: "applied"`, a `state_classification`, and `architecture/model/elements.yaml`
now containing `fn-example` — confirm with `poetry run python architecture/model/build.py`
reporting a higher element count and still VALID.

## 2. Rejection with an explanation (US2 Scenario 1, SC-002)

Propose a change that violates the metamodel (e.g. a relationship type illegal for its
endpoints). Expect `status: "flagged"`, `validation_result.clean: false`, one `findings`
entry naming the violated rule and a `proposed_fix` — and confirm nothing was written:
`git status --short architecture/model/` shows no change until a `decide` call.

## 3. Duplicate flag (US2 Scenario 2, SC-003)

Propose an element whose name and description closely match an existing one. Expect
`duplicates` populated with `matched_fields` containing at least `name` and `description`.
Call `decide` with `action: "reject"` and confirm no write; call again with
`action: "merge"` and confirm the existing element, not a new one, is the one changed.

## 4. Pattern suggestion (US2 Scenario 3)

Propose a direct relationship matching a `conventions.yaml` `interposed-pattern` rule (e.g.
the `sw-neo4j`-shaped pattern). Expect `pattern_suggestions` populated with the intermediary
type(s); `decide` with `action: "keep-direct"` applies the direct form anyway (it is legal).

## 5. Override traceability (US2 Scenario 4, FR-014)

Repeat step 2 or 3, then call `decide` with `action: "override"` and a `rationale`. Expect
`status: "applied"` and a non-null `override_decision_id`; confirm `docs/adr/` now has a new
`Status: Proposed` ADR stub whose body's `objection_detail` matches what was overridden (R7).

## 6. Render, auto and on-request (US1 Scenarios 2–3, SC-005)

```bash
curl -s -X PUT localhost:8100/authoring/config -d '{"auto_render": true}'
# re-run step 1's apply call: response now includes an inline "render" field
curl -s -X PUT localhost:8100/authoring/config -d '{"auto_render": false}'
curl -s "localhost:8100/authoring/render?object_id=fn-example" | jq .view_id
```

## 7. State query (US3, SC-004)

```bash
curl -s localhost:8100/authoring/sessions/$SID/deltas/$DID/state
```

Expect the classification recorded at apply time in step 1, unchanged.

## 8. Skill parity (Assumption 1)

```bash
poetry run python .claude/skills/model-archimate/scripts/validate.py architecture/model/frictionless-architect.xml
```

Expect the same findings the router's `validate` call would produce for the same model — the
skill now calls `modelling_specification.validation` rather than `pyArchimate` directly.

## 9. Gates

```bash
poetry run pytest tests/unit
cd platform && poetry run pytest packages/modelling-specification
bash scripts/pre_commit_checks.sh
bash scripts/platform_checks.sh
```
