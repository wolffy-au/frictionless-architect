#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

cd "$(git rev-parse --show-toplevel)"

echo "Starting pre-commit checks..."

echo "Running pre-commit checks..."

# --- Commit message standard ---
# Scope list, 72-char subject, case, period and breaking-change rules from the commit-message
# skill's standard. Covers the commits this branch adds over develop; fails on any violation.
echo "Checking commit messages..."
base=$(git rev-parse --verify --quiet develop || git rev-parse --verify --quiet origin/develop || true)
if [ -n "$base" ]; then
  poetry run python scripts/check_commit_messages.py --range "$base..HEAD"
else
  echo "No develop ref found; skipping commit message check."
fi

# --- Linting and Formatting Check ---
echo "Running pymarkdown lint..."
# Runs pymarkdown for linting markdown files. Assumes pymarkdown is executable in the environment.
poetry run pymarkdownlnt fix ./*.md specs/*.md

echo "Running ruff check..."
# Runs ruff for linting and formatting checks across the project.
poetry run ruff check . --fix

echo "Running pyright..."
# Runs pyright for static type checking. Assumes pyright is executable in the environment.
poetry run pyright

# --- Static Type Checking ---
echo "Running mypy..."
# Runs mypy on the src directory for static type checking.
poetry run mypy

# --- Unit Tests ---
echo "Running pytest unit tests..."
poetry run pytest tests/unit/

# --- platform/ monorepo packages (own lock + venv) ---
echo "Running platform/ package checks..."
scripts/platform_checks.sh


echo "Pre-commit checks passed successfully."
echo "✅ Pre-commit checks completed."
echo "Run scripts/pre_merge_checks.sh before merging to exercise security, backend, and frontend suites."
exit 0
