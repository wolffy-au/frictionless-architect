# Quickstart: AI-Assisted Policy & Standard Conversion to OSCAL

## Prerequisites

- From `platform/`: `poetry install` (adds `compliance-trestle`, `litellm`, `pypdf`,
  `python-docx` and `openpyxl` once declared in
  `packages/controls-compliance-catalog/pyproject.toml`; one shared lock, ADR-0002).
- Vendored golden-dataset submodules checked out for the golden-dataset tests:
  `git submodule update --init third_party/oscal-content third_party/fedramp-automation`.
- An LLM provider credential available to `litellm` (env var per provider, e.g.
  `ANTHROPIC_API_KEY`) — same trust boundary as other platform LLM uses (FR-016).

## Run the service

```bash
cd platform
poetry run uvicorn controls_compliance_catalog.app:app --reload
# serves the /oscal/* routes in contracts/api.md
```

## Validate User Story 1 (conversion)

```bash
curl -s -X POST http://localhost:8000/oscal/conversions \
  -F "source_document_id=demo-policy-v1" \
  -F "source_kind=custom-policy" \
  -F "file=@sample-data/oscal/example-policy.docx"
```

Expect `201` with `status: "validated"` and a `workspace_path` under `.data/oscal/`
containing Trestle-editable Markdown. Resubmit the same `source_document_id` with an
edited file and confirm the workspace is overwritten (FR-015), not duplicated.

## Validate User Story 2 (assembly)

```bash
curl -s -X POST http://localhost:8000/oscal/conversions/demo-policy-v1/approve \
  -H "Content-Type: application/json" -d '{"approved_by": "demo-officer"}'

curl -s -X POST http://localhost:8000/oscal/assemblies \
  -H "Content-Type: application/json" -d '{"source_document_id": "demo-policy-v1"}'
```

Expect `201` with `catalog_path` and `profile_path` both present and pointing at real
OSCAL JSON files that validate against `third_party/oscal`'s schemas.

## Validate User Story 3 (resolution)

```bash
curl -s -X POST http://localhost:8000/oscal/resolutions \
  -H "Content-Type: application/json" -d '{"source_document_id": "demo-policy-v1"}'
```

Expect `201` with a `resolved_catalog_path` pointing at a fully resolved OSCAL Catalog.

## Run the golden-dataset validation (FR-006/FR-007, SC-002/SC-003)

```bash
cd platform
poetry run pytest -m golden packages/controls-compliance-catalog/tests/api/test_oscal_golden_dataset.py -v
```

This is excluded from the default `poetry run pytest` run (see `research.md` R8) because
it invokes the real LLM and real trestle end to end against the vendored NIST/FedRAMP
content. Expect the report to show 100% of golden-catalog controls identified and a
faithfulness judgement per SC-002/SC-003.

## Run the fast suite

```bash
bash scripts/platform_checks.sh     # from the repo root: pyright, mypy, pytest at 90% coverage
bash scripts/pre_commit_checks.sh   # runs platform_checks.sh along with the root checks
```

## Failure modes to check

- Submit a document whose control identifiers collide with an already-assembled catalog
  under a *different* `source_document_id` → expect `status: "conversion_failed"` with a
  specific collision error (FR-013), no partial Markdown written.
- Attempt `/oscal/assemblies` before approval → expect `403` (FR-011).
- Attempt `/oscal/resolutions` before `/oscal/assemblies` has run → expect `422` (US3
  Acceptance Scenario 2).
