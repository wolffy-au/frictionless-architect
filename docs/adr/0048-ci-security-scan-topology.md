# ADR-0048: CI security-scan topology — SonarQube and CodeQL gate CI; Snyk is local-only

- **Status:** Proposed
- **Date:** 2026-11-08
- **Sources:** commit `acb7b81` (`ci: parallelize test jobs, drop Snyk, cache PlantUML jar`,
  pre-dates `v0.9.0`); `.github/workflows/ci.yml`; GitHub code-scanning default setup
  (`languages: ["actions","python"]`, `schedule: weekly`, configured 2026-10-25); commit
  `b033868` (`docs: stop describing Snyk as a CI check`); commit `a170129`
  (`docs: correct what the pre-commit and pre-merge gates run`); `RELEASE.md` §2–3;
  `AGENTS.md` "Toolchain" ("Snyk runs locally only. CI no longer runs Snyk.")

## Context

`ci.yml` originally ran three `snyk` steps (SCA on root + `platform/`, plus Snyk Code),
made `continue-on-error` (`6477df1`, `b1557fd`) once the org's test quota was repeatedly
exhausted, then dropped from `ci.yml` entirely (`acb7b81`) in favour of running all three
scans only in the local `pre_merge_checks.sh` gate, blocking there instead. Separately,
GitHub's CodeQL default setup was enabled for this repo (Python + GitHub Actions, weekly
schedule) as a `security/code-scanning` feature outside `ci.yml` — it has already produced
and auto-fixed findings (alerts #1/#2, `py/stack-trace-exposure` in
`llm-provider-config/router.py`). Both changes pre-date `v0.9.0` and were never recorded as
a decision; several agent/process docs (`.claude/agents/*.md`, `CONTRIBUTING.md`,
`RELEASE.md`, `TECHNICAL.md`) still described Snyk as a CI check until this release's docs
commits (`b033868`, `a170129`) caught them up to what `ci.yml` and the repo's code-scanning
settings actually do. The current gate composition — which security scanner blocks a PR vs.
which is advisory/local-only — is exactly the kind of choice Principle V (Security
Practices) and Principle X (Decision Traceability) expect an ADR for, and it determines
what a human reviewer can rely on CI having already checked before merging to `main`.

## Decision

> DRAFT — confirm: CI (`ci.yml`) blocks a PR on ruff/pyright/mypy/behave/pytest(+coverage)
> and the SonarQube quality gate. GitHub's CodeQL default setup (Python + Actions, weekly
> schedule, not a step in `ci.yml`) runs as a second, GitHub-native blocking-by-convention
> check surfaced via `security/code-scanning` alerts, triggered on every push per its own
> schedule/trigger rather than `ci.yml`'s. Snyk (open-source SCA on the root and `platform/`
> locks, plus Snyk Code) is **not** run in CI at all; it runs only locally, in
> `scripts/pre_merge_checks.sh`, and blocks a release there (needs `SNYK_TOKEN`) rather than
> blocking any individual PR.

## Consequences

> DRAFT — confirm:

- A PR can merge to `develop` without ever running Snyk; only a release (`pre_merge_checks.sh`,
  RELEASE.md step 2) is guaranteed to have run it, and only on whoever's machine ran that
  script.
- Dependabot/CodeQL alerts (GitHub-native) and SonarCloud issues are the only security
  findings guaranteed to have run on every push; both are referenced by number in commit
  messages per the agent catalog's convention ("Closes codeql alert #N" /
  "Closes dependabot alert #N").
- `release-runner`/`vulnerability-remediator`/`quality-uplift` already encode this topology
  in their own instructions (`.claude/agents/*.md`) as of this release's docs fixes; this ADR
  is the architectural record those instructions should cite, rather than the only place the
  rule is written down.
- Revisit if the Snyk org's test-quota exhaustion is resolved (a paid plan, or Consistent
  Ignores enabled) — re-adding a non-blocking Snyk step to CI would need re-opening this
  decision, not a silent `ci.yml` edit.

## Alternatives considered

- **Keep Snyk in `ci.yml` as `continue-on-error`** (the intermediate state before
  `acb7b81`) — rejected: still consumed quota on every push even though its failures were
  ignored, apparently with no corresponding benefit over running it locally pre-merge.
- **Drop Snyk entirely, nowhere** — not adopted: it still runs locally in
  `pre_merge_checks.sh` and gates a release, so open-source/code-level Snyk findings are not
  simply unchecked.
