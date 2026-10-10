#!/bin/bash

# Exit immediately if any command fails.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "💡 Running pre-merge checks (includes pre-commit and heavier suites)..."
scripts/pre_commit_checks.sh

echo "Checking the generated GitHub roadmap layer is current..."
# Fails (exit 1) if GitHub has moved on; fix with scripts/refresh_gh_roadmap.sh, review and commit.
poetry run python architecture/model/import_gh_roadmap.py --check

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

echo "Updating platform/poetry.lock and re-running the platform/ package checks..."
scripts/platform_checks.sh --update

# --- Code Quality Checks ---
# echo "Running code quality scan..."
# poetry run pysonar --sonar-token=<token> --exclude .git || true

# --- Security Checks ---
echo "Running Snyk security scan..."
# SNYK_TOKEN lives in the gitignored .env (also in .secrets/); load it if not already exported.
if [ -z "${SNYK_TOKEN:-}" ] && [ -f .env ]; then
  SNYK_TOKEN="$(grep -m1 '^SNYK_TOKEN=' .env | cut -d= -f2- | tr -d "\"'")"
  export SNYK_TOKEN
fi
poetry run snyk auth "${SNYK_TOKEN:?SNYK_TOKEN must be set to run the pre-merge Snyk scan}"
poetry run snyk test --package-manager=poetry --org=wolffy-au
poetry run snyk code test --package-manager=poetry --org=wolffy-au --include-ignores
# platform/ has its own lock; `snyk test` scans one project per directory.
# (Snyk Code above already walks platform/ source.)
(cd platform && snyk test --package-manager=poetry --file=poetry.lock --org=wolffy-au)

echo "Running behave acceptance scenarios..."
poetry run behave tests/features/

echo "Running pytest suites..."
poetry run pytest --cov-fail-under=90 --cov=src --cov=architecture/model --cov-report=term-missing

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
