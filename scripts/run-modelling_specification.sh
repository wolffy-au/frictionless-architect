#!/bin/bash

# Runs the modelling-specification ... (GH #108)

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
unset VIRTUAL_ENV

root="$(git rev-parse --show-toplevel)"
cd "$root/platform"

poetry run uvicorn modelling_specification.app:app \
  --reload \
  --app-dir packages/modelling-specification/src \
  --host 127.0.0.1 \
  --port 8001
