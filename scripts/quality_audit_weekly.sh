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
SONAR_BRANCH="${SONAR_BRANCH:-main}"

AGENT=quality-uplift
OUT_NAME=quality-audit
MODE=root
TOOLS="Read,Grep,Glob,Bash(poetry run ruff check:*),Bash(poetry run pyright:*),Bash(poetry run mypy:*),Bash(git log:*),Bash(git diff:*)"

# Fetch the open SonarCloud issues for the agent. The project is public, so this is an unauthenticated GET and no token
# is needed. If it fails, the audit runs without Sonar.
cd "$(git rev-parse --show-toplevel)"
mkdir -p ".cache/$OUT_NAME"
SONAR_JSON=".cache/$OUT_NAME/sonar-issues.json"
trap 'rm -f "$SONAR_JSON"' EXIT
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

agent_report_run
