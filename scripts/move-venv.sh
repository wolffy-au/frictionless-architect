#!/bin/sh

set -e

VENV_DIR="$HOME/.cache/pypoetry/virtualenvs/frictionless-architect"

# create parent directory only
mkdir -p "$(dirname "$VENV_DIR")"

# create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    python -m venv "$VENV_DIR"
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
rm poetry.lock
poetry env use "$VENV_DIR/bin/python"
uv sync --upgrade --all-groups
