#!/bin/bash

# Exit immediately if any command fails.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "💡 Running pre-merge checks (includes pre-commit and heavier suites)..."
scripts/pre_commit_checks.sh

echo "Updating dependency locks to the latest compatible versions..."
# CI only runs `poetry install` against the committed lock — this is where
# poetry.lock actually gets refreshed. If it changes, it must be committed
# before pushing, or the bump never reaches CI.
poetry update
if ! git diff --quiet -- poetry.lock; then
  echo "poetry.lock changed — review and commit it before pushing:" >&2
  git --no-pager diff --stat -- poetry.lock >&2
  exit 1
fi
echo "poetry.lock already up to date."

# --- Code Quality Checks ---
# echo "Running code quality scan..."
# poetry run pysonar --sonar-token=<token> --exclude .git || true

# --- Security Checks ---
echo "Running Snyk security scan..."
poetry run snyk auth "${SNYK_TOKEN:?SNYK_TOKEN must be set to run the pre-merge Snyk scan}"
poetry run snyk test --package-manager=poetry --org=wolffy-au
poetry run snyk code test --package-manager=poetry --org=wolffy-au --include-ignores

# behave (BDD acceptance) is not gated while tests/features/ is a placeholder.
# Re-add `poetry run behave tests/features/` here once real scenarios exist.

echo "Running pytest suites..."
poetry run pytest --cov-fail-under=90 --cov=src --cov-report=term-missing

echo "Running frontend UI harness..."
if [ -d frontend ]; then
  cd frontend
  npm config set bin-links false
  npm install
  node ./node_modules/playwright/cli.js install chromium
  npm run test:ui
  cd ..
else
  echo "Skipping frontend UI harness because frontend directory is missing."
fi
