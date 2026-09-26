---
name: pr-wrapup
description: 'Wrap up a GitHub issue and its PR once the PR is merged — verify the merge, delete the remote branch, close the issue with a summary comment, remove the local worktree and branches, prune, and report leftovers. Use for "PR merged, clean up", "wrap up issue #N", "/pr-wrapup <PR#>".'
---

# pr-wrapup

Post-merge housekeeping for one PR and the issue(s) it fixes. Every destructive step is
gated on **proof the work is in the base branch** — never delete a branch or worktree on
the strength of "the user said it merged".

Inputs: a PR number (preferred) or an issue number (find the PR with
`gh pr list --state merged --search "<issue#>"`). Always pass
`-R wolffy-au/frictionless-architect` to `gh` — the worktrees can trip git's
"dubious ownership" check, which makes `gh` fail to infer the repo.

## 1. Verify the merge

```bash
gh pr view <PR> -R wolffy-au/frictionless-architect \
  --json state,mergedAt,mergeCommit,baseRefName,headRefName,headRefOid,closingIssuesReferences,url
```

- `state` must be `MERGED`. Anything else → stop and report.
- Note `baseRefName`. Feature/bugfix PRs target **`develop`**; GitHub only auto-closes
  `Closes #N` issues on the default branch (`main`), so for a `develop` PR the issue is
  still open and step 3 is required.
- `git fetch --prune origin`, then prove the local branch holds nothing unmerged:
  - local tip == `headRefOid` (nothing committed locally after the PR's last push), **and**
  - `git merge-base --is-ancestor <headRefOid> origin/<base>` succeeds (merge commit /
    rebase-merge). For a **squash** merge that check fails by design — instead confirm
    `git diff <headRefOid> <mergeCommit> --stat` is empty or only shows changes that
    landed on the base after the branch point.
  - Any local-only commits or an unexplained diff → stop and show them.

## 2. Delete the remote branch

Skip if GitHub already deleted it (`git ls-remote --heads origin <head>` is empty).

```bash
git push origin --delete <headRefName>
```

## 3. Close the issue with a comment

For each linked issue still `OPEN` (`gh issue view <N> --json state`):

- Draft a short comment in the scratchpad:
  ``Fixed by #<PR> (merged into `<base>` as <short mergeCommit>).`` plus one to three lines on what changed and any ADR / follow-up
  issue. Reuse the PR body's summary; don't restate the whole PR.
- Show the draft to the user, then:

```bash
gh issue close <N> -R wolffy-au/frictionless-architect --reason completed \
  --comment "$(cat <scratchpad>/issue-<N>-close.md)"
```

If the issue was already closed (default-branch PR), don't add a duplicate comment.

## 4. Remove the local worktree

Run from the **main checkout** (`/workspaces/frictionless-architect`), never from inside
the worktree being removed — the session's cwd disappears with it, so use absolute paths
from here on.

```bash
git worktree list                        # find the worktree for <headRefName>
git -C <worktree> status --porcelain     # must be empty; otherwise stop and show it
git worktree remove <worktree>
```

On this drvfs mount `git worktree remove` often unregisters the worktree but fails to
delete the directory (`Permission denied`). After checking the path is exactly the
worktree you meant (not the main checkout, not a sibling), finish with
`sudo rm -rf <worktree>` and then `git worktree prune`.

## 5. Delete local branches

```bash
git branch -d <headRefName>     # -D only after step 1 proved it merged (squash merges need -D)
```

Also delete any scratch branches made for this work (e.g. `backup/<issue>-before-reword`)
— list them with `git branch --list '*<issue#>*'`, show the user, and delete with `-D`.

If git fails with `could not lock config file .git/config: Operation not permitted`
(drvfs EPERM when removing upstream tracking), repeat the command as
`sudo git -c safe.directory='*' <command>`.

## 6. Prune and report

```bash
git worktree prune
git fetch --prune origin
git -C /workspaces/frictionless-architect status -sb   # is local <base> behind?
```

Finish with a short report of what was done (with SHAs), then the **leftovers**:

- local `<base>` behind `origin/<base>` → suggest `git pull --ff-only` (don't run it if
  the checkout has uncommitted or staged changes that aren't yours).
- follow-ups listed in the PR body (open issues for them if the user agrees).
- generated docs that now describe stale behaviour (`wiki/` pages → a `wiki-librarian`
  run; `wiki-maintenance` can confirm which).
- advisories from `commit-auditor` or reviewers that weren't acted on.
- CI checks that were red but accepted (e.g. Snyk quota), so they aren't mistaken for
  new failures later.

## Guardrails

- Remote actions (branch delete, issue comment/close) are outward-facing: confirm with
  the user once for the set, unless they already asked for exactly these steps.
- Never force-delete a branch, `rm -rf` a directory, or close an issue before step 1
  passes.
- Never touch changes you didn't make in the main checkout (stray staged files, other
  worktrees) — report them instead.
- Don't reopen, edit, or re-merge the PR; this skill only tidies up after it.
