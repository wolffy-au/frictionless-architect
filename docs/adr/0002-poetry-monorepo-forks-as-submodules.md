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

## Implementation status (2026-09-26)

`ARCHITECTURE.md` §8 steps 1–3 are in (#71). `platform/pyproject.toml` is a
non-package Poetry project (`package-mode = false`) with one `poetry.lock`,
listing each package as a path dependency (`develop = true`). The first package
is `platform/packages/controls-compliance-catalog`. `scripts/platform_checks.sh`
gates every package, and the root gate scripts, the pre-push hook and CI call it.

Until step 7 empties the flat `src/`, the repo root keeps its own project,
`poetry.lock` and virtualenv beside `platform/`. So there are two locks for now,
not one. Root pyright excludes `platform/`, which has its own pyright config and
environment. Versioning and commitizen stay at the repo root: packages carry a
fixed `0.0.0` until they move to the monorepo root with the last extraction.

## Alternatives considered

- **`uv` workspace** — see ADR-0003.
- **Nx / meta-repo tools (`meta`, `git-subrepo`)** — JS-first or solve a polyrepo
  coordination problem we are deliberately avoiding.
- **Submodules for everything** — pointer-commit churn makes daily multi-package work miserable.
- **`pnpm` + `turborepo` now** — deferred until JS weight justifies a task graph.
