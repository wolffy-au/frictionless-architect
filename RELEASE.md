# Release Process

How to cut a release of `frictionless-architect`, end to end. Derived from the
repo's tooling (`commitizen`, `poetry-dynamic-versioning`, `.github/workflows/ci.yml`,
`scripts/pre_merge_checks.sh`) and modelled on the pyArchimate project's
`how_to_build.md`. The `release-runner` agent executes this document step by step.

## Versioning model

- **Runtime version** comes from the latest `v<X.Y.Z>` git tag via
  `poetry-dynamic-versioning` (`pyproject.toml` `[tool.poetry-dynamic-versioning]`,
  `style = "semver"`). `[tool.poetry] version` stays `0.0.0` as a placeholder — do not
  hand-edit it.
- **Bump size** is computed by `commitizen` from the Conventional Commit history
  (`fix:` → patch, `feat:` → minor, `feat!:` / `BREAKING CHANGE:` → major).
  Config: `[tool.commitizen]`, `tag_format = "v$version"`, `version_provider = "scm"`
  (reads the current version from the latest tag — same source as
  `poetry-dynamic-versioning`, so nothing is written to `pyproject.toml`),
  `major_version_zero = true` (pre-1.0: breaking changes bump the minor, not to 1.0.0),
  `annotated_tag = true`, `update_changelog_on_bump = true`.
- **`CHANGELOG.md`** is generated/updated by `cz bump`. `cz bump` writes only
  `CHANGELOG.md`, a bump commit and a tag. The tag it creates sits on `develop`, so it is
  deleted and re-created on `main` after the PR merge (§6, §8).

## Branch model

- Feature work on `feature/**`, fixes on `bugfix/**`; CI runs on their PRs (`ci.yml`).
- Integrate to `develop`.
- **Release via a `develop` → `main` PR.** `main` only changes via PR and a **human**
  reviews and merges it manually. Tags are created on `main`, after that merge.

## Keeping releases fast

Release day should only **verify** a clean state, never **produce** one. The agents in
§3–§5 (`quality-uplift`, `vulnerability-remediator`, `docs-uplift`, `spec-alignment`,
`adr-auditor`) do real remediation work when they find drift, and running that
serially at release time — scan, fix, re-gate, scan, fix, re-gate — is what makes a
release take hours instead of minutes.

- **Run these agents continuously on `develop`, not at release time.** Schedule them
  (cron / `/loop` / a CI job triggered on merge to `develop`) so SonarCloud/Snyk findings
  and doc/spec/ADR drift get fixed as they appear, days before anyone cuts a release.
  §3–§5 below should then be a quick read of already-green status, not a remediation
  pass.
- **If §3–§5 do find something at release time** (continuous maintenance lapsed, or
  new findings landed since the last scheduled run), dispatch the independent agents
  **in parallel** (one message, multiple `Agent` calls) rather than one after another:
  `quality-uplift` + `vulnerability-remediator` are independent of each other and of
  `docs-uplift` + `spec-alignment` + `adr-auditor`. Only re-run `pre_merge_checks.sh`
  once, after all of them land, not after each one.
- **Treat a release that required remediation as a signal to fix the schedule**, not as
  the new normal — the next release should go back to a verify-only pass.

## Preconditions

- Working tree clean, no untracked files that belong in the release.
- You are on `develop`, up to date with `origin/develop`.
- Every commit since the last tag follows Conventional Commits — verify with the
  `commit-auditor` agent first.
- CI is green on `develop`.

## Steps

### 1. Sync `develop` with `main`

```bash
git fetch origin
git checkout develop && git pull --ff-only origin develop
git merge --ff-only origin/main
```

This must be a fast-forward: prefer fast-forwards over merge commits, so `develop` and
`main` share one linear history instead of a sync merge commit on every release.
If it isn't a fast-forward — `main` picked up hotfix commits (e.g. a vulnerability fix)
that `develop` doesn't have yet — stop here. Rebase `develop` onto `main` and
force-push `develop` yourself *before* triggering the release agent; it does not do
this rebase/force-push on your behalf (`develop`'s normal push rule stays
fast-forward-only, never force — this is a deliberate, one-off exception you perform
by hand, not standing policy).

Never merge or fast-forward `main` locally.

### 2. Run the full quality gate

```bash
bash scripts/pre_merge_checks.sh
```

This runs `scripts/pre_commit_checks.sh` (pymarkdown, ruff, pyright, mypy, unit tests),
then `behave`, then `pytest --cov-fail-under=90 --cov=src`, then the frontend UI harness
if `frontend/` exists. Must pass clean.

### 3. SonarCloud — no open issues

CI already ran the scan on the last push. Confirm nothing is `OPEN`
(`TECHNICAL.md` → "SonarCloud Remediation Workflow"; token in `.secrets/`):

```bash
# API check:
curl -s "https://sonarcloud.io/api/issues/search?componentKeys=wolffy-au_frictionless-architect&branch=main&statuses=OPEN&ps=50&token=<token-from-.secrets>"
# or: poetry run pysonar --sonar-token=<token-from-.secrets>
```

This should normally come back empty — `quality-uplift` is expected to be running on
a schedule against `develop` (see "Keeping releases fast"), not invoked here for the
first time. If it does find something, dispatch `quality-uplift` and continue to step
4 rather than waiting on it in isolation; run both in parallel.

### 4. Security — no unresolved high/critical vulnerabilities

