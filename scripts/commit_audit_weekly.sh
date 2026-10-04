#!/bin/bash
# Report-only run of the commit-auditor agent (.claude/agents/commit-auditor.md).
# Writes the conformance report to .cache/commit-audit/<date>.md; the agent is read-only already.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/commit_audit_weekly.sh [target] [base]
#   target  branch/tag to audit (default: develop)
#   base    ref the range starts from (default: the last release tag reachable from target, else main)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

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
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git merge-base:*),Bash(git rev-list:*),Bash(git show:*),Bash(git describe:*)"
TASK="Audit the range $BASE..$REF with base=$BASE and target=$REF. Follow your Steps 1 and 3-4; skip Step 2 (do not run poetry or cz, evaluate the ruleset by hand). Put the per-commit results under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"

agent_report_run
