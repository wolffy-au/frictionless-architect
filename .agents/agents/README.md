# Agents

Tool-neutral catalog of the subagents in this repo. Each is a single Markdown file
with YAML frontmatter (`name`, `description`, `tools`, `model`) followed by its
instructions. Agents that support it expose each by its `name`.

`.agents/agents/` is symlinked to `.claude/agents/` by the devcontainer.

## Maintenance agents

| Agent | Writes? | Purpose |
|-------|---------|---------|
| `commit-auditor` | read-only | Audit a branch's commits against Conventional Commits + repo conventions; per-commit report with corrected messages. Paired skill: `commit-message`. |
| `quality-uplift` | branch + PR | Fix SonarCloud-class quality issues (complexity, duplication, dead code, type gaps) locally before CI. Can consume a SonarCloud issue list. |
| `coverage-uplift` | branch + PR | Incrementally raise `pytest` coverage toward the 90% gate with real positive/negative tests. |
| `acceptance-author` | branch + PR | Transcribe a story/ticket/spec's acceptance criteria into `behave` scenarios kept close to verbatim, wire the steps, keep a criterion→scenario map. Owns `tests/features/`. |
| `docs-uplift` | branch + PR | Resync docstrings, README/quickstart/feature guides, and PlantUML/C4/ArchiMate diagrams with the code. |
| `vulnerability-remediator` | branch + PR | Resolve Dependabot / Snyk / SonarCloud security findings; bump or pin fixed versions, patch vulnerable code, verify gates. |
| `refactor-analyst` | read-only | Whole-codebase structural assessment vs `ARCHITECTURE.md` / `TECHNICAL.md`; prioritised recommendations, no code changes. |
| `spec-alignment` | read-only | Traceability gap report: code vs `PROJECT_SPECIFICATION.md`, `specs/**`, constitution. |
| `adr-auditor` | branch + draft PR | Audit `docs/adr/` against the decision-bearing docs and the code; report missing / stale / misaligned / superseded records, and draft `Status:Proposed` ADR stubs plus status edits. Never fleshes out or attests a decision. |
| `release-runner` | branch + tag + release | Run `RELEASE.md` end to end: gates, `cz bump`, tag, GitHub release, merge back. Stops on any red gate. |

The write-capable agents push a branch, open a PR against `develop`, then watch CI
(`.github/workflows/ci.yml`) and iterate on the same branch until every check is green —
CI gates (SonarQube, Snyk, coverage) routinely surface things the local pass misses.
They mark the PR ready but **never merge** — that stays a human decision. They hand back
early only when a failure is outside their remit (unrelated flake, missing secret).
`release-runner` pushes the tag and creates the release only after an explicit go-ahead.
`adr-auditor` is the exception: it opens a **draft** PR and leaves it draft, because its
proposed ADR stubs are deliberately incomplete — a human writes the decision and attests it.

## Conventions

- Toolchain is **Poetry**, never `uv`, matching `scripts/*.sh` and the repo's
  `poetry-over-uv` decision.
- Commit messages follow the `commit-message` skill's `references/standard.md`.
- Working branches: `feature/**` or `bugfix/**` (matches `.github/workflows/ci.yml`).
  Never work directly on `main` or `develop`.