```bash
poetry run snyk test --package-manager=poetry
gh api repos/wolffy-au/frictionless-architect/dependabot/alerts --jq '[.[] | select(.state=="open")]'
```

As with step 3, this should come back clean if `vulnerability-remediator` has been
running continuously. If not, dispatch it alongside `quality-uplift` (parallel `Agent`
calls, not sequential) rather than blocking step 3 on it first.

### 5. Refresh documentation and specs against the code

```bash
# docstrings, README/quickstart, feature guides, diagrams, and the agent-orientation
# doc (AGENTS.md — what a coding agent needs to know on first contact with this repo):
#   docs-uplift
# spec-vs-code gap check (report only — action its findings if material):
#   spec-alignment
# decision-log check (opens a draft PR with proposed ADR stubs + stale-status edits —
#   review, flesh out, and merge before tagging if material):
#   adr-auditor
```

These three are independent of each other and of §3–§4 — dispatch all five agents
(`quality-uplift`, `vulnerability-remediator`, `docs-uplift`, `spec-alignment`,
`adr-auditor`) that turn out to have work in a single batch of parallel `Agent` calls,
not one after another, and run `pre_merge_checks.sh` (step 2) once more only after they
all land. As with §3–§4, a clean run of these should be the common case because they
run on a schedule against `develop`, not something release day discovers.

Commit any regenerated artefacts:

```bash
git status --porcelain
git add -A && git commit -m "docs: refresh docs, diagrams, and specs pre-release"
```

### 6. Bump the version and update the changelog (on `develop`)

```bash
poetry run cz bump --dry-run     # confirm the computed version
poetry run cz bump               # updates CHANGELOG.md, adds a bump commit and tag v<X.Y.Z>
git tag -d v<X.Y.Z>              # drop the develop-side tag; it is re-created on main (§8)
```

Review the generated `CHANGELOG.md` entry first.

*First release only:* with no existing `v*` tag, plain `cz bump` fails ("No tag matching
configuration could be found"). Use `poetry run cz bump --increment MINOR` (0.0.0 → 0.1.0).

### 7. Open the `develop` → `main` PR (human merge gate)

```bash
git push origin develop          # fast-forward only, never force
gh pr create --base main --head develop    # or update the existing PR
```

Wait until every check is resolved and green (CI, SonarCloud quality gate, Snyk), then
**stop**. A human reviews the PR and merges it manually, using a merge commit (not squash
or rebase, so the bump commit stays reachable from `main`). Do not use `gh pr merge`,
a local merge, or a push to `main`.

If Snyk fails on account quota ("Code test limit reached", "used your limit of private
tests") rather than on findings, the human decides whether to accept that.

### 8. Tag `main` after the merge

```bash
gh pr view --json state,mergedAt   # must be MERGED
git fetch origin
git tag -a v<X.Y.Z> -m "bump: version <A> → <X.Y.Z>" origin/main
git tag -l 'v*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$'   # confirm the name; rename if not
git merge-base --is-ancestor v<X.Y.Z> origin/main && echo ok
git push origin v<X.Y.Z>         # push only the tag
```

The name must match `tag_format = "v$version"` (and `poetry-dynamic-versioning`) exactly.

### 9. Create the GitHub release

Draft notes from the previous release as a template (subject line + summary of all
commits since the last tag), review, then:

```bash
gh release create v<X.Y.Z> --verify-tag --title "v<X.Y.Z>" --notes "<release notes>"
```

### 10. Merge `main` back into `develop`

```bash
git checkout develop && git pull --ff-only origin develop
git merge --ff-only origin/main   # or a plain merge if develop moved on
git push origin develop
```

## Not yet configured (TODO)

### PyPI / package publish

Not wired up: there is no `.github/workflows/release.yml`, no PyPI project, and it is
not yet decided that this codebase is distributed as a package at all (the spec frames
it as a locally-run application; `ARCHITECTURE.md` §5 only anticipates *per-package*
publish if a component is open-sourced standalone). Until that is decided, releases
stop after step 9 (tag + GitHub release, no artifact upload).

When a package *should* be published, the prerequisites are:

1. Create the PyPI project and configure a **trusted publisher** (OIDC) for this repo +
   workflow — no API token needed.
2. Add a GitHub Environment named `pypi`.
3. Add the workflow below. `poetry-dynamic-versioning` (the build backend) derives the
   version from the pushed tag, so `poetry build` needs no explicit version step.
4. Add consumer-facing usage docs — how an agent or developer writes code *against* the
   published package (API surface, patterns, gotchas). This goes in the README's usage
   section, or a dedicated `AI.md` if the consumer guidance outgrows it. Distinct from
   `AGENTS.md`, which orients agents *modifying* this repo.

```yaml
# .github/workflows/release.yml — adapted from pyArchimate's
name: Release

on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'

jobs:
  test:
    name: Test gate
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # dynamic versioning needs full history + tags
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Poetry
        run: pipx install poetry
      - run: poetry install --with dev --no-interaction
      - run: poetry run pytest --cov=src --cov-report=xml --cov-fail-under=90
      - run: poetry run behave tests/features/

  publish:
    name: Build and publish to PyPI
    needs: test
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/frictionless-architect
    permissions:
      id-token: write           # OIDC trusted publishing
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Poetry
        run: pipx install poetry
      - name: Build sdist and wheel
        run: poetry build       # version comes from the tag via poetry-dynamic-versioning
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

With that in place, step 8 (pushing the `v<X.Y.Z>` tag) triggers the publish, and
this section is deleted.
