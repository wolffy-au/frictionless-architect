#!/bin/bash
# Weekly run of the refactor-analyst agent (.claude/agents/refactor-analyst.md).
# By default: an interactive session in worktree ../<repo>-refactor-audit, detached at the ref (opened in Herdr when
# run inside it). The agent is read-only: it reports the structural findings, asks which to pursue, and hands those
# back as speckit-specify candidates or ready-to-file issues. --report-only: the unattended report in
# .cache/refactor-audit/<date>.md.
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
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*)"
TASK="Follow your Steps 1-5 and Output sections. Do not run poetry commands. Put the findings table under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"
[ -z "$SCOPE" ] || { TASK="$TASK Scope: $SCOPE."; STAMP="$(date +%F)-$(tr -c 'A-Za-z0-9' '-' <<< "$SCOPE" | sed 's/-*$//')"; }

agent_workdir
agent_run
