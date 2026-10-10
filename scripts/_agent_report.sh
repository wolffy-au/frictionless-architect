#!/bin/bash
# Shared driver for the weekly agent runs (scripts/*_weekly.sh). Two modes:
#
#   session (default)  human in the loop. Creates (or reuses) a persistent worktree next to the repo,
#                      ../<repo>-<OUT_NAME>, on BRANCH (or detached at REF), prepares it (SETUP), and starts an
#                      interactive `claude --agent AGENT` there — in a new Herdr workspace when run inside Herdr,
#                      otherwise in this terminal. The agent reviews first, presents the findings as numbered
#                      options, waits for your choice, then fixes only what you picked (FIX_TASK) and commits on
#                      the branch. It never pushes, opens a PR or merges unless you ask.
#   --report-only      unattended (cron / timers). The original contract: the report goes to
#                      .cache/<OUT_NAME>/<stamp>.md (+ .log, .json), no branch/commit/PR is created, and the run exits
#                      non-zero if claude fails, any tool call was denied, or the report has no '## Findings' heading.
#
# Usage in a script:
#   source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"
#   agent_parse_flags "$@"; set -- "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}"
#   ...set the variables...
#   agent_workdir        # cd's into WORKDIR: where any prep files (relative paths in TASK) must be written
#   ...optional prep...
#   agent_run
#
# Variables (set before agent_workdir):
#   AGENT     agent name under .claude/agents/                      (required)
#   OUT_NAME  subdirectory of .cache/ for the output; also the worktree suffix, Herdr label and agent name (required)
#   TASK      the review: what to tell the agent (steps to run/skip, scope) (required)
#   TOOLS     comma-separated --allowedTools list for the review    (required; a session asks you for anything else)
#   REF       git ref to check out (default: develop)
#   STAMP     output basename (default: today's date)
#   MODE      report-only only: worktree (default) = audit a clean temp checkout of REF; root = run in the current
#             checkout, for agents that need the Poetry venv / .secrets / wiki/.cache. A root run reports on whatever
#             is checked out, so REF is ignored and a dirty tree only warns.
#   BRANCH    session only: branch the fixes go on, created from REF if missing (default: detached, review only)
#   FIX_TASK  session only: how to fix the findings you pick. Empty = the agent cannot edit, so it hands each chosen
#             finding back as a concrete follow-up instead.
#   SETUP     session only: space-separated worktree preparation — venv (poetry install), submodules
#             (third_party/*), secrets (link the main checkout's gitignored .env and .secrets/).

set -euo pipefail

# Append to TASK: the --allowedTools matcher rejects chained commands, so agents must keep Bash calls simple.
AGENT_BASH_RULE="Use Read, Grep and Glob for files; use Bash only for the allowed commands, one per call (no cd, sed, ls, 'git -C', ';', '&&', '|' or redirects)."

agent_fail() {
  echo "ERROR: $*" >&2
  [ -z "${LOG:-}" ] || echo "See $LOG and $RAW" >&2
  exit 1
}

# Split --report-only off the script's arguments; the rest land in AGENT_ARGS.
agent_parse_flags() {
  REPORT_ONLY=0
  AGENT_ARGS=()
  local a
  for a in "$@"; do
    case "$a" in
      --report-only) REPORT_ONLY=1 ;;
      *) AGENT_ARGS+=("$a") ;;
    esac
  done
}

# Delete prep files when the script exits — report-only runs only: a session's agent reads them after this exits.
agent_cleanup_on_exit() {
  [ "${REPORT_ONLY:-0}" = 1 ] || return 0
  # shellcheck disable=SC2064  # expand the paths now
  trap "rm -f $(printf '%q ' "$@")" EXIT
}

# Resolve ROOT and WORKDIR and cd into WORKDIR. A session creates its worktree here.
agent_workdir() {
  : "${AGENT:?}" "${OUT_NAME:?}"
  export PATH="$HOME/.local/bin:$PATH"
  cd "$(git rev-parse --show-toplevel)"
  ROOT="$PWD"
  if [ "${REPORT_ONLY:-0}" = 1 ]; then
    WORKDIR="$ROOT"
  else
    _agent_worktree
    _agent_setup
    WORKDIR="$WT"
  fi
  mkdir -p "$WORKDIR/.cache/$OUT_NAME"
  cd "$WORKDIR"
}

