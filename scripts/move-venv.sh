#!/bin/sh

set -e

VENV_DIR="$HOME/.cache/pypoetry/virtualenvs/sdd_cash_manager"

# create parent directory only
mkdir -p "$(dirname "$VENV_DIR")"

# create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    uv venv "$VENV_DIR"
fi

# create workspace symlink if missing
if [ ! -d ".venv" ]; then
    rm -rf .venv
fi
if [ ! -e ".venv" ]; then
    ln -s "$VENV_DIR" .venv
fi

# uv cache clean
rm uv.lock
uv sync --upgrade --all-groups
