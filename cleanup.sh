#!/bin/sh

rm -rf `find -type d -name __pycache__`
rm -rf `find -type d -name .mypy_cache`
rm -rf .aider.tags.*/ .chainlit/ .files/ .coverage cov.json .pytest_cache/ .ruff_cache/ build/ dist/ test_sqlite_models_*.db
rm -rf db/*
rm -rf ~/.embedchain/
