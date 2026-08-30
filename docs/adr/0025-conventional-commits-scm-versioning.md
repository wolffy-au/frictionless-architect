# ADR-0025: Conventional Commits + commitizen; SCM-derived versions; branch model

- **Status:** Accepted
- **Date:** unknown (pre-dates this log)
- **Sources:** `TECHNICAL.md` §"Version Control"; `AGENTS.md` §Conventions; `RELEASE.md` §"Branch model"

## Context

Release automation needs to infer the version bump and generate a changelog
without manual bookkeeping, and multi-branch work needs a predictable integration
path.

## Decision

- **Conventional Commits**, enforced by **commitizen** (pre-commit hook on the
  message). Allowed types/scopes and `v$version` tags per the `commit-message`
  skill and `[tool.commitizen]`.
- Versioning: `poetry-dynamic-versioning` with `version_provider = "scm"`,
  `tag_format = "v$version"`. `cz bump` owns `CHANGELOG.md` and the tag.
- Branch model: work on `feature/**` or `bugfix/**` (never directly on `main` /
  `develop`); integrate to `develop`; **release from `main`**; merge `main` back
  into `develop` after a release. Full procedure in `RELEASE.md`.

## Consequences

- Every commit must be Conventional-Commits-clean so `cz` can infer the bump;
  `commit-auditor` checks a branch before a PR.
- Feature work is spec-driven (`speckit-specify` → `-plan` → `-tasks` →
  `-implement`) against the constitution.
