# ADR-0001: Application code lives one level below the root

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md`)
- **Sources:** `ARCHITECTURE.md` §1, §3.1, §11

## Context

The repo began as one flat tree mixing product vision, SpecKit machinery, feature
specs, and the single implemented slice (`src/frictionless_architect/`). The
target is an 8-capability platform, which will not fit one flat package.

## Decision

The repository root is a thin **governance / orchestration layer** only — vision,
constitution, cross-cutting specs, coordination scripts, submodule pointers, and
the fan-out CI. It holds **zero application code**. All application code lives one
level below the root.

## Consequences

- A migration is required to move today's `src/` into `platform/` (see ADR-0002, ADR-0005).
- Root-absolute config (`[tool.pytest]` `testpaths`, `[tool.behave]`, Sonar, CI)
  must be re-homed per package.
- This is a packaging decision only; the product vision in `PROJECT_SPECIFICATION.md`
  is unchanged.
