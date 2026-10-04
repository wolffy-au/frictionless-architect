#!/bin/bash
# Shared driver for the report-only agent runs (scripts/*_weekly.sh). Source it, set the variables, call agent_report_run.
# Same contract as adr_audit_weekly.sh: the report goes to .cache/<OUT_NAME>/<stamp>.md (+ .log, .json),
# no branch/commit/PR is created, and the run exits non-zero if claude fails, any tool call was denied,
# or the report has no '## Findings' heading.
#
# Variables (set before calling):
#   AGENT     agent name under .claude/agents/                      (required)
#   OUT_NAME  subdirectory of .cache/ for the output               (required)
#   TASK      what to tell the agent (steps to run/skip, scope)    (required)
#   TOOLS     comma-separated --allowedTools list                  (required)
#   REF       git ref to check out for the run (default: develop)
#   STAMP     output basename (default: today's date)
#   MODE      worktree (default) = audit a clean temp checkout of REF;
#             root = run in the current checkout, for agents that need the Poetry venv / .secrets / wiki/.cache.
#             A root run reports on whatever is checked out, so REF is ignored and a dirty tree only warns.

set -euo pipefail

# Append to TASK: the --allowedTools matcher rejects chained commands, so agents must keep Bash calls simple.
AGENT_BASH_RULE="Use Read, Grep and Glob for files; use Bash only for the allowed commands, one per call (no cd, sed, ls, 'git -C', ';', '&&', '|' or redirects)."

agent_fail() {
  echo "ERROR: $*" >&2
  [ -z "${LOG:-}" ] || echo "See $LOG and $RAW" >&2
  exit 1
}

agent_report_run() {
  : "${AGENT:?}" "${OUT_NAME:?}" "${TASK:?}" "${TOOLS:?}"
  local ref="${REF:-develop}" mode="${MODE:-worktree}" claude_dir

  export PATH="$HOME/.local/bin:$PATH"
  cd "$(git rev-parse --show-toplevel)"
  ROOT="$PWD"
  OUT_DIR="$ROOT/.cache/$OUT_NAME"
  mkdir -p "$OUT_DIR"

  OUT="$OUT_DIR/${STAMP:-$(date +%F)}.md"
  LOG="${OUT%.md}.log"
  RAW="${OUT%.md}.json"

  if [ "$mode" = worktree ]; then
    WORKTREE="$(mktemp -d)"
    trap 'cd "$ROOT"; git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true' EXIT
    git worktree add --detach "$WORKTREE" "$ref" >/dev/null
    claude_dir="$WORKTREE"
  else
    ref="$(git rev-parse --abbrev-ref HEAD)@$(git rev-parse --short HEAD)"
    [ -z "$(git status --porcelain)" ] || echo "WARNING: working tree is dirty; the report covers uncommitted changes too." >&2
    claude_dir="$ROOT"
  fi

  # "Since" baseline: the last release tag reachable from the ref, else the last 30 days.
  local baseline
  if LAST_TAG="$(git describe --tags --abbrev=0 "${ref%%@*}" 2>/dev/null)"; then
    baseline="Use \`git log $LAST_TAG..HEAD\` as the 'since last release' baseline."
  else
    baseline="No release tag is reachable; use \`git log --since='30 days ago'\` as the baseline instead of git describe."
  fi

  echo "Running $AGENT at $ref -> $OUT"

  # The temp worktree can trip git's "dubious ownership" check; trust it for this run only (env, not config).
  export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'

  cd "$claude_dir"
  claude -p "Report only. Do not create a branch, edit or create files, commit, push or open a PR. \
$TASK $baseline Print only the final report as your last message, with a '## Findings' heading." \
    --agent "$AGENT" \
    --allowedTools "$TOOLS" \
    --output-format json \
    > "$RAW" 2> "$LOG" || agent_fail "claude exited non-zero"

  # Keep whatever report the agent produced, even if a check below fails.
  jq -r '.result // empty' "$RAW" > "$OUT" || true

  jq -e '.is_error == false' "$RAW" >/dev/null || agent_fail "claude reported an error: $(jq -r '.result // .subtype' "$RAW")"

  local denials
  denials="$(jq -r '.permission_denials | length' "$RAW")"
  if [ "$denials" -ne 0 ]; then
    # claude's stderr is usually empty on a denial; record the denied commands so the .log explains the failure.
    jq -r '.permission_denials[] | "DENIED \(.tool_name): \(.tool_input.command // (.tool_input | tostring))"' "$RAW" >> "$LOG"
  fi
  [ "$denials" -eq 0 ] || agent_fail "$denials tool call(s) were denied: $(jq -c '[.permission_denials[].tool_name]' "$RAW")"

  grep -q '^## Findings' "$OUT" || agent_fail "report has no '## Findings' section (incomplete run)"

  echo "Done: $OUT"
}
