# Phase 0 Research: Browser-Level Tests for the HTML UIs

All ambiguity was already resolved during `/speckit-clarify` (see `spec.md` →
Clarifications) and during this plan's own scope research (captured as ADR-0053). No
`[NEEDS CLARIFICATION]` markers remain in `spec.md`'s Technical Context inputs. This file
records the decisions that shaped the plan, so `plan.md` can reference rather than restate
them.

## Decision: Reuse the existing behave + Playwright pattern (no pytest-playwright)

- **Decision**: Extend the `behave` + plain `playwright` harness already shipped in
  `platform/packages/controls-compliance-catalog/tests/features/` and mirrored in
  `platform/packages/modelling-specification`, rather than adding `pytest-playwright` as
  GH #119 originally proposed.
- **Rationale**: Two of the three in-scope UI surfaces already have committed, working
  browser-level coverage using this pattern, already gated by `scripts/platform_checks.sh`
  (itself called from `scripts/pre_merge_checks.sh`). A second toolchain would duplicate
  live-server bootstrap and browser-lifecycle logic for the same job, violating Principle I
  (DRY). Full decision record: ADR-0053.
- **Alternatives considered**: `pytest-playwright` (rejected — redundant toolchain); see
  ADR-0053 for the full list.

## Decision: Visualiser gets a minimal placeholder HTML page

- **Decision**: Add one minimal placeholder landing page to
  `src/frictionless_architect/visualizer/`, sufficient for smoke testing only.
- **Rationale**: The visualiser currently serves only a JSON API; GH #74 (still open) tracks
  its real UI composition/build tooling separately. Without a page, FR-001/FR-002 have
  nothing to exercise for this surface. The maintainer chose to deliver smoke coverage for
  all three named surfaces now rather than descope the visualiser to two of three.
- **Alternatives considered**: Skip the visualiser entirely until GH #74 ships (rejected by
  maintainer); smoke-test FastAPI's auto-generated `/docs` Swagger UI as a stand-in
  (rejected — exercises code this project doesn't own).

## Decision: One automatic retry on browser-test failure (FR-008)

- **Decision**: A failing browser-level test is retried exactly once before the merge gate
  reports a failure; a second consecutive failure is reported as real.
- **Rationale**: User's explicit clarification answer (Session 2026-11-14, Option B),
  trading a small risk of masking an intermittent real bug for fewer flaky false positives.
  This diverges from this plan's own fail-fast default recommendation (Principle VII) and
  is recorded as the binding decision in `spec.md`'s Clarifications section.
- **Alternatives considered**: No retries / fail-fast on first failure (Option A — the
  plan's own recommendation, not chosen).

## Decision: Delete the dead `frontend/` block outright, no replacement

- **Decision**: Remove the stub in `scripts/pre_merge_checks.sh` that checks for a
  nonexistent `frontend/` directory and always prints "Skipping…", without replacing it with
  new logic in that location.
- **Rationale**: `scripts/platform_checks.sh`'s existing Playwright/behave fan-out and the
  pre-existing root `poetry run behave tests/features/` step already gate all real UI-test
  work (existing platform packages' coverage, plus the new root `@ui` scenarios this feature
  adds). A replacement step in the same place would be a second, redundant gate.
- **Alternatives considered**: Rewrite the stub to call the new root `@ui` scenarios
  directly (rejected — redundant with the pre-existing root `behave tests/features/` call,
  which already runs them once `@ui` scenarios exist there).

## Decision: Deterministic stand-ins for external dependencies (FR-004)

- **Decision**: Reuse each surface's existing stand-in pattern — `FakeCompletion` for the LLM
  provider, the visualiser's existing sample-data fallback (`VisualizerSettings.neo4j_uri`
  default) for Neo4j — rather than introducing new mocking infrastructure.
- **Rationale**: Both already exist and are already proven in the shipped harness this
  feature extends; "Check simplest fix first" — no new plumbing is needed.
- **Alternatives considered**: A new shared fixture/stub library (rejected — no identified
  need beyond what already exists; would be premature abstraction for a single-feature
  concern).

## Model impact

None — see `plan.md` → "Model impact" for the reasoned statement (checked against
ADR-0044's Technology-layer threshold and the existing `gap-neo4j-schema-ui` Gap, not just
asserted).
