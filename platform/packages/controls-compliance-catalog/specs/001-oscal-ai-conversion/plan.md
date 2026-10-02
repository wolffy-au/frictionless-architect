# Implementation Plan: AI-Assisted Policy & Standard Conversion to OSCAL

**Branch**: `003-oscal-ai-conversion` | **Date**: 2026-09-23; re-targeted 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/spec.md`
(originally `specs/003-oscal-ai-conversion`; re-homed here per `ARCHITECTURE.md` §6 and §8.1)

## Summary

Build the first real path from a verbatim policy/regulatory-standard document (PDF,
Word, spreadsheet/CSV, Markdown, or text) to machine-readable OSCAL, orchestrated end to
end behind a new FastAPI surface (`/oscal/*`, served by the `controls-compliance-catalog`
package's own app): normalize → AI-assisted, chunked conversion to Trestle-editable
Markdown → Trestle structural validation → a Compliance-Officer approval gate → Trestle
import/assemble into an OSCAL Catalog + Profile → Trestle profile-resolve into a fully
resolved Catalog. Because neither an LLM client nor a forensic audit ledger exists in
code yet (both are architecture-model vision only — `ext-llm`, `store-ledger`), this
feature also stands up minimal, tightly-scoped first-party versions of each: a
`litellm`-backed conversion client and an append-only JSONL ledger, built only to the
shape this feature needs. Accuracy is proven against two vendored golden datasets (NIST
SP 800-53 rev5 via `third_party/oscal-content`, FedRAMP baselines via
`third_party/fedramp-automation`) in a separate, marked test path — never as a production
input source (FR-008).

Normalization's sectioning/traceability design and the validation-report shape are
ported as native Python from `oscal-document-workbench` (Apache-2.0 prior art for an
adjacent SSP-drafting problem, not a dependency of this feature — `research.md` R10).

## Technical Context

**Language/Version**: Python 3.12 (package range `>=3.11,<3.14` per the package's
`pyproject.toml`).

**Primary Dependencies**: FastAPI (the package's own app, `/oscal` router), Pydantic v2,
`compliance-trestle` (used via its Python command classes — research.md R6; the
repo-root project already depends on it, but the package declares its own dependencies,
locked in the shared `platform/poetry.lock` — ADR-0002), `litellm` (new — `ext-llm` client, R2), `pypdf` (new — PDF
normalization), `python-docx` (new — Word normalization), `openpyxl` (new — `.xlsx`
normalization; stdlib `csv` covers `.csv`).

**Storage**: Filesystem only — Trestle workspaces per Source Document Identifier under
`.data/oscal/workspaces/<slug>/` (R7), and an append-only JSONL forensic ledger at
`.data/oscal/forensic-ledger.jsonl` (R3). No Postgres/Neo4j dependency for this feature.

**Testing**: `pytest` + `pytest-asyncio` (the visualiser's pattern: in-process
`httpx.AsyncClient` against the FastAPI app, under the package's `tests/api/`) for the
fast suite; a separate `golden` pytest marker for the FR-006/FR-007 golden-dataset
validation that invokes a real LLM and real trestle (excluded from the default run — R8).
The package's `tests/unit/` mirrors `src/controls_compliance_catalog/` per `TECHNICAL.md`'s
Testing Layout, and `scripts/platform_checks.sh` gates it (pyright, mypy, pytest at 90%
coverage). Real trestle
CLI/library invocations in tests, never mocked (FR-012, constitution-aligned since
mocking the one thing under integration test would hide the behavior we need to catch).

**Target Platform**: Linux server (same as the existing visualiser deployment target).

**Project Type**: Monorepo package — `platform/packages/controls-compliance-catalog`
(subsystem 1, `ARCHITECTURE.md` §4), the first extraction into `platform/` (§8.1). It has
its own FastAPI app and imports nothing from the flat `src/frictionless_architect/`.

**Performance Goals**: No fixed request-latency target for conversion/assembly/resolution
(these are long-running, LLM-bound operations, not the <1s/<5s query targets in
`NONFUNCTIONALS.md`, which apply to read-path queries). `GET /oscal/conversions/{id}`
status reads should meet the NONFUNCTIONALS "common queries <1s" bar since they're a
plain filesystem/ledger read.

**Constraints**: Documents may exceed a single LLM context window and MUST still convert
correctly via chunking that preserves control identity (FR-018, R5). LLM failures/timeouts
must produce zero partial output (FR-014) — every write path is all-or-nothing per
identifier. Verbatim document content is sent to the LLM as-is, no redaction step
(FR-016) — this is a deliberate, spec-approved deviation from ADR-0014's PII-gateway rule,
scoped narrowly: see Constitution Check below.

**Scale/Scope**: Single-user, locally-run MVP scope per `ADR-0024`/`PROJECT_SPECIFICATION.md`
— one conversion/assembly/resolution in flight at a time per Source Document Identifier
(concurrent submissions to the *same* identifier are rejected `409`, not queued).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Principle | Assessment |
|---|---|
| I. Code Quality | The package's modules follow the existing `visualizer/` module boundaries (config/api/service-per-concern). No violation. |
| II. Testing Standards | Real trestle invocations in tests (FR-012) instead of mocks is the correct application of "verified correctness" here — mocking the one integration surface under test would hide real behavior. Golden-dataset tests are marked and excluded from the fast loop to keep TDD's red-green cycle fast for everything else; coverage target (>90%) applies to the fast suite. No violation. |
| III. UX Consistency | API follows the same action-based-endpoint / Pydantic-validation pattern as the existing visualiser contract (`specs/002-neo4j-schema-ui/contracts/api.md`). Error body is standardized (`error_code`/`message`/`details`) per `TECHNICAL.md`. No violation. |
| IV. Performance | Conversion/assembly/resolution are inherently >200ms (LLM + trestle round-trip) — handled as async/background-eligible operations, consistent with "any operation exceeding 200ms must be asynchronous or justified." Justified here: LLM latency is external and unavoidable. |
| V. Security | FR-016 sends verbatim document content to the LLM without ADR-0014's redaction step. Policy/standard documents are organizational artefacts inside the trust boundary, not collaboration-tool chatter carrying PII/PHI — a different ingestion path, not a bypass; ADR-0014 is unchanged. Recorded as `ADR-0031`. |
| VI. State Management | `ApprovalRecord`/conversion `status` are explicit, ledger-derived states with defined transitions (data-model.md "State machines"). No violation. |
| VII. System Integrity & Accuracy | Golden-dataset validation (FR-006/FR-007) validates the AI-assisted pipeline before it's trusted, against a "faithful paraphrase" bar (SC-002/SC-003). No violation. |
| VIII. Durability & Interoperability | Outputs are real OSCAL JSON validated against `third_party/oscal` schemas; Catalog/Profile/Resolved-Catalog stay distinct (FR-009). Ported designs (R10) carry Apache-2.0 attribution headers; the port decision itself is recorded in `ADR-0030`. No violation. |
| IX. Cross-Platform Consistency | Pure backend/API feature, no OS-specific or display-dependent behavior. Not applicable beyond "runs the same on any Linux host," which filesystem-only storage satisfies. |

**Gate result**: PASS, with one explicit, spec-directed exception (V. Security / FR-016)
recorded above rather than hidden — no Complexity Tracking entry needed since it is not
added complexity, it's a documented scope boundary the spec itself set via clarification.

**Tracked follow-ups**: filed as `ADR-0031` (FR-016's deviation from `ADR-0014`'s
redaction rule) and as an update to `ADR-0030` (the decision to port, not vendor or
depend on, `oscal-document-workbench`'s sectioning and validation-report designs).

## Project Structure

### Documentation (this feature)

```text
platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── api.md            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by this command)
```

### Source Code (`platform/packages/controls-compliance-catalog/`)

```text
src/controls_compliance_catalog/
├── __init__.py
├── app.py                             # FastAPI app for this package; includes the api.py router
├── api.py                             # FastAPI router: /oscal/conversions, /approve, /assemblies, /resolutions
├── config.py                          # OscalSettings (FRICTIONLESS_ARCHITECT_ env prefix, data_dir, llm model/timeout)
├── models.py                          # Pydantic request/response + domain models (data-model.md)
├── normalizer.py                      # PDF/Word/spreadsheet-CSV/Markdown/text -> NormalizedDocument + SourceMapEntry sections (R4; sectioning ported from oscal-document-workbench, R10 — attribution header)
├── chunking.py                        # packs normalizer sections into LLM-call chunks preserving control identity (R5)
├── llm_client.py                      # ext-llm wrapper over litellm (R2)
├── markdown_converter.py              # orchestrates normalize+chunk+LLM -> Trestle Markdown, updates SourceMapEntry.status per section
├── trestle_ops.py                     # import / author-assemble / profile-resolve via trestle's Python API (R6); validate produces a ValidationReport (shape ported from oscal-document-workbench, R10 — attribution header)
├── workspace.py                       # Trestle workspace layout keyed by Source Document Identifier (R7)
├── approval.py                        # FR-011 approval-gate logic, reads ApprovalRecord off the ledger
└── ledger.py                          # append-only JSONL forensic ledger (R3)

tests/
├── unit/                              # mirrors src/controls_compliance_catalog/, one test module per production module
├── api/
│   ├── test_oscal_conversions.py      # US1
│   ├── test_oscal_assemblies.py       # US2
│   ├── test_oscal_resolutions.py      # US3
│   └── test_oscal_golden_dataset.py   # FR-006/FR-007, marked `golden`, excluded from default run
└── features/                          # behave acceptance scenarios added via acceptance-author, per AGENTS.md workflow
```

### Component diagram

Module dependencies within `src/controls_compliance_catalog/` (arrows read "depends on"
/ "calls"). `app.py` only constructs the app and mounts `api.py`'s router, so the diagram
starts at `api.py`. Source: `diagrams/oscal-component-diagram.puml`.

![Component diagram](diagrams/oscal-component-diagram.svg)

**Structure Decision**: The pipeline is written straight into
`packages/controls-compliance-catalog`, not into the flat `src/` and moved later
(`ARCHITECTURE.md` §8.1, ADR-0005). The package runs its own FastAPI app rather than
mounting a router on `frictionless_architect.app`, which the flat layout keeps only until
§8 step 7 empties it; the `/oscal` URL prefix and the contract in `contracts/api.md` are
unchanged. The package depends on no other platform package (§8.1): the forensic ledger
belongs to subsystem 3 (`digital-twin-knowledge-graph`, §4), so `ledger.py` stays a
narrow, package-local ledger (R3) until that package exists to take it over.

This plan covers the package's Python side, the `api/` half of ADR-0020's per-subsystem
layout. The `ui/` half, which #44 builds first with stubs, is not planned here; its build
tooling is still open (#55).

## Complexity Tracking

*No unjustified Constitution violations — see Constitution Check above (the one FR-016
security deviation is spec-directed and documented there, not a complexity trade-off).*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| — | — | — |
