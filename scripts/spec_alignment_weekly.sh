#!/bin/bash
# Report-only run of the spec-alignment agent (.claude/agents/spec-alignment.md).
# Writes the traceability report to .cache/spec-alignment/<date>.md; the agent is read-only already.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/spec_alignment_weekly.sh [git-ref] [spec]
#   git-ref  branch/tag to check (default: develop)
#   spec     spec directory prefix to focus on, e.g. "001" or "002-neo4j" (default: all of specs/)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

REF="${1:-develop}"
SPEC="${2:-}"

AGENT=spec-alignment
OUT_NAME=spec-alignment
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*)"
TASK="Follow your Steps 1-5 and Output sections. Do not run poetry commands. Put the ranked gap findings under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"

if [ -n "$SPEC" ]; then
  [[ "$SPEC" =~ ^[A-Za-z0-9._-]+$ ]] || agent_fail "invalid spec '$SPEC' (expected e.g. 001 or 002-neo4j)"
  git -C "$(git rev-parse --show-toplevel)" ls-tree --name-only "$REF" specs/ | grep -q "^specs/$SPEC" \
    || agent_fail "no specs/$SPEC* directory at $REF"
  TASK="$TASK Focus only on the requirements in specs/$SPEC*, plus the constitution gates that touch them."
  STAMP="$(date +%F)-spec-$SPEC"
fi

agent_report_run
