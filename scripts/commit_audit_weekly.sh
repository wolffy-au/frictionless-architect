#!/bin/bash
# Weekly run of the commit-auditor agent (.claude/agents/commit-auditor.md).
# By default: an interactive session in worktree ../<repo>-commit-audit (detached at the target, unless the target
# is a real non-default branch — see below), opened in Herdr when run inside it. The agent audits, asks which
# findings you care about, then rewords only the ones not yet pushed to a remote; an already-published commit
# (the usual case for `develop`) stays report-only — rewriting that would need a force-push, which this repo bans.
# --report-only: the unattended report in .cache/commit-audit/<date>.md.
#
# Usage: scripts/commit_audit_weekly.sh [--report-only] [target] [base]
#   target  branch/tag to audit (default: develop)
#   base    ref the range starts from (default: the last release tag reachable from target, else main)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"
agent_parse_flags "$@"; set -- "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}"

REF="${1:-develop}"
BASE="${2:-}"

if [ -z "$BASE" ]; then
  BASE="$(git describe --tags --abbrev=0 "$REF" 2>/dev/null || echo main)"
fi
git rev-parse --verify --quiet "$BASE^{commit}" >/dev/null || agent_fail "base ref '$BASE' not found"
git rev-parse --verify --quiet "$REF^{commit}" >/dev/null || agent_fail "target ref '$REF' not found"

AGENT=commit-auditor
OUT_NAME=commit-audit
STAMP="$(date +%F)-${BASE//\//_}..${REF//\//_}"
# develop/main are almost always fully published by audit time, and are usually checked out in the main worktree
# already, so stay detached for them (a fix there drops back to reporting, by the agent's own rules). A real
# feature/bugfix branch passed as $REF, though, is exactly the case where unpushed commits can be fixed in place —
# attach the worktree to it so a rebase there actually moves the branch ref you'll push yourself.
case "$REF" in
  develop|main) ;;
  *) BRANCH="$REF" ;;
esac
FIX_TASK="Follow your Steps 5 and 'Fixing chosen findings' for the chosen findings: rewrite only the commits Step 5 \
found not yet published, verify with cz check after, and report the new SHAs. For any chosen finding that turns out \
to be published, give the corrected message and say it cannot be rewritten in place — never force-push."
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git merge-base:*),Bash(git rev-list:*),Bash(git show:*),Bash(git describe:*),\
Bash(git for-each-ref:*),Bash(git branch -r --contains*),Bash(git rebase:*),Bash(git commit --amend*),\
Bash(poetry run cz check:*)"
TASK="Audit the range $BASE..$REF with base=$BASE and target=$REF. Follow your Steps 1, 3, 4 and 5 for the review; \
skip Step 2 (do not run poetry or cz, evaluate the ruleset by hand). For subject length, regex, casing and punctuation \
checks, evaluate the subjects already listed in Step 1 by reading them — do not shell out to 'git log --grep' or any \
other regex-bearing Bash command; those get denied under this run's tool allowlist and will fail the whole run. \
Put the per-commit results, including each commit's published/unpublished state, under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"

agent_workdir
agent_run
