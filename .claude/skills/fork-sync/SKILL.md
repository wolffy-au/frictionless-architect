---
name: fork-sync
description: Keep forked GitHub dependencies in sync with upstream. Rebases fix/* and private/* branches onto the latest upstream, rebuilds a dist-candidate branch, runs tests, flags security-relevant upstream changes, and escalates conflicts instead of guessing. Use for "/fork-sync", "sync the forks", scheduled fork maintenance.
---

# fork-sync

Deterministic scripts do the mechanical work (fetch / rebase / rebuild / test) and
emit JSON + exit codes. This skill is the **orchestrator**: run the scripts, read
their output, and apply judgement only where a script escalated.

## When to use

- Interactive: `/fork-sync` (all forks) or `/fork-sync <name>` (one fork).
- Scheduled: a systemd/launchd/cron timer runs `dist/run-fork-sync.sh`, which calls
  `claude -p "/fork-sync"` headless. See `dist/README.md`.

## One-time setup

Run once per machine (idempotent):

```bash
.claude/skills/fork-sync/scripts/setup.sh
```

It enables `git rerere` globally, creates the workspace, clones every fork in
`forks.yml`, and wires the `upstream` + `fork` remotes and the `vendor-main` branch.

## The manifest

`forks.yml` is the single source of truth. Each fork declares its upstream URL,
your fork URL, the upstream branch to track, the ordered list of `fix_branches`
(PR'd upstream) and `private_branches` (never upstreamed), an optional `test_cmd`,
and `security_paths` globs. Edit this file to add/remove forks — never hard-code a
fork anywhere else.

## Workflow (per run)

1. `scripts/sync-all.sh` — or `scripts/sync-fork.sh <name>` for one.
   It prints one JSON object per fork plus a final summary object.
2. For each fork, branch on `status`:

   | status         | what it means                              | action |
   |----------------|--------------------------------------------|--------|
   | `up_to_date`   | upstream unchanged since last sync          | nothing |
   | `clean`        | candidate built + tests pass, pushed to fork | open a submodule-bump PR on the meta-repo (see below) |
   | `conflict`     | a branch would not rebase cleanly           | see **Conflicts** |
   | `test_failure` | candidate built but `test_cmd` failed        | file an issue with the captured output; do **not** promote |
   | `remote_error` | fetch/clone failed                          | file an issue; retry next run |
   | `config_error` | manifest/branch misconfigured               | file an issue; stop touching that fork |

3. Write `~/forks/REPORT.md` summarising every fork (status, commits pulled,
   security flags, candidate SHA). In headless runs this is the primary output.

## Conflicts

1. The script already tried `git rerere`. If it resolved everything the status is
   `clean`, not `conflict` — nothing for you to do.
2. If `conflict_files` intersects this fork's `security_paths`: **stop.** Do not
   attempt a resolution. File an issue titled `fork-sync: manual security-path
   conflict in <fork>` with the file list and leave the working tree as the script
   left it (mid-rebase is fine — `setup.sh` state is recoverable).
3. Otherwise you may resolve straightforward conflicts (import ordering, changelog
   collisions, adjacent-line edits). After resolving, re-run `sync-fork.sh <name>`
   to rebuild and test from the resolved state. `rerere` will remember it.
4. If a `fix_branch` conflicts because upstream merged an equivalent change, that
   branch is done: remove it from `forks.yml`, note it in the report, and re-run.

## Guardrails — never do these autonomously

- **Never** promote `dist-candidate-*` to the real `dist` branch. That is a manual
  step you take after reading the report: `git branch -f dist <candidate-sha> &&
  git push --force-with-lease fork dist`.
- **Never** open, push to, or comment on an **upstream** repo. PRs back to upstream
  are drafted for review only (branch + `references/pr-template.md`), never sent.
- **Never** resolve a conflict touching `security_paths`.
- **Never** `git push --force*` to anything except a `dist-candidate-*` branch on
  your own fork.
- **Never** edit files under the fork clones outside an active rebase.

## Submodule-bump PR (meta-repo)

For a `clean` fork whose candidate you have reviewed and promoted to `dist`:

```bash
gh issue create ... # or, if you maintain pins in this repo:
# update the pin file / submodule to the new dist SHA on a branch, then
gh pr create --title "chore(deps): bump <fork> to <short-sha>" --body-file -
```

The agent proposes this PR; a human merges it.

## Command reference

| script | purpose | key exit codes |
|---|---|---|
| `scripts/setup.sh` | one-time: rerere, clone, remotes | 0 ok / 3 remote / 4 config |
| `scripts/sync-fork.sh <name> [--dry-run]` | full cycle for one fork | 0 ok · 1 conflict · 2 test_failure · 3 remote · 4 config |
| `scripts/sync-all.sh [--dry-run]` | loop over the manifest | 0 all ok · 1 at least one non-clean |
| `scripts/check-upstream.sh <name>` | list new upstream commits + security flags | 0 ok · 3 remote · 4 config |
| `scripts/rebuild-dist.sh <name>` | rebuild candidate only (branches already rebased) | 0 ok · 1 conflict |

All scripts emit a JSON object on stdout; human-readable progress goes to stderr.
