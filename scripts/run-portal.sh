#!/bin/bash

# Runs the portal: hosts the platform packages' UIs under one app (ADR-0020).

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
unset VIRTUAL_ENV

root="$(git rev-parse --show-toplevel)"
cd "$root/platform"

poetry run uvicorn portal.app:app \
  --reload \
  --app-dir packages/portal/src \
  --host 127.0.0.1 \
  --port 8001
