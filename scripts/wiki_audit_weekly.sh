#!/bin/bash
# Weekly run of the wiki-maintenance agent (.claude/agents/wiki-maintenance.md).
# By default: an interactive session in worktree ../<repo>-wiki-audit on feature/wiki-audit-<date> (opened in Herdr
# when run inside it), with its own Poetry venv and initialised third_party submodules. The agent runs the checks, asks
# which findings to act on, applies the mechanical fixes (missing index.md links) and hands the rest back as
# librarian runs / sources.yaml decisions.
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
FIX_TASK="Apply only the mechanical bookkeeping your Rules allow (missing index.md links) for the chosen findings. \
For every other chosen finding, give the follow-up instead: which wiki-librarian topics to rebuild, or the sources.yaml \
decision needed."
TOOLS="Read,Grep,Glob,Bash(poetry run python .claude/skills/wiki-librarian/tools/*),Bash(wc:*),Bash(git log:*)"
TASK="Run all seven checks. The tools may write to wiki/.cache while they run; that is fine. Do not edit or create any file: \
where your rules say to fix a missing index.md link, report it instead. In the summary, replace 'what was fixed' with 'what needs a fix'. \
Put every check's results under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"

agent_workdir
agent_run
