#!/bin/bash
# Report-only run of the adr-auditor agent (.claude/agents/adr-auditor.md), via the shared driver _agent_report.sh.
# Writes the findings to .cache/adr-audit/<date>.md; creates no branch, commit or PR.
# Exits non-zero if claude fails, any tool call was denied, or the report is missing its findings.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/adr_audit_weekly.sh [git-ref] [adr-list]
#   git-ref   branch/tag to audit (default: develop)
#   adr-list  comma-separated ADR numbers to focus on, e.g. "14,31" or "0014,0031" (default: all)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

cd "$(git rev-parse --show-toplevel)"

REF="${1:-develop}"
ADRS="${2:-}"

git rev-parse --verify --quiet "$REF^{commit}" >/dev/null || agent_fail "unknown git ref '$REF'"

# Optional focus: normalise "14, 31" -> "0014,0031" and make sure each ADR exists at REF.
SCOPE="Audit the whole ADR log."
STAMP="$(date +%F)"
if [ -n "$ADRS" ]; then
  NORMALISED=""
  IFS=',' read -ra NUMS <<< "$ADRS"
  for n in "${NUMS[@]}"; do
    n="${n//[[:space:]]/}"
    [[ "$n" =~ ^[0-9]+$ ]] || agent_fail "invalid ADR number '$n' (expected e.g. 14,31)"
    n="$(printf '%04d' "$((10#$n))")"
    git ls-tree --name-only "$REF" docs/adr/ | grep -q "^docs/adr/$n-.*\.md$" || agent_fail "ADR-$n not found in docs/adr/ at $REF"
    NORMALISED="${NORMALISED:+$NORMALISED,}$n"
  done
  SCOPE="Focus only on ADR-${NORMALISED//,/, ADR-}: inventory, staleness, ADR-vs-ADR conflicts and un-recorded decisions that touch them. Ignore other records unless they conflict with these."
  # Output names: <date>.* for the whole log, <date>-adr-0017-0018.* for a focused run.
  STAMP="$STAMP-adr-${NORMALISED//,/-}"
fi

AGENT=adr-auditor
OUT_NAME=adr-audit
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*),Bash(git submodule status)"
TASK="Follow your Steps 2-6, skip Steps 1 and 7-11. $SCOPE $AGENT_BASH_RULE Report the final Output section."

agent_report_run
