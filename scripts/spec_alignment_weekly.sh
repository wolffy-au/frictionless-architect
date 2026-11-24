#!/bin/bash
# Weekly run of the spec-alignment agent (.claude/agents/spec-alignment.md).
# By default: an interactive session in worktree ../<repo>-spec-alignment on feature/spec-alignment-<date> (opened
# in Herdr when run inside it), with its own Poetry venv. The agent reports the gaps, asks which to pursue, then
# fixes documentation/model/spec-text findings directly and hands back genuinely Missing/Partial requirements as
# speckit-specify candidates instead of implementing them.
# --report-only: the unattended report in .cache/spec-alignment/<date>.md; fixes nothing and opens no PR.
#
# Usage: scripts/spec_alignment_weekly.sh [--report-only] [git-ref] [spec]
#   git-ref  branch/tag to check (default: develop)
#   spec     spec directory prefix to focus on, e.g. "001" or "002-neo4j" (default: all of specs/)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"
agent_parse_flags "$@"; set -- "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}"

REF="${1:-develop}"
SPEC="${2:-}"

AGENT=spec-alignment
OUT_NAME=spec-alignment
BRANCH="feature/spec-alignment-$(date +%F)"
SETUP="venv"
FIX_TASK="Follow your 'Fixing chosen findings' section for the chosen findings: edit spec/model/ADR text for \
documentation-level findings, re-run the Step 4 check it came from to confirm it now passes, then commit. For any \
chosen finding that is a Missing/Partial/Diverged requirement, do not implement it — hand back the speckit-specify \
candidate instead and say so in the commit list."
TOOLS="Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*),Bash(git tag:*),Bash(gh api:*),\
Bash(poetry run python architecture/model/build.py)"
TASK="Follow your Steps 1-5 and Output sections for the review. Do not run poetry commands in this phase. \
Put the ranked gap findings under '## Findings'."
TASK="$TASK $AGENT_BASH_RULE"

if [ -n "$SPEC" ]; then
  [[ "$SPEC" =~ ^[A-Za-z0-9._-]+$ ]] || agent_fail "invalid spec '$SPEC' (expected e.g. 001 or 002-neo4j)"
  git -C "$(git rev-parse --show-toplevel)" ls-tree --name-only "$REF" specs/ | grep -q "^specs/$SPEC" \
    || agent_fail "no specs/$SPEC* directory at $REF"
  TASK="$TASK Focus only on the requirements in specs/$SPEC*, plus the constitution gates that touch them."
  STAMP="$(date +%F)-spec-$SPEC"
fi

agent_workdir
agent_run
