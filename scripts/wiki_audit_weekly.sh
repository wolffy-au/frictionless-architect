#!/bin/bash
# Weekly run of the wiki-maintenance agent (.claude/agents/wiki-maintenance.md).
# By default: an interactive session in worktree ../<repo>-wiki-audit on feature/wiki-audit-<date> (opened in Herdr
# when run inside it), with its own Poetry venv and initialised third_party submodules. The agent runs the checks, asks
# which findings to fix, then fixes and commits those: missing index.md links directly, stale/new/orphan pages by
# running the wiki-librarian skill on their topics, and any sources.yaml change you chose.
# --report-only: the unattended audit in .cache/wiki-audit/<date>.md, applying no fix. It runs in the CURRENT
# checkout, not a temp worktree: the wiki tools need the Poetry venv, the initialised third_party submodules and
# wiki/.cache. Run it from a checkout whose wiki/ is the one you want audited.
#
# Usage: scripts/wiki_audit_weekly.sh [--report-only]

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"
agent_parse_flags "$@"; set -- "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}"

AGENT=wiki-maintenance
OUT_NAME=wiki-audit
MODE=root
BRANCH="feature/wiki-audit-$(date +%F)"
SETUP="venv submodules"
FIX_TASK="Follow your 'Fixing chosen findings' section for the chosen findings: fix missing index.md links directly, \
run the wiki-librarian skill on the chosen NEW/STALE/ORPHAN topics, and make only the sources.yaml changes I chose. \
Re-run build_status.py and verify_wiki.py to confirm the chosen topics are FRESH and clean."
TOOLS="Read,Grep,Glob,Bash(poetry run python .claude/skills/wiki-librarian/tools/*),Bash(wc:*),Bash(git log:*)"
TASK="Run all seven checks. The tools may write to wiki/.cache while they run; that is fine. Do not edit or create any file: \
where your rules say to fix a missing index.md link, report it instead. In the summary, replace 'what was fixed' with 'what needs a fix'. \
Put every check's results under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"

agent_workdir
agent_run
