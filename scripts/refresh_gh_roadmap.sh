#!/bin/bash
# Refresh the generated GitHub roadmap layer (ADR-0035): import from GitHub, rebuild the model XML,
# regenerate diagrams, then show what changed for review. Needs an authenticated `gh`.
# Writes nothing if GitHub is unreachable (importer exit 2). Review and commit the result yourself.
#
# Usage: scripts/refresh_gh_roadmap.sh [--check] [--no-diagrams]
#   --check        only report whether the layer is stale (exit 1 if so); change nothing
#   --no-diagrams  skip render_diagrams.py (e.g. no PlantUML available)

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CHECK=0
DIAGRAMS=1
for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    --no-diagrams) DIAGRAMS=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [ "$CHECK" -eq 1 ]; then
  exec poetry run python architecture/model/import_gh_roadmap.py --check
fi

poetry run python architecture/model/import_gh_roadmap.py
poetry run python architecture/model/build.py
if [ "$DIAGRAMS" -eq 1 ]; then
  poetry run python architecture/model/render_diagrams.py
fi

echo
echo "Changes to review (nothing is committed):"
git --no-pager status --short -- architecture/model
