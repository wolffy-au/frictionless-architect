#!/bin/bash
# Weekly run of the spec-alignment agent (.claude/agents/spec-alignment.md).
# By default: an interactive session in worktree ../<repo>-spec-alignment, detached at the ref (opened in Herdr when
# run inside it). The agent is read-only: it reports the gaps, asks which to pursue, and hands those back as concrete
# speckit steps or ready-to-file issues. --report-only: the unattended report in .cache/spec-alignment/<date>.md.
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

agent_workdir
agent_run
