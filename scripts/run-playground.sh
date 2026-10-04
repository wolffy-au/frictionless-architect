#!/bin/bash

# Runs the controls-compliance-catalog control conversion playground (GH #76)
# as a local dev server: paste an OSCAL control/catalog (YAML or JSON) and see the real
# compliance-trestle Markdown rendering at /playground.

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
unset VIRTUAL_ENV

root="$(git rev-parse --show-toplevel)"
cd "$root/platform"

poetry run uvicorn controls_compliance_catalog.app:app \
  --reload \
  --app-dir packages/controls-compliance-catalog/src \
  --host 127.0.0.1 \
  --port 8001
