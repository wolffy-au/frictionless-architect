#!/bin/bash
# Weekly run of the docs-uplift agent (.claude/agents/docs-uplift.md).
# By default: an interactive session in worktree ../<repo>-docs-audit on feature/docs-uplift-<date> (opened in Herdr
# when run inside it). The agent lists the documentation drift, asks which items to fix, then fixes and commits those.
# --report-only: the unattended drift list in .cache/docs-audit/<date>.md; changes no docs, diagrams or branches.
#
# Usage: scripts/docs_audit_weekly.sh [--report-only] [git-ref] [scope]
#   git-ref  branch/tag to audit (default: develop)
#   scope    free-text focus, e.g. "docstrings only" or "diagrams only" (default: full sweep)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"
agent_parse_flags "$@"; set -- "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}"

REF="${1:-develop}"
SCOPE="${2:-}"

AGENT=docs-uplift
OUT_NAME=docs-audit
BRANCH="feature/docs-uplift-$(date +%F)"
SETUP="venv"
FIX_TASK="Follow your Steps 2-7 (docstrings, prose, feature coverage, diagrams, lint, commit) for the chosen findings; \
render and validate any diagram you change."
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*)"
TASK="Run the review part of your Steps 2-5 only: skip Steps 1 and 6-11 and do not render diagrams or run poetry. \
Instead of fixing, list each stale or missing docstring, prose doc, feature-coverage gap and out-of-date diagram \
with its file and what is wrong, ranked by how far it has drifted. Put them under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"
[ -z "$SCOPE" ] || { TASK="$TASK Scope: $SCOPE."; STAMP="$(date +%F)-$(tr -c 'A-Za-z0-9' '-' <<< "$SCOPE" | sed 's/-*$//')"; }

agent_workdir
agent_run
