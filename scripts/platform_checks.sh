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

echo "Running pyright on platform/packages..."
poetry run pyright packages

mkdir -p "$root/build"
for pkg in packages/*/; do
  pkg="${pkg%/}"
  name="$(basename "$pkg")"
  echo "── $name: mypy"
  poetry run mypy "$pkg/src" "$pkg/tests"
  echo "── $name: pytest (coverage gate 90%)"
  poetry run pytest "$pkg/tests" \
    --cov="$pkg/src" --cov-fail-under=90 --cov-report=term-missing \
    --cov-report="xml:$root/build/platform-coverage-$name.xml"
done

echo "✅ Platform checks passed."
