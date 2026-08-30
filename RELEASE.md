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
- **`CHANGELOG.md`** is generated/updated by `cz bump` (does not exist yet — the first
  bump creates it). `cz bump` writes only `CHANGELOG.md` and the tag.

## Branch model

- Feature work on `feature/**`, fixes on `bugfix/**` (matches `ci.yml` triggers).
- Integrate to `develop`.
- **Release from `main`.** Tags are created on `main`.

## Preconditions

- Working tree clean, no untracked files that belong in the release.
- You are on `main`, up to date with `origin/main`.
- Every commit since the last tag follows Conventional Commits — verify with the
  `commit-auditor` agent first.
- CI is green on `main`.

## Steps

### 1. Sync branches and fast-forward `main` to `develop`

```bash
git checkout main   && git pull origin main
git checkout develop && git pull origin develop
git merge main            # carry any main-only hotfixes into develop
git checkout main
git merge --ff-only develop
```

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

Resolve anything open (`quality-uplift` agent) before continuing.

### 4. Security — no unresolved high/critical vulnerabilities

```bash
poetry run snyk test --package-manager=poetry --severity-threshold=high
gh api repos/wolffy-au/frictionless-architect/dependabot/alerts --jq '[.[] | select(.state=="open")]'
```

Clear findings with the `vulnerability-remediator` agent.

### 5. Refresh documentation and specs against the code

```bash
# docstrings, README/quickstart, feature guides, diagrams, and the agent-orientation
# doc (AGENTS.md — what a coding agent needs to know on first contact with this repo):
#   run the  docs-uplift  agent
# spec-vs-code gap check:
#   run the  spec-alignment  agent   (report only — action its findings if material)
# decision-log check:
#   run the  adr-auditor  agent   (opens a draft PR with proposed ADR stubs +
#   stale-status edits — review, flesh out, and merge before tagging if material)
```

Commit any regenerated artefacts:

```bash
git status --porcelain
git add -A && git commit -m "docs: refresh docs, diagrams, and specs pre-release"
```

### 6. Bump the version and update the changelog

```bash
poetry run cz bump          # updates CHANGELOG.md, bumps version, creates the v<X.Y.Z> tag
```

Review the generated `CHANGELOG.md` entry and the tag before pushing.

*First release only:* with no existing `v*` tag, `cz bump` treats the base as `0.0.0`
and produces the first tag from the commit history. If you want to pin the starting
point instead, run `poetry run cz bump --increment MINOR` or pass an explicit
`--tag-version v0.1.0`.

### 7. Push `main` and the tag

```bash
git push origin main --tags
```

### 8. Create the GitHub release

Draft notes from the previous release as a template (subject line + summary of all
commits since the last tag), review, then:

```bash
gh release create v<X.Y.Z> --title "v<X.Y.Z>" --notes "<release notes>"
```

### 9. Merge `main` back into `develop`

```bash
git checkout develop && git pull origin develop
git merge main
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

With that in place, step 7 (`git push origin main --tags`) triggers the publish, and
this section is deleted.
