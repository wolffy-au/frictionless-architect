# ADR-0002: First-party code in one Poetry monorepo; forks as submodules

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md`)
- **Sources:** `ARCHITECTURE.md` §3.1, §4, §5, §11

## Context

The platform will have ~8 first-party packages plus a small number of vendored
upstream forks (an ArchiMate parser, OSCAL tooling). These two categories have
opposite change profiles: first-party code changes constantly and cross-package;
forks are low-touch (periodic `fork-sync`).

## Decision

- **First-party components** live as packages in a **single Poetry monorepo**
  (`platform/`): one tree, per-package `pyproject.toml`, one shared `poetry.lock`,
  siblings wired by path dependencies (`{ path = "../x", develop = true }`).
- **Vendored forks** are **git submodules under `third_party/` — and only there**.
  Never a submodule for actively developed first-party code.
- Frontends are packages in the same monorepo (pnpm/Vite sub-tree), not a separate repo.

## Consequences

- Dynamic versioning and the commitizen config move to the monorepo root.
- Splitting the single `pyproject.toml` touches every path dependency and the
  versioning setup — treat as its own migration step.
- Whether anything ever leaves the monorepo for its own repo is an open question
  (`ARCHITECTURE.md` §10); current lean is "package forever".

## Alternatives considered

- **`uv` workspace** — see ADR-0003.
- **Nx / meta-repo tools (`meta`, `git-subrepo`)** — JS-first or solve a polyrepo
  coordination problem we are deliberately avoiding.
- **Submodules for everything** — pointer-commit churn makes daily multi-package work miserable.
- **`pnpm` + `turborepo` now** — deferred until JS weight justifies a task graph.
