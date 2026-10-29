#!/bin/bash

# Fan-out gate for the platform/ Poetry monorepo (ADR-0002, ARCHITECTURE.md §8
# step 3): one shared lock and virtualenv for platform/, then every package
# under platform/packages/ type-checked and tested on its own. ruff is not run
# here — the repo-root `ruff check .` already covers platform/.
#
# Called by pre_commit_checks.sh, pre_merge_checks.sh, the pre-push hook and CI.
# Pass --update to refresh platform/poetry.lock first (pre-merge only).
#
# Diff-scoping: when run as the git pre-push hook, pre-commit sets
# PRE_COMMIT_FROM_REF/PRE_COMMIT_TO_REF to the range being pushed. If that
# range touches no platform/ file, the whole script is a no-op instead of
# paying the full install+pyright+per-package fan-out every push. If it
# touches only specific packages/<name>/ paths, the fan-out below (pyright,
# mypy, pytest, behave) is scoped to just those packages -- the packages are
# deliberately isolated (own lock/venv per ADR-0002), so a change in one has
# no bearing on another's tests. A change to a shared file (platform/
# pyproject.toml, poetry.lock) falls back to checking every package, since
# that can affect all of them. --update (pre-merge only) always runs full,
# and so does any invocation without those env vars (manual run, CI) -- only
# the git pre-push hook's own invocation is ever scoped.

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
# A caller's active virtualenv (e.g. the repo root's, under `poetry run` or an
# activated shell) would otherwise capture every poetry command below.
unset VIRTUAL_ENV

root="$(git rev-parse --show-toplevel)"

SCOPE_PACKAGES=""
if [[ "${1:-}" != "--update" && -n "${PRE_COMMIT_FROM_REF:-}" && -n "${PRE_COMMIT_TO_REF:-}" ]]; then
  changed="$(git -C "$root" diff --name-only "$PRE_COMMIT_FROM_REF" "$PRE_COMMIT_TO_REF" -- platform/ || true)"
  if [[ -z "$changed" ]]; then
    echo "No platform/ changes between $PRE_COMMIT_FROM_REF and $PRE_COMMIT_TO_REF — skipping platform/ package checks."
    exit 0
  fi
  shared_changed=0
  touched_pkgs=""
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    if [[ "$f" =~ ^platform/packages/([^/]+)/ ]]; then
      touched_pkgs+="${BASH_REMATCH[1]}"$'\n'
    else
      shared_changed=1
    fi
  done <<< "$changed"
  if [[ "$shared_changed" -eq 0 && -n "$touched_pkgs" ]]; then
    SCOPE_PACKAGES="$(printf '%s' "$touched_pkgs" | sort -u)"
    echo "Scoping platform/ checks to the packages this push touches: $(tr '\n' ' ' <<< "$SCOPE_PACKAGES")"
  else
    echo "This push touches a shared platform/ file (pyproject.toml/poetry.lock) — running checks for every package."
  fi
fi

cd "$root/platform"

if [[ "${1:-}" == "--update" ]]; then
  echo "Updating platform/poetry.lock to the latest compatible versions..."
  poetry update --no-interaction
  if ! git diff --quiet -- poetry.lock; then
    echo "platform/poetry.lock changed — review and commit it before pushing:" >&2
    git --no-pager diff --stat -- poetry.lock >&2
    exit 1
  fi
fi

echo "Checking platform/poetry.lock matches platform/pyproject.toml..."
poetry check --lock

echo "Installing the platform/ workspace..."
poetry install --no-interaction --quiet

need_playwright=0
if [[ -n "$SCOPE_PACKAGES" ]]; then
  while IFS= read -r p; do
    [[ -d "packages/$p/tests/features" ]] && need_playwright=1
  done <<< "$SCOPE_PACKAGES"
elif compgen -G "packages/*/tests/features" > /dev/null; then
  need_playwright=1
fi
if [[ "$need_playwright" -eq 1 ]]; then
  echo "Installing Playwright's Chromium browser (for behave UI scenarios)..."
  poetry run playwright install --with-deps chromium
fi

