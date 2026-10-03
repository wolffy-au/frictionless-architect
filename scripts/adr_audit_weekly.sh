#!/bin/bash
# Report-only run of the adr-auditor agent (.claude/agents/adr-auditor.md).
# Writes the findings to .cache/adr-audit/<date>.md; creates no branch, commit or PR.
# Exits non-zero if claude fails, any tool call was denied, or the report is missing its findings.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/adr_audit_weekly.sh [git-ref] [adr-list]
#   git-ref   branch/tag to audit (default: develop)
#   adr-list  comma-separated ADR numbers to focus on, e.g. "14,31" or "0014,0031" (default: all)

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

cd "$(git rev-parse --show-toplevel)"
ROOT="$PWD"

REF="${1:-develop}"
ADRS="${2:-}"
OUT_DIR="$ROOT/.cache/adr-audit"
STAMP="$(date +%F)"
LOG="" RAW=""  # set once the focus is known; fail() can run before that

mkdir -p "$OUT_DIR"

fail() {
  echo "ERROR: $*" >&2
  [ -z "$LOG" ] || echo "See $LOG and $RAW" >&2
  exit 1
}

# Audit a clean checkout of REF so a dirty working tree never skews the result.
WORKTREE="$(mktemp -d)"
trap 'cd "$ROOT"; git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true' EXIT
git worktree add --detach "$WORKTREE" "$REF" >/dev/null

# Optional focus: normalise "14, 31" -> "0014,0031" and make sure each ADR exists at REF.
SCOPE="Audit the whole ADR log."
if [ -n "$ADRS" ]; then
  NORMALISED=""
  IFS=',' read -ra NUMS <<< "$ADRS"
  for n in "${NUMS[@]}"; do
    n="${n//[[:space:]]/}"
    [[ "$n" =~ ^[0-9]+$ ]] || fail "invalid ADR number '$n' (expected e.g. 14,31)"
    n="$(printf '%04d' "$((10#$n))")"
    compgen -G "$WORKTREE/docs/adr/$n-*.md" >/dev/null || fail "ADR-$n not found in docs/adr/ at $REF"
    NORMALISED="${NORMALISED:+$NORMALISED,}$n"
  done
  SCOPE="Focus only on ADR-${NORMALISED//,/, ADR-}: inventory, staleness, ADR-vs-ADR conflicts and un-recorded decisions that touch them. Ignore other records unless they conflict with these."
fi

# Output names: <date>.* for the whole log, <date>-adr-0017-0018.* for a focused run.
[ -n "$ADRS" ] && STAMP="$STAMP-adr-${NORMALISED//,/-}"
OUT="$OUT_DIR/$STAMP.md"
LOG="$OUT_DIR/$STAMP.log"
RAW="$OUT_DIR/$STAMP.json"

# "Since" baseline: the last release tag reachable from REF, else the last 30 days.
if LAST_TAG="$(git describe --tags --abbrev=0 "$REF" 2>/dev/null)"; then
  BASELINE="Use \`git log $LAST_TAG..HEAD\` as the 'since last release' baseline."
else
  BASELINE="No release tag is reachable from $REF; use \`git log --since='30 days ago'\` as the baseline instead of git describe."
fi

echo "Auditing ADRs${ADRS:+ ($ADRS)} at $REF -> $OUT"

# The temp worktree can trip git's "dubious ownership" check; trust it for this run only (env, not config).
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'

cd "$WORKTREE"
claude -p "Report only: follow your Steps 2-6, skip Steps 1 and 7-11. Do not create a branch, \
edit or create files, commit, push or open a PR. $SCOPE $BASELINE \
Print only the final Output section as your last message, with a '## Findings' heading." \
  --agent adr-auditor \
  --allowedTools "Read,Grep,Glob,Bash(git log:*),Bash(git describe:*),Bash(git diff:*)" \
  --output-format json \
  > "$RAW" 2> "$LOG" || fail "claude exited non-zero"

# Keep whatever report the agent produced, even if a check below fails.
jq -r '.result // empty' "$RAW" > "$OUT" || true

jq -e '.is_error == false' "$RAW" >/dev/null || fail "claude reported an error: $(jq -r '.result // .subtype' "$RAW")"

DENIALS="$(jq -r '.permission_denials | length' "$RAW")"
[ "$DENIALS" -eq 0 ] || fail "$DENIALS tool call(s) were denied: $(jq -c '[.permission_denials[].tool_name]' "$RAW")"

grep -q '^## Findings' "$OUT" || fail "report has no '## Findings' section (incomplete audit)"

echo "Done: $OUT"
