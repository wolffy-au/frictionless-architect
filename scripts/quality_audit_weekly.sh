#!/bin/bash
# Weekly run of the quality-uplift agent (.claude/agents/quality-uplift.md).
# By default: an interactive session in worktree ../<repo>-quality-audit on bugfix/quality-uplift-<date> (opened in
# Herdr when run inside it), with its own Poetry venv. The agent reports the Sonar-style smells, asks which to fix,
# then fixes those, runs the local gate and commits.
# --report-only: the unattended smell report in .cache/quality-audit/<date>.md; fixes nothing and opens no PR. It runs
# in the CURRENT checkout, not a temp worktree: ruff/pyright/mypy need the Poetry venv.
#
# Usage: scripts/quality_audit_weekly.sh [--report-only] [scope]
#   scope  path or module to focus on, e.g. src/frictionless_architect/visualizer (default: src/ and tests/)

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"
agent_parse_flags "$@"; set -- "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}"

SCOPE="${1:-}"
SONAR_BRANCH="${SONAR_BRANCH:-main}"

AGENT=quality-uplift
OUT_NAME=quality-audit
MODE=root
BRANCH="bugfix/quality-uplift-$(date +%F)"
SETUP="venv submodules secrets"
FIX_TASK="Follow your Steps 4-6 (fix, run the local gate, commit) for the chosen findings."
TOOLS="Read,Grep,Glob,Bash(poetry run ruff check:*),Bash(poetry run pyright:*),Bash(poetry run mypy:*),Bash(git log:*),Bash(git diff:*)"

# Fetch the open SonarCloud issues for the agent. The project is public, so this is an unauthenticated GET and no token
# is needed. If it fails, the audit runs without Sonar.
agent_workdir
SONAR_JSON=".cache/$OUT_NAME/sonar-issues.json"
agent_cleanup_on_exit "$SONAR_JSON"
if curl -fsS "https://sonarcloud.io/api/issues/search?componentKeys=wolffy-au_frictionless-architect&branch=$SONAR_BRANCH&resolved=false&ps=500" \
  | jq '{total, issues: [.issues[] | {rule, severity, type, status, file: (.component | sub("^[^:]*:"; "")), line, message}]}' \
  > "$SONAR_JSON"; then
  SONAR_TASK="A SonarCloud payload of the open issues on branch $SONAR_BRANCH is at $SONAR_JSON (read it with Read; 'total' above 500 means it is truncated): map each OPEN issue to a finding."
else
  rm -f "$SONAR_JSON"
  echo "WARNING: could not fetch SonarCloud issues; running without them." >&2
  SONAR_TASK="No SonarCloud payload is available this run; say so in the report."
fi

TASK="Follow your Steps 2-3 only: skip Steps 1 and 4-10. Run ruff, pyright and mypy for the baseline (do not use --fix), \
then hunt for the smells in Step 3. $SONAR_TASK Do not fetch Sonar yourself or read .secrets/. Instead of fixing, \
list each issue as file:line | rule/smell | suggested fix, ranked by severity, under '## Findings'. $AGENT_BASH_RULE"
if [ -n "$SCOPE" ]; then
  TASK="$TASK Scope: $SCOPE only."
  STAMP="$(date +%F)-$(tr -c 'A-Za-z0-9' '-' <<< "$SCOPE" | sed 's/-*$//')"
fi

agent_run