echo "Running pyright on platform/packages..."
if [[ -n "$SCOPE_PACKAGES" ]]; then
  pyright_targets=()
  while IFS= read -r p; do pyright_targets+=("packages/$p"); done <<< "$SCOPE_PACKAGES"
  poetry run pyright "${pyright_targets[@]}"
else
  poetry run pyright packages
fi

mkdir -p "$root/build"

# Each package's mypy/pytest/behave sequence is independent of every other
# package's, so they fan out as background jobs instead of a serial for-loop.
# Each gets its own mypy/pytest cache dir (both default to one shared path
# under this cwd) so concurrent runs can't race writing the same cache file.
# `set -e` only aborts the parent shell on a *foreground* failure, so each
# job's exit status is collected explicitly via `wait` below.
#
# pytest's own -n auto would pick a full core count *inside each* already-
# concurrent package job; two packages doing that at once oversubscribes the
# machine and, on this workspace's 9p/drvfs mount, reliably corrupted
# pytest-cov's per-worker SQLite file (coverage.exceptions.DataError /
# xdist "KeyError: WorkerController"). Split the core count across the
# packages running instead, so the two layers of parallelism don't compound.
if [[ -n "$SCOPE_PACKAGES" ]]; then
  pkg_count=$(printf '%s\n' "$SCOPE_PACKAGES" | sed '/^$/d' | wc -l)
else
  pkg_count=$(find packages -maxdepth 1 -mindepth 1 -type d | wc -l)
fi
pytest_workers=$(( $(nproc) / pkg_count ))
[[ $pytest_workers -lt 1 ]] && pytest_workers=1

run_package_checks() {
  local pkg="$1" name="$2"
  echo "── $name: mypy"
  poetry run mypy --cache-dir="$root/build/.mypy_cache_$name" "$pkg/src" "$pkg/tests"
  echo "── $name: pytest (coverage gate 90%)"
  # pytest-cov's workers each write their own SQLite coverage DB (named by
  # host+pid+random, so filenames never collide); on this workspace's
  # 9p/drvfs mount, two packages' processes doing that concurrently in the
  # *same directory* still hit sqlite3 "disk I/O error" / xdist worker
  # KeyErrors. Giving each package its own coverage data directory (not
  # just its own filename) avoids the shared-directory contention.
  local cov_dir="$root/build/.coverage_data_$name"
  mkdir -p "$cov_dir"
  COVERAGE_FILE="$cov_dir/.coverage" poetry run pytest "$pkg/tests" -n "$pytest_workers" \
    -o "cache_dir=$root/build/.pytest_cache_$name" \
    --cov="$pkg/src" --cov-fail-under=90 --cov-report=term-missing \
    --cov-report="xml:$root/build/platform-coverage-$name.xml"
  if [[ -d "$pkg/tests/features" ]]; then
    echo "── $name: behave"
    poetry run behave "$pkg/tests/features"
  fi
}

echo "Running per-package checks (mypy, pytest, behave) in parallel ($pytest_workers pytest worker(s) per package)..."
pids=()
names=()
for pkg in packages/*/; do
  pkg="${pkg%/}"
  name="$(basename "$pkg")"
  if [[ -n "$SCOPE_PACKAGES" ]] && ! grep -qx "$name" <<< "$SCOPE_PACKAGES"; then
    echo "── $name: skipped (not touched by this push)"
    continue
  fi
  if [[ ! -d "$pkg/src" ]]; then
    # A package directory can legitimately exist with only specs/ during the
    # spec-driven workflow's pause between /speckit-plan and /speckit-tasks
    # (no src/ yet) -- not a failure, just nothing to type-check or test yet.
    echo "── $name: skipped (no $pkg/src yet)"
    continue
  fi
  run_package_checks "$pkg" "$name" > "$root/build/platform-check-$name.log" 2>&1 &
  pids+=("$!")
  names+=("$name")
done

status=0
for i in "${!pids[@]}"; do
  name="${names[$i]}"
  if wait "${pids[$i]}"; then
    echo "── $name: passed"
  else
    echo "── $name: FAILED"
    status=1
  fi
  echo "---- $name output ----"
  cat "$root/build/platform-check-$name.log"
done

if [[ $status -ne 0 ]]; then
  exit 1
fi

echo "✅ Platform checks passed."
