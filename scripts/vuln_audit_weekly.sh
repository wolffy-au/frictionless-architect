#!/bin/bash
# Report-only run of the vulnerability-remediator agent (.claude/agents/vulnerability-remediator.md).
# Writes the advisory table to .cache/vuln-audit/<date>.md; bumps no dependency, edits no lock file, opens no PR.
# Runs in the CURRENT checkout, not a temp worktree: the scanners need the Poetry venv and gh/Snyk auth.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/vuln_audit_weekly.sh

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

AGENT=vulnerability-remediator
OUT_NAME=vuln-audit
MODE=root
TOOLS="Read,Grep,Glob,Bash(gh api repos/*/dependabot/alerts*),Bash(poetry run pip-audit:*),Bash(poetry run snyk test:*),Bash(poetry run snyk code test:*),Bash(poetry show:*),Bash(poetry check:*),Bash(git log:*)"
TASK="Follow your Steps 2-3 only: skip Steps 1 and 4-9. Gather advisories from every scanner that is available \
(Dependabot via gh api, pip-audit, Snyk); if one is unavailable, say so in the report rather than failing. \
Do not read .secrets/, run poetry add/lock/update, or install anything. Instead of remediating, give the Output \
advisory table (advisory ID | package/file | severity | current -> fixed | recommended action) plus the unresolved \
list, under '## Findings'."

agent_report_run
