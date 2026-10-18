#!/bin/bash

# Fan-out gate for the platform/ Poetry monorepo (ADR-0002, ARCHITECTURE.md §8
# step 3): one shared lock and virtualenv for platform/, then every package
# under platform/packages/ type-checked and tested on its own. ruff is not run
# here — the repo-root `ruff check .` already covers platform/.
#
# Called by pre_commit_checks.sh, pre_merge_checks.sh, the pre-push hook and CI.
# Pass --update to refresh platform/poetry.lock first (pre-merge only).

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
# A caller's active virtualenv (e.g. the repo root's, under `poetry run` or an
# activated shell) would otherwise capture every poetry command below.
unset VIRTUAL_ENV

root="$(git rev-parse --show-toplevel)"
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

if compgen -G "packages/*/tests/features" > /dev/null; then
  echo "Installing Playwright's Chromium browser (for behave UI scenarios)..."
  poetry run playwright install --with-deps chromium
fi

echo "Running pyright on platform/packages..."
poetry run pyright packages

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
pkg_count=$(find packages -maxdepth 1 -mindepth 1 -type d | wc -l)
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
