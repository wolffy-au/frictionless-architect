#!/bin/bash
# Report-only run of the docs-uplift agent (.claude/agents/docs-uplift.md).
# Lists the documentation drift it would fix in .cache/docs-audit/<date>.md; changes no docs, diagrams or branches.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/docs_audit_weekly.sh [git-ref] [scope]
#   git-ref  branch/tag to audit (default: develop)
#   scope    free-text focus, e.g. "docstrings only" or "diagrams only" (default: full sweep)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

REF="${1:-develop}"
SCOPE="${2:-}"

AGENT=docs-uplift
OUT_NAME=docs-audit
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*)"
TASK="Run the review part of your Steps 2-5 only: skip Steps 1 and 6-11 and do not render diagrams or run poetry. \
Instead of fixing, list each stale or missing docstring, prose doc, feature-coverage gap and out-of-date diagram \
with its file and what is wrong, ranked by how far it has drifted. Put them under '## Findings'."
[ -z "$SCOPE" ] || { TASK="$TASK Scope: $SCOPE."; STAMP="$(date +%F)-$(tr -c 'A-Za-z0-9' '-' <<< "$SCOPE" | sed 's/-*$//')"; }

agent_report_run
