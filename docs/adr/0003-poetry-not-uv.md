# ADR-0003: Poetry is the package manager, not `uv`

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §5)
- **Sources:** `ARCHITECTURE.md` §5; `TECHNICAL.md` §"Utilities and Frameworks", §"Dependency Installation"

## Context

The repo already uses Poetry (`poetry-dynamic-versioning`, commitizen,
`poetry.lock`). `uv` offers a faster resolver and a native workspace model that
would suit the planned monorepo (ADR-0002).

## Decision

Use **Poetry** for all first-party Python packages. `uv` is **not adopted**:
`uv sync` failed repeatedly in this environment, and no benefit is large enough to
justify migrating a working build. Do not use `requirements.txt`.

## Consequences

- `poetry install` (with all groups: `dev`, `tests`, `lint`, `docs`); run
  everything via `poetry run`.
- `uv` sits in an explicit "on hold" state — revisit only if Poetry's monorepo
  story becomes a real drag.
- `TECHNICAL.md` points at this decision as canonical rather than restating it.
