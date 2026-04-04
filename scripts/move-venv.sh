#!/bin/sh

set -euo pipefail

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
if [ -f uv.lock ]; then
    rm uv.lock
fi
if [ -f uv.lock ]; then
    rm uv.lock
fi
if [ -f poetry.lock ]; then
    rm poetry.lock
fi
poetry env use "$VENV_DIR/bin/python"
uv sync --upgrade --all-groups