agent_run() {
  : "${AGENT:?}" "${OUT_NAME:?}" "${TASK:?}" "${TOOLS:?}" "${WORKDIR:?call agent_workdir first}"
  if [ "${REPORT_ONLY:-0}" = 1 ]; then
    agent_report_run
  else
    agent_session_run
  fi
}

# "Since" baseline for the agent: the last release tag reachable from $1, else the last 30 days.
_agent_baseline() {
  local last_tag
  if last_tag="$(git describe --tags --abbrev=0 "$1" 2>/dev/null)"; then
    echo "Use \`git log $last_tag..HEAD\` as the 'since last release' baseline."
  else
    echo "No release tag is reachable; use \`git log --since='30 days ago'\` as the baseline instead of git describe."
  fi
}

# Remove a failed submodule clone's debris (its checkout and its git dir) so the next attempt starts clean.
_agent_clear_submodule() {
  local git_dir
  git_dir="$(git -C "$WT" rev-parse --absolute-git-dir)/modules/$1"
  sudo rm -rf "${WT:?}/$1" "$git_dir"
  mkdir -p "$WT/$1"
}

_agent_worktree() {
  local ref="${REF:-develop}"
  WT="$(dirname "$ROOT")/$(basename "$ROOT")-$OUT_NAME"
  git worktree prune

  if git worktree list --porcelain | grep -qxF "worktree $WT"; then
    echo "Reusing worktree $WT ($(git -C "$WT" rev-parse --abbrev-ref HEAD))"
  else
    [ ! -e "$WT" ] || agent_fail "$WT exists but is not a worktree of $ROOT; move it aside first"
    # The parent (/workspaces in the devcontainer) can be root-owned.
    mkdir "$WT" 2>/dev/null || { sudo mkdir "$WT" && sudo chown "$(id -u):$(id -g)" "$WT"; } \
      || agent_fail "cannot create $WT"
    if [ -z "${BRANCH:-}" ]; then
      git worktree add --detach "$WT" "$ref" >/dev/null
    elif git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
      git worktree add "$WT" "$BRANCH" >/dev/null
    else
      git worktree add -b "$BRANCH" "$WT" "$ref" >/dev/null
    fi
    echo "Created worktree $WT (${BRANCH:-detached at $ref})"
  fi

  # The shared .git lives on drvfs, owned by another UID, so git in the worktree trips "dubious ownership". The
  # interactive agent does not inherit this script's env, so trust the path in the user's global config (herdr does
  # the same when it opens a worktree).
  git config --global --get-all safe.directory 2>/dev/null | grep -qxF "$WT" \
    || git config --global --add safe.directory "$WT"
}

_agent_setup() {
  local step
  for step in ${SETUP:-}; do
    case "$step" in
      venv) _agent_setup_venv ;;
      submodules) _agent_setup_submodules ;;
      secrets) _agent_setup_secrets ;;
      *) agent_fail "unknown SETUP step '$step'" ;;
    esac
  done
}

# Poetry keys its virtualenv on the project path, so a new worktree gets an empty venv of its own.
_agent_setup_venv() {
  poetry -C "$WT" env info --path >/dev/null 2>&1 && poetry -C "$WT" run python -c 'import frictionless_architect' \
    2>/dev/null && return 0
  echo "Installing the Poetry venv for $WT"
  poetry -C "$WT" install --no-interaction >/dev/null || agent_fail "poetry install failed in $WT"
}

_agent_setup_submodules() {
  local path ref_dir
  while read -r _ path; do
    [[ "$(git -C "$WT" submodule status -- "$path")" == -* ]] || continue
    echo "Initialising $path"
    # Borrow objects from the main checkout's copy instead of re-cloning from scratch.
    ref_dir="$ROOT/.git/modules/$path"
    local args=(submodule update --init)
    [ -d "$ref_dir" ] && args+=(--reference "$ref_dir")
    args+=(-- "$path")
    _agent_clear_submodule "$path"
    if ! (cd "$WT" && git "${args[@]}" >/dev/null 2>&1); then
      # The submodule's git dir sits under the main checkout's .git, on drvfs: unprivileged chmods there fail with
      # EPERM (AGENTS.md "Known environment quirks"). Clear the half-made clone and retry as root; safe.directory goes
      # on the command line rather than into root's global config.
      _agent_clear_submodule "$path"
      (cd "$WT" && sudo git -c safe.directory='*' "${args[@]}" >/dev/null) || agent_fail "could not initialise $path"
    fi
  done < <(git -C "$WT" config -f .gitmodules --get-regexp '^submodule\..*\.path$')
  # Undo any root-owned files the privileged retry left in the worktree (the overlay honours chown).
  [ -z "$(find "$WT/third_party" -maxdepth 2 ! -user "$(id -u)" -print -quit 2>/dev/null)" ] \
    || sudo chown -R "$(id -u):$(id -g)" "$WT/third_party"
}

