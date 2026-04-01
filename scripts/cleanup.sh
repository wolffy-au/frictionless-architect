#!/bin/bash
set -euo pipefail

cleanup_dirs=(
  "__pycache__"
  ".mypy_cache"
  ".ruff_cache"
  ".pytest_cache"
)

for dir in "${cleanup_dirs[@]}"; do
  find . -type d -name "$dir" -prune -exec rm -rf {} +
done

rm -rf .chainlit .files build dist db .coverage cov.json ~/.embedchain .aider.tags.* test_sqlite_models_*.db
