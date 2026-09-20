# Contributing to frictionless-architect

Thanks for taking the time to contribute. This document covers how work
actually happens in this repo: the toolchain, branch/commit conventions, the
spec-driven workflow, and the quality gates a change has to clear. For the
project's shape and rationale, start with [`README.md`](README.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md), and
[`PROJECT_SPECIFICATION.md`](PROJECT_SPECIFICATION.md). Day-to-day development
guidance for both human and AI-agent contributors lives in
[`AGENTS.md`](AGENTS.md) — this file is the narrative front door to it.

By participating in this project you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- Check open [issues](../../issues) and [pull requests](../../pulls) so you're
  not duplicating work in flight.
- For anything non-trivial, open an issue first (use the **User story**,
  **Feature request**, or **Bug report** template under
  `.github/ISSUE_TEMPLATE/`) so the approach can be discussed before code is
  written.
- Security vulnerabilities are **not** reported via public issues — see
  [`SECURITY.md`](SECURITY.md).

## Toolchain

- **Poetry only** for dependency management — never `uv` (see
  [`ARCHITECTURE.md`](ARCHITECTURE.md) §5). `poetry install` installs the
  project and all dependency groups (`dev`, `tests`, `lint`, `docs`).
- Python 3.12 (supported range `>=3.11,<3.14`).
- Lint / types: `ruff`, `pyright`, `mypy`. Tests: `pytest` (+ `pytest-cov`),
  `behave`.
- Run everything through `poetry run …` or `poetry env activate`.

```bash
poetry install                       # project + all dependency groups
poetry run pytest                    # full test suite
bash scripts/pre_commit_checks.sh    # fast gate: lock refresh, pymarkdown, ruff, pyright, mypy, tests/unit/
bash scripts/pre_merge_checks.sh     # + behave, coverage-gated pytest, frontend UI harness
```

Pre-commit hooks are installed (`.pre-commit-config.yaml`): fast autofix on
commit, type/test suite on push, Conventional Commits check on the message.

## Branching and commits

- Work on `feature/**` or `bugfix/**` branches — never directly on `main` or
  `develop`.
- Commit messages follow **Conventional Commits**, enforced by commitizen.
  Use the `commit-message` skill for the ruleset, or the `commit-auditor`
  agent to check a whole branch before opening a PR. Tags are `v$version`
  (`cz bump` owns `CHANGELOG.md` and the tag).
- Keep spelling consistent: code identifiers, module/package names, paths,
  and route segments use `visualizer` (`-z-`); running prose uses the en-GB
  `visualiser` (`-s-`). Seeing both in one sentence is intentional.

## Repository layout

- **Root** — governance and orchestration only:
  `PROJECT_SPECIFICATION.md`, `.specify/memory/constitution.md`,
  `ARCHITECTURE.md`, `TECHNICAL.md`, `RELEASE.md`.
- `src/frictionless_architect/` — application code (`visualizer/`, `schema/`).
- `tests/` — mirrors the `src/` package layout: `tests/unit/<pkg>/test_<mod>.py`
  for `src/frictionless_architect/<pkg>/<mod>.py`. Also `tests/api/`
  (in-process FastAPI) and `tests/features/` (behave). See `TECHNICAL.md` →
  "Testing Layout".
- `.claude/skills/` and `.claude/agents/` — the skill and subagent catalogs
  (tracked in git despite living under `.claude/`).
- `.specify/` — Spec Kit machinery; `specs/` — feature specs.
- `docs/adr/` — Architecture Decision Records (MADR format).

## Spec-driven feature work

Non-trivial features go through the Spec Kit workflow rather than straight to
code:

`speckit-specify` → `speckit-clarify` → `speckit-plan` → `speckit-tasks` →
`speckit-implement`, checked against
[`.specify/memory/constitution.md`](.specify/memory/constitution.md).

Each skill is documented in [`.claude/skills/README.md`](.claude/skills/README.md).
If you're contributing without the Claude Code tooling, the same phases still
apply conceptually: write down what and why before how, get it reviewed, break
it into ordered tasks, then implement against them.

## Architecture decisions

Record any load-bearing choice as an ADR under [`docs/adr/`](docs/adr/README.md)
(MADR-lite format, `docs/adr/0000-adr-template.md` is the template). Set
`Status: Proposed` on the PR that introduces the decision; it flips to
`Accepted` once agreed. The `adr-auditor` agent sweeps for decisions made
without a record — running clean against it is part of the release gate.

## Submitting a pull request

1. Fork the repo (or branch directly if you have write access) and create a
   `feature/**` or `bugfix/**` branch.
2. Make your change, with tests. New behaviour needs new tests; bug fixes
   need a regression test that fails before the fix and passes after.
3. Run `bash scripts/pre_commit_checks.sh` locally before pushing; run
   `bash scripts/pre_merge_checks.sh` before opening the PR if your change
   touches diagrams, the frontend harness, or coverage-sensitive code.
4. Update relevant docs (`README.md`, `ARCHITECTURE.md`, wiki pages, ADRs) in
   the same PR as the code change — the `docs-uplift` agent exists to help
   catch what's missed, not to replace doing it.
5. Open the PR against `main` (or `develop`, per current release state — see
   [`RELEASE.md`](RELEASE.md)) using the relevant issue template's structure
   in the description. Link the issue it closes.
6. A green CI run and at least one review are required before merge.

## Code style

Follow standard Python conventions; `ruff`, `pyright`, and `mypy` enforce the
specifics (see `pyproject.toml` for configuration). Don't fight the linters —
if a rule seems wrong for a specific case, raise it rather than silently
suppressing it.

## Questions

Open a [discussion or issue](../../issues) if anything here is unclear —
that's useful signal that this document needs updating.