# The scanners and fix gates read tokens from the gitignored .env / .secrets/; share the main checkout's.
_agent_setup_secrets() {
  local f
  for f in .env .secrets; do
    [ -e "$ROOT/$f" ] && [ ! -e "$WT/$f" ] && ln -s "$ROOT/$f" "$WT/$f"
  done
  return 0
}

agent_session_run() {
  local stamp="${STAMP:-$(date +%F)}" report fix
  report=".cache/$OUT_NAME/$stamp.md"

  if [ -n "${FIX_TASK:-}" ]; then
    fix="Phase 3, fix: work only on the findings I chose. $FIX_TASK You are already on branch ${BRANCH:-the current branch} \
in a dedicated worktree, so skip your branch step. Commit in focused Conventional Commits (commit-message skill ruleset). \
Do not push, open a PR or merge unless I ask; when done, list the commits and anything you deferred."
  else
    fix="Phase 3, follow-up: you cannot edit files. For each finding I chose, give the concrete next step (the exact \
command, skill or agent to run, or a ready-to-file GitHub issue title and body) so I can act on it."
  fi

  local prompt
  prompt="This is the weekly $OUT_NAME run, with a human in the loop. Work in three phases. \
Phase 1, review (read-only: edit nothing, commit nothing): $TASK $(_agent_baseline HEAD) \
Number every finding (F1, F2, ...) and give each a severity and a recommended action. \
$( [ -n "${FIX_TASK:-}" ] && echo "Save the full report to $report with a '## Findings' heading, then print it." \
  || echo "Print the full report with a '## Findings' heading.") \
Phase 2, decide: present the findings as options grouped by severity, with your recommendation, and ask me which to act \
on (all, a list of IDs, or none) using AskUserQuestion. Then stop and wait for my answer; do nothing further until I reply. \
$fix"

  local cmd=(claude --agent "$AGENT" --allowedTools "$TOOLS" --name "$OUT_NAME-$stamp" "$prompt")

  if [ "${HERDR_ENV:-}" = 1 ] && command -v herdr >/dev/null; then
    if herdr agent get "$OUT_NAME" >/dev/null 2>&1; then
      herdr agent focus "$OUT_NAME" >/dev/null
      echo "An agent named '$OUT_NAME' is already running in Herdr; focused it instead of starting another."
      return 0
    fi
    local opened pane
    opened="$(herdr worktree open --cwd "$ROOT" --path "$WT" --label "$OUT_NAME" --focus)" \
      || agent_fail "herdr could not open $WT: $opened"
    pane="$(jq -r '.result.root_pane.pane_id // empty' <<< "$opened")"
    [ -n "$pane" ] || agent_fail "herdr returned no pane for $WT: $opened"
    herdr pane run "$pane" "$(printf '%q ' "${cmd[@]}")" >/dev/null
    herdr pane rename "$pane" "$OUT_NAME" >/dev/null 2>&1 || true
    echo "Started $AGENT in Herdr workspace '$OUT_NAME' (pane $pane), worktree $WT."
    echo "It will review, then ask which findings to fix."
  else
    [ -t 0 ] && [ -t 1 ] || agent_fail "a session needs a terminal; use --report-only for unattended runs"
    echo "Starting $AGENT in $WT (not inside Herdr, so in this terminal)."
    cd "$WT"
    exec "${cmd[@]}"
  fi
}

agent_report_run() {
  local ref="${REF:-develop}" mode="${MODE:-worktree}" claude_dir

  OUT_DIR="$ROOT/.cache/$OUT_NAME"
  mkdir -p "$OUT_DIR"

  OUT="$OUT_DIR/${STAMP:-$(date +%F)}.md"
  LOG="${OUT%.md}.log"
  RAW="${OUT%.md}.json"

  cd "$ROOT"
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

  local baseline
  baseline="$(_agent_baseline "${ref%%@*}")"

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
