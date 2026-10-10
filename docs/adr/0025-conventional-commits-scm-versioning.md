# ADR-0025: Conventional Commits + commitizen; SCM-derived versions; branch model; local/CI gates

- **Status:** Accepted
- **Date:** unknown (pre-dates this log); behave gating added 2026-10-05 (commit `143570d`)
- **Sources:** `TECHNICAL.md` §"Version Control"; `AGENTS.md` §Conventions; `RELEASE.md` §"Branch model";
  `.pre-commit-config.yaml`; `scripts/pre_merge_checks.sh`; `.github/workflows/ci.yml`

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
- Once `tests/features/` holds real scenarios for a spec, `behave` becomes a
  **blocking** gate, not an optional one: it runs pre-push (`.pre-commit-config.yaml`)
  and in `scripts/pre_merge_checks.sh`, and the CI step drops its non-blocking
  `|| true`. Gates tighten from advisory to blocking as soon as a given check has
  real coverage behind it, rather than being blocking from day one.

## Consequences

- Every commit must be Conventional-Commits-clean so `cz` can infer the bump;
  `commit-auditor` checks a branch before a PR.
- Feature work is spec-driven (`speckit-specify` → `-plan` → `-tasks` →
  `-implement`) against the constitution.
- Any future local/CI gate follows the same tighten-when-covered pattern: add it
  non-blocking, flip it to blocking once real scenarios/tests exist for it.
