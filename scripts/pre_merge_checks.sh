#!/bin/bash

# Exit immediately if any command fails.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "💡 Running pre-merge checks (includes pre-commit and heavier suites)..."
scripts/pre_commit_checks.sh

echo "Running security scan..."
uv run snyk test --package-manager=poetry || true

echo "Running behave acceptance tests..."
uv run behave tests/features/

echo "Running pytest suites..."
uv run pytest --cov-fail-under=90 --cov=src --cov-report=term-missing

echo "Running frontend UI harness..."
cd frontend
npm config set bin-links false
npm install
node ./node_modules/playwright/cli.js install chromium
npm run test:ui
