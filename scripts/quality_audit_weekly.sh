#!/bin/bash
# Report-only run of the quality-uplift agent (.claude/agents/quality-uplift.md).
# Writes the Sonar-style smell report to .cache/quality-audit/<date>.md; fixes nothing and opens no PR.
# Runs in the CURRENT checkout, not a temp worktree: ruff/pyright/mypy need the Poetry venv.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/quality_audit_weekly.sh [scope]
#   scope  path or module to focus on, e.g. src/frictionless_architect/visualizer (default: src/ and tests/)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

SCOPE="${1:-}"

AGENT=quality-uplift
OUT_NAME=quality-audit
MODE=root
TOOLS="Read,Grep,Glob,Bash(poetry run ruff check:*),Bash(poetry run pyright:*),Bash(poetry run mypy:*),Bash(git log:*),Bash(git diff:*)"
TASK="Follow your Steps 2-3 only: skip Steps 1 and 4-10. Run ruff, pyright and mypy for the baseline (do not use --fix), \
then hunt for the smells in Step 3. Do not supply or fetch a Sonar payload. Instead of fixing, list each issue as \
file:line | rule/smell | suggested fix, ranked by severity, under '## Findings'."
if [ -n "$SCOPE" ]; then
  TASK="$TASK Scope: $SCOPE only."
  STAMP="$(date +%F)-$(tr -c 'A-Za-z0-9' '-' <<< "$SCOPE" | sed 's/-*$//')"
fi

agent_report_run
