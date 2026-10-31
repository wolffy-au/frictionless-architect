---
name: pr-preflight
description: 'Pre-flight checklist for a branch about to become a PR — refresh docs/wiki/diagrams against the real diff, run an autofix pass, confirm the quality/security/commit gates, open the PR as a draft, then watch CI and fix failures before marking it ready for human review. Use for "get this ready for a PR", "preflight this branch", "/pr-preflight".'
allowed-tools: Bash(gh pr create:*)
---

# pr-preflight

Run this on a `feature/**` / `bugfix/**` branch once the code changes are done, before
opening (or pushing further commits to) its PR. It is the mirror image of `pr-wrapup`:
that skill cleans up *after* a PR lands; this one gets a branch *into* PR-worthy shape
first. Narrower than a full release gate (`RELEASE.md`) — scoped to this branch's own
diff, not the whole repo — and lighter than the `scripts/*_weekly.sh` audits, which
review the whole codebase/history on a schedule with a human picking findings.

Nothing here is destructive and everything stays on the current branch: no merges, no
pushes to `develop`/`main`, no issue/PR state changes. Commit as you go, in focused
Conventional Commits (`commit-message` skill ruleset) — don't bundle the whole preflight
into one commit.

Inputs: nothing required. Optionally a base ref to diff against (default: where the
branch forked from `develop`, via `git merge-base HEAD origin/develop`).

## 1. Scope the diff

```bash
git fetch origin develop
BASE="$(git merge-base HEAD origin/develop)"
git diff --stat "$BASE"...HEAD
git log --oneline "$BASE"..HEAD
```

Everything below is scoped to the files this range touches — this is a preflight for
*this branch's* change, not a repo-wide sweep. If the branch is still mid-work (code
changes clearly unfinished), say so and stop; don't run the rest against a half-built
diff.

## 2. Autofix pass

Run the project's own autofix tools over the touched files before any manual review, so
style/lint noise doesn't show up as review comments:

```bash
bash scripts/pre_commit_checks.sh
```

This already runs `ruff check --fix` / `ruff format`, pyright, mypy and the unit suite
(`AGENTS.md` → Commands). If it reports fixes applied, re-stage and commit them as their
own `style:`/`fix:` commit before continuing.

For a deeper pass than the lint-level autofix — reuse/simplification/efficiency cleanups
and correctness bugs in the diff itself — run the `code-review` skill with `--fix` scoped
to this branch's diff (this is the `/autofix-pr`-style step: no such slash command exists
in this repo today, so `code-review --fix` is the closest equivalent; if one gets
added later, prefer it here instead):

```text
/code-review --fix HEAD
```

Review what it changed before committing — `--fix` applies findings to the working tree,
it doesn't commit for you.

## 3. Refresh documentation and diagrams for what this branch touched

Scoped versions of the checks `docs_audit_weekly.sh` and `wiki_audit_weekly.sh` run on a
schedule for the whole repo — here, pointed only at this branch's diff:

- **Docstrings / README / feature guides / `AGENTS.md`**: if the diff adds or changes
  public functions, classes, routes, or user-facing behaviour, check their docstrings and
  any prose docs that describe them are still accurate. Use the `docs-uplift` agent,
  scoped to the touched paths (`git diff --name-only "$BASE"...HEAD`), rather than letting
  it sweep the whole repo:
  > "Review only these files for doc drift: `<paths>`. Follow your Steps 2-6."
- **Diagrams**: if the diff touches `architecture/model/` (elements/relationships/views)
  or anything a PlantUML/ArchiMate/C4 diagram depicts, regenerate and validate the
  affected ones (`model-archimate` validate → `diagram-archimate` / `diagram-c4` /
  `diagram-plantuml` render) rather than leaving stale `.svg`/`.puml` output committed
  alongside changed source.
- **Wiki**: if the diff touches a file or doc a `wiki/sources.yaml` topic sources from,
  run the `wiki-librarian` skill on just that topic (not a full repo rebuild) so `wiki/`
  doesn't go stale the moment this PR merges. Skip entirely if nothing touched sources a
  topic.

