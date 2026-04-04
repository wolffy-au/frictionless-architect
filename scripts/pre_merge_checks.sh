#!/bin/bash

# Exit immediately if any command fails.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "💡 Running pre-merge checks (includes pre-commit and heavier suites)..."
scripts/pre_commit_checks.sh

# --- Code Quality Checks ---
# echo "Running code quality scan..."
# uv run pysonar --sonar-token=<token> --exclude .git || true

# --- Security Checks ---
# echo "Running security scan..."
# uv run snyk test --package-manager=poetry || true

echo "Running behave acceptance tests..."
uv run behave tests/features/

echo "Running pytest suites..."
uv run pytest --cov-fail-under=90 --cov=src --cov-report=term-missing

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
