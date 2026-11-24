#!/bin/bash
# Weekly run of the refactor-analyst agent (.claude/agents/refactor-analyst.md).
# By default: an interactive session in worktree ../<repo>-refactor-audit on bugfix/refactor-uplift-<date> (opened
# in Herdr when run inside it), with its own Poetry venv. The agent reports the structural findings, asks which to
# pursue, then makes small/local/mechanically-safe fixes directly and hands back anything structural (package
# extraction, directory reshuffle) as a speckit-specify candidate instead of attempting it.
# --report-only: the unattended report in .cache/refactor-audit/<date>.md; fixes nothing and opens no PR.
#
# Usage: scripts/refactor_audit_weekly.sh [--report-only] [git-ref] [scope]
#   git-ref  branch/tag to assess (default: develop)
#   scope    free-text focus, e.g. "src/frictionless_architect/visualizer" or "platform/ only" (default: whole codebase)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"
agent_parse_flags "$@"; set -- "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}"

REF="${1:-develop}"
SCOPE="${2:-}"

AGENT=refactor-analyst
OUT_NAME=refactor-audit
BRANCH="bugfix/refactor-uplift-$(date +%F)"
SETUP="venv"
FIX_TASK="Follow your 'Fixing chosen findings' section for the chosen findings: make the small/local/mechanically-safe \
changes, run the local gate (ruff, pyright, mypy, the affected pytest paths), then commit. For anything structural, \
do not attempt it — hand back the speckit-specify candidate instead and say so in the commit list."
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*),Bash(poetry run ruff check:*),\
Bash(poetry run pyright:*),Bash(poetry run mypy:*),Bash(poetry run pytest:*)"
TASK="Follow your Steps 1-5 and Output sections for the review. Do not run poetry commands in this phase. \
Put the findings table under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"
[ -z "$SCOPE" ] || { TASK="$TASK Scope: $SCOPE."; STAMP="$(date +%F)-$(tr -c 'A-Za-z0-9' '-' <<< "$SCOPE" | sed 's/-*$//')"; }

agent_workdir
agent_run
