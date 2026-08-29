# Commit message standard (internal)

Baseline: **Conventional Commits 1.0.0**. Enforced by commitizen
(`[tool.commitizen]` in `pyproject.toml`, ruleset `cz_conventional_commits`).
This file records the repo-specific choices layered on top.

## Format

```
<type>(<scope>)?<!>?: <description>

<body>

<footers>
```

Only the subject line is mandatory.

## Types

| Type       | Use for                                                        | Bumps |
|------------|---------------------------------------------------------------|-------|
| `feat`     | a new capability, user- or agent-visible                       | minor |
| `fix`      | a bug fix                                                      | patch |
| `docs`     | documentation only (README, ARCHITECTURE, specs prose, skills) | –     |
| `style`    | formatting/whitespace, no code-behaviour change                | –     |
| `refactor` | code change that neither fixes a bug nor adds a feature        | –     |
| `perf`     | performance improvement                                        | patch |
| `test`     | adding or correcting tests only                                | –     |
| `build`    | build system, dependencies, packaging, devcontainer            | –     |
| `ci`       | CI config and scripts (`.github/`, workflows)                  | –     |
| `chore`    | maintenance that fits nothing above (lockfile pins, cleanup)   | –     |
| `revert`   | reverts a previous commit; body has `Refs: <sha>`              | –     |

A `!` before the colon, or a `BREAKING CHANGE:` footer, marks an incompatible
change and forces a major bump regardless of type.

## Scopes

Optional but expected when a change is localised. Lower-case, `[a-z0-9-]+`.

**Package scopes** — a member of the `platform/` Poetry monorepo, named by its
directory under `platform/packages/` (e.g. `knowledge-graph`, `schema-visualizer`).
Use the package directory name, not the Python module name.

**Area scopes** — cross-cutting parts of the repo:

- `agents` — `.agents/agents/` and `.agents/skills/`
- `skills` — a single skill when `agents` is too broad
- `devcontainer` — `.devcontainer/`
- `speckit` — Spec Kit integration, `.specify/`
- `specs` — feature specs under `specs/` or `packages/*/specs/`
- `architecture` — `ARCHITECTURE.md` and structural decisions
- `sample-data` — fixture/sample models
- `ci` — release/versioning plumbing
- `deps` — dependency bumps (`chore(deps):`, `build(deps):`)

Omit the scope for genuinely repo-wide changes. Add a new area scope to this list
in the same commit that first needs it.

## Subject rules

- imperative mood: "add", "fix", "remove" — not "added" / "adds"
- lower-case first word (after the colon)
- no trailing period
- ≤ 72 characters including the `type(scope):` prefix
- describe the change, not the file touched ("prevent duplicate scope" not
  "edit validator.py")

## Body

- required only when the reason for the change is not evident from the diff
- blank line between subject and body
- wrap at 72 columns
- explain *why* and any non-obvious *how*; the diff already shows *what*

## Footers

- `BREAKING CHANGE: <description + migration path>` — mandatory prose for any
  `!`-marked commit
- `Refs: #<n>`, `Closes: #<n>`, `Fixes: #<n>` — issue links
- `Co-Authored-By:` and `Claude-Session:` / harness trailers — keep as appended
- `Revert: <sha>` on `revert` commits

## Tags & versioning

- release tags are `v$version` (`tag_format = "v$version"`), PEP 440 /
  `poetry-dynamic-versioning`, semver style
- `cz bump` reads the log since the last tag, applies the bump implied by the
  types above, and updates the changelog (`update_changelog_on_bump = true`)
- never hand-edit the changelog or move a `v*` tag

## Tooling

```bash
poetry run cz check --message "<msg>"             # lint one message
poetry run cz check --rev-range <base>..HEAD      # lint a range
poetry run cz commit                              # interactive prompt
```

commitizen is declared in the `dev` dependency group (`poetry install --with dev`).
If `poetry run cz` does not work, fall back to the regex/checklist in the
`commit-message` skill.