Commit regenerated artefacts separately from the autofix commit, e.g.
`docs: refresh docs/diagrams for <this change>`.

## 4. Spec and ADR check

- If the branch implements or changes behaviour a spec under `specs/**` describes, confirm
  the spec still matches (or update it) — this is `spec-alignment`'s check, scoped to the
  one spec this branch is for rather than the whole tree.
- If the branch makes a load-bearing choice with no ADR behind it yet (new dependency,
  new architectural boundary, a reversal of a prior decision), file one now rather than
  letting `adr-auditor`'s weekly sweep catch it after the fact (`AGENTS.md` → Conventions).

## 5. Commit message check

```bash
poetry run python scripts/check_commit_messages.py --range "$BASE"..HEAD
```

Fixes what `commit_audit_weekly.sh` / `commit-auditor` would otherwise flag after the
fact. Reword any non-conforming commit now, while the branch is still yours to rewrite —
`pr-wrapup` and the repo's own hooks assume this is already clean by the time a PR opens.

## 6. Quality and security spot-check

Not a substitute for CI or the weekly `quality_audit_weekly.sh` / `vuln_audit_weekly.sh`
sweeps — just enough to not open a PR with an obvious, already-known issue:

```bash
poetry run ruff check .
poetry run pyright
poetry run mypy .
gh api repos/{owner}/{repo}/dependabot/alerts --jq '[.[] | select(.state=="open")]'
```

If this surfaces something non-trivial to fix (a real Sonar-style smell, an open
advisory), don't fix it inline here — hand it to `quality-uplift` / `vulnerability-remediator`
and note the follow-up in the PR description rather than scope-creeping the branch.

## 7. Final gate, push, and open the PR as a draft

```bash
bash scripts/pre_merge_checks.sh
git push origin HEAD
gh pr create --base develop --fill --draft   # or update the existing PR
```

If `pre_merge_checks.sh` fails, fix and re-run — don't push a red branch. Open as a
**draft**: the PR exists so CI runs against it, but it isn't yet asking anyone for
review — that only happens once §8 is clean.

## 8. Watch CI and fix before requesting review

```bash
gh pr checks --watch
```

CI (`.github/workflows/ci.yml`) re-runs ruff/pyright/mypy/behave/pytest+coverage plus
SonarQube and Snyk/CodeQL — gates §§2 and 6 only spot-checked locally. For any failing
check:

```bash
gh run view --log-failed
```

Fix the cause on this branch, commit (small, focused — same Conventional Commits
discipline as everywhere else in this skill), push, and re-watch. Repeat until green.

Stop and hand back instead of looping forever if a failure is genuinely outside this
skill's remit (unrelated flake, missing secret, a fix that would need a major/breaking
dependency bump) — report it in the PR description rather than forcing a fix.

Once every check is green, mark the PR ready for human review:

```bash
gh pr ready
```

This is the point the branch is actually asking someone to look at it. Before this,
nothing here requests review.

## Guardrails

- Everything stays on the current branch; never touch `develop`/`main` directly from here.
- Scope every check to this branch's diff (`git merge-base HEAD origin/develop`), not the
  whole repo — that's what the weekly audits and `RELEASE.md`'s release gate are for.
- Commit in small, focused Conventional Commits as each step finishes, not one giant
  "preflight" commit.
- If a step surfaces something bigger than this branch's scope (a repo-wide doc gap, a
  structural refactor idea, a vulnerability in an unrelated dependency), note it as a
  follow-up rather than pulling it into this PR.
- Don't push and open the PR (§7) until §§2-6 are clean.
- The PR opens as a **draft** and only gets marked ready (§8) once CI is green — never
  call `gh pr ready` while a check is still red or hasn't run yet.
- Never merge; `pr-preflight`'s job ends at `gh pr ready` — the merge decision stays human.
