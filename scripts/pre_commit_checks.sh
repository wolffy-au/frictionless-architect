#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

echo "Starting pre-commit checks..."
echo "Updating dependency locks to the latest compatible versions..."
uv run poetry update
uv sync --upgrade --all-groups

echo "Running pre-commit checks..."

# --- Linting and Formatting Check ---
echo "Running pymarkdown lint..."
# Runs pymarkdown for linting markdown files. Assumes pymarkdown is executable in the environment.
uv run pymarkdownlnt fix *.md specs/*.md

echo "Running ruff check..."
# Runs ruff for linting and formatting checks across the project.
uv run ruff check . --fix

echo "Running pyright..."
# Runs pyright for static type checking. Assumes pyright is executable in the environment.
uv run pyright

# --- Static Type Checking ---
echo "Running mypy..."
# Runs mypy on the src directory for static type checking.
uv run mypy

# --- Unit Tests ---
echo "Running pytest unit tests..."
uv run pytest tests/unit/


echo "Pre-commit checks passed successfully."
echo "✅ Pre-commit checks completed."
echo "Run scripts/pre_merge_checks.sh before merging to exercise security, backend, and frontend suites."
exit 0
