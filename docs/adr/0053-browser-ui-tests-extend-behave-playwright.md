# ADR-0053: Browser-level UI tests extend the existing behave+Playwright harness

- **Status:** Accepted
- **Date:** 2026-11-14
- **Sources:** GH #119; `platform/packages/controls-compliance-catalog/tests/features/environment.py`;
  `platform/packages/modelling-specification/tests/features/environment.py`;
  `scripts/platform_checks.sh`; `scripts/pre_merge_checks.sh`; GH #74

## Context

GH #119 proposed introducing `pytest-playwright` (Python) under Poetry as a new browser-test
harness for the platform's server-rendered HTML UIs, with its own live-server fixture, to
replace the dead `frontend/` stub in `scripts/pre_merge_checks.sh`. Research during planning
found that two of the three UI surfaces in scope — the control conversion playground and the
LLM provider config page — already have committed, working browser-level coverage:
`platform/packages/controls-compliance-catalog/tests/features/` drives `behave` scenarios
against a real `uvicorn`-hosted FastAPI app via plain `playwright` (not `pytest-playwright`),
with a stubbed LLM backend and clean teardown. `platform/packages/modelling-specification`
mirrors the same pattern for its own UI. Both are already wired into
`scripts/platform_checks.sh`'s existing Playwright/behave fan-out, which
`scripts/pre_merge_checks.sh` already calls — so the dead `frontend/` block is a second,
unrelated no-op sitting alongside infrastructure that already does this job for those two
surfaces.

The third surface, the schema visualiser (`src/frictionless_architect/visualizer/`), has no
HTML page at all — only a JSON API. Building its UI composition is tracked separately as
still-open GH #74 and is explicitly out of scope here.

## Decision

Browser-level UI tests for this feature extend the existing `behave` + plain `playwright`
pattern already shipped in `platform/packages/{controls-compliance-catalog,
modelling-specification}/tests/features/`, rather than introducing `pytest-playwright` as a
second, parallel toolchain. Root-level scenarios (`tests/features/`) get the same
live-uvicorn-and-Playwright capability, added to the existing shared `tests/features/environment.py`
(conditionally, for `@ui`-tagged scenarios only, so non-UI scenarios there are unaffected and
don't pay for a browser launch). The visualiser gets one minimal, placeholder HTML landing page
— just enough surface for a smoke test — added under `src/frictionless_architect/visualizer/`;
it is not the subsystem UI composition work GH #74 tracks, and is expected to be superseded by
it.

The dead `frontend/` block in `scripts/pre_merge_checks.sh` is deleted outright, not replaced:
`scripts/platform_checks.sh` already gates the platform packages' UI scenarios, and the new
root-level `@ui` scenarios are gated by the pre-existing `poetry run behave tests/features/`
step in the same script — no new gate step is needed.

## Consequences

- One browser-test pattern across the codebase (`behave` + `playwright`), not two, keeping
  Principle I's DRY intact and avoiding two fixture styles doing the same job.
- `playwright` is added to the root `tests` dependency group (`pyproject.toml`), mirroring
  `platform/pyproject.toml`'s existing `tests` group; `playwright install chromium` is added to
  `scripts/pre_merge_checks.sh` immediately before the root `behave` step, mirroring
  `platform_checks.sh`'s own install step.
- The visualiser's placeholder page is intentionally minimal and carries a code comment noting
  it is superseded once GH #74 ships a real subsystem UI for it — it is not meant to accrete
  features.
- Follow-up: once GH #74's UI composition/build tooling lands, the visualiser's placeholder page
  and its test should be revisited (replaced, not kept indefinitely).

## Alternatives considered

- **Add `pytest-playwright` as GH #119 originally proposed** — rejected: the issue was filed
  without visibility into the `behave` + Playwright harness `controls-compliance-catalog` and
  `modelling-specification` had already shipped; adding a second toolchain for the same job
  duplicates fixture logic (two live-server bootstraps, two browser-lifecycle managers) for no
  behavioral gain.
- **Skip the visualiser surface entirely until GH #74 ships** — rejected by the maintainer in
  favor of a minimal placeholder page, so this feature still delivers smoke coverage for all
  three originally-named surfaces rather than two of three.
- **Smoke-test FastAPI's auto-generated `/docs` (Swagger UI) as a stand-in page** — rejected:
  it exercises FastAPI's bundled Swagger UI, not anything this project owns or could regress in
  a way relevant to this feature's intent.
