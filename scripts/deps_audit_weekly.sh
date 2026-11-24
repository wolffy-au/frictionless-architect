#!/bin/bash
# Weekly dependency refresh: the root poetry.lock, platform/poetry.lock, pre-commit hook versions, and the
# third_party/ submodules. Supersedes the old scripts/update-all.sh (folded into the same worktree/report-only
# pattern as the other scripts/*_weekly.sh audits — see scripts/register_audit_reminders.ps1). Mechanical, so
# unlike the other weeklies it runs no Claude agent: there is no judgement call here, just "is a newer
# compatible version available."
#
# By default: opens (or reuses) worktree ../<repo>-deps-audit on chore/deps-refresh-<date>, refreshes both
# Poetry locks, pre-commit hook pins and the submodules, then the full gate (scripts/pre_merge_checks.sh). If
# the gate passes, commits each changed area as its own Conventional Commit (chore(deps): ..., chore: ...) on
# the branch. It never pushes, opens a PR or merges — review the branch and push it yourself.
# --report-only: checks for drift without changing anything (a dry-run on both locks, a pre-commit autoupdate
# dry run, and each submodule's checked-out SHA against its remote default branch); writes
# .cache/deps-audit/<date>.md and exits non-zero if anything is stale.
#
# Usage: scripts/deps_audit_weekly.sh [--report-only]

set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

REPORT_ONLY=0
[ "${1:-}" = "--report-only" ] && REPORT_ONLY=1

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
OUT_NAME=deps-audit
STAMP="$(date +%F)"

if [ "$REPORT_ONLY" = 1 ]; then
  OUT_DIR="$ROOT/.cache/$OUT_NAME"
  mkdir -p "$OUT_DIR"
  OUT="$OUT_DIR/$STAMP.md"
  {
    echo "## Findings"
    echo
    echo "### Root poetry.lock"
    poetry update --dry-run 2>&1 || true
    echo
    echo "### platform/poetry.lock"
    (cd platform && poetry update --dry-run 2>&1) || true
    echo
    echo "### pre-commit hook versions"
    poetry run pre-commit autoupdate --dry-run 2>&1 || true
    echo
    echo "### third_party/ submodules"
    git submodule foreach --quiet '
      default_branch="$(git remote show origin | sed -n "s/.*HEAD branch: //p")"
      git fetch -q origin "$default_branch"
      current="$(git rev-parse --short HEAD)"
      latest="$(git rev-parse --short "origin/$default_branch")"
      if [ "$current" = "$latest" ]; then
        echo "$path: up to date ($current)"
      else
        echo "$path: $current -> $latest available on $default_branch"
      fi
    ' 2>&1 || true
  } > "$OUT"
  echo "Done: $OUT"
  grep -qE 'Updating|available on' "$OUT" && { echo "Drift found, see $OUT"; exit 1; }
  exit 0
fi

# Session mode: worktree + refresh + gate + commit.
WT="$(dirname "$ROOT")/$(basename "$ROOT")-$OUT_NAME"
BRANCH="chore/deps-refresh-$STAMP"
git worktree prune
if git worktree list --porcelain | grep -qxF "worktree $WT"; then
  echo "Reusing worktree $WT ($(git -C "$WT" rev-parse --abbrev-ref HEAD))"
else
  [ ! -e "$WT" ] || { echo "ERROR: $WT exists but is not a worktree of $ROOT; move it aside first" >&2; exit 1; }
  mkdir "$WT" 2>/dev/null || { sudo mkdir "$WT" && sudo chown "$(id -u):$(id -g)" "$WT"; }
  if git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
    git worktree add "$WT" "$BRANCH" >/dev/null
  else
    git worktree add -b "$BRANCH" "$WT" develop >/dev/null
  fi
  echo "Created worktree $WT ($BRANCH)"
fi
# The shared .git lives on drvfs, owned by another UID (AGENTS.md "Known environment quirks").
git config --global --get-all safe.directory 2>/dev/null | grep -qxF "$WT" || git config --global --add safe.directory "$WT"

cd "$WT"
bash scripts/update-all.sh

if [ -z "$(git status --porcelain)" ]; then
  echo "Nothing to refresh this week."
  exit 0
fi

echo "--- refreshed ---"
git status --porcelain

bash scripts/pre_merge_checks.sh

commit_path() {
  git diff --quiet -- "$1" 2>/dev/null && [ -z "$(git status --porcelain -- "$1")" ] && return 0
  git add "$1"
  git commit -m "$2"
}
commit_path poetry.lock "chore(deps): refresh poetry.lock"
commit_path platform/poetry.lock "chore(deps): refresh platform/poetry.lock"
commit_path .pre-commit-config.yaml "chore: bump pre-commit hook versions"
git add third_party 2>/dev/null || true
git diff --cached --quiet -- third_party || git commit -m "chore(deps): bump third_party submodules"

echo "Refreshed and committed on $BRANCH in $WT. Review and push yourself when ready."
