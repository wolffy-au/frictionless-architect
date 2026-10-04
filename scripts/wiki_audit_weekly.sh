#!/bin/bash
# Report-only run of the wiki-maintenance agent (.claude/agents/wiki-maintenance.md).
# Writes the audit to .cache/wiki-audit/<date>.md; it does not even apply the agent's one mechanical fix
# (a missing index.md link) — that goes in the report instead.
# Runs in the CURRENT checkout, not a temp worktree: the wiki tools need the Poetry venv, the initialised
# third_party submodules and wiki/.cache. Run it from a checkout whose wiki/ is the one you want audited.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/wiki_audit_weekly.sh

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

AGENT=wiki-maintenance
OUT_NAME=wiki-audit
MODE=root
TOOLS="Read,Grep,Glob,Bash(poetry run python .claude/skills/wiki-librarian/tools/*),Bash(wc:*),Bash(git log:*)"
TASK="Run all seven checks. The tools may write to wiki/.cache while they run; that is fine. Do not edit or create any file: \
where your rules say to fix a missing index.md link, report it instead. In the summary, replace 'what was fixed' with 'what needs a fix'. \
Put every check's results under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"

agent_report_run
