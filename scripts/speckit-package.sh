#!/usr/bin/env bash
# Run a vendored .specify/scripts/bash/<script> against a package's own spec
# sequence instead of the root specs/ tree (ADR-0004, GH #107).
#
# .specify/scripts/bash/ is git-ignored and regenerated wholesale by
# `specify integration upgrade` against whatever specify-cli release is
# current (see .claude/skills/README.md) — it must never be hand-patched,
# or the patch is silently lost on the next regeneration. Instead this
# wrapper is tracked and uses SPECIFY_INIT_DIR, an override `common.sh`
# already documents ("running a Spec Kit command against a member project
# from a monorepo root without cd"). Each package that wants its own `NNN-`
# sequence carries a tracked `.specify` symlink back to the root install
# (one source of truth, not a per-package copy); SPECIFY_INIT_DIR points
# the vendored script's repo-root resolution at that package directory, so
# its hardcoded `$REPO_ROOT/specs` lands on `platform/packages/<name>/specs`.
#
# Usage:
#   scripts/speckit-package.sh --package <name> <script> [script-args...]
#   scripts/speckit-package.sh <script> [script-args...]   # root EPIC-* specs, unchanged
#
# <script> is any .specify/scripts/bash/*.sh name, e.g. create-new-feature.sh,
# check-prerequisites.sh, setup-plan.sh, setup-tasks.sh.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

PACKAGE=""
if [ "${1:-}" = "--package" ]; then
    if [ $# -lt 2 ]; then
        echo "Error: --package requires a value" >&2
        exit 1
    fi
    PACKAGE="$2"
    shift 2
fi

if [ $# -lt 1 ]; then
    echo "Usage: $0 [--package <name>] <script> [script-args...]" >&2
    exit 1
fi

SCRIPT_NAME="$1"
shift

VENDORED_SCRIPT="$REPO_ROOT/.specify/scripts/bash/$SCRIPT_NAME"
if [ ! -f "$VENDORED_SCRIPT" ]; then
    echo "Error: $VENDORED_SCRIPT not found. Run 'specify integration upgrade claude' to (re)generate .specify/scripts/bash/." >&2
    exit 1
fi

if [ -n "$PACKAGE" ]; then
    PACKAGE_DIR="$REPO_ROOT/platform/packages/$PACKAGE"
    if [ ! -d "$PACKAGE_DIR" ]; then
        echo "Error: no such package: platform/packages/$PACKAGE" >&2
        exit 1
    fi
    if [ ! -e "$PACKAGE_DIR/.specify" ]; then
        echo "Error: $PACKAGE_DIR/.specify does not exist. Create it as a tracked symlink to the root .specify (ln -s ../../../.specify $PACKAGE_DIR/.specify) before giving this package its own spec sequence." >&2
        exit 1
    fi
    export SPECIFY_INIT_DIR="$PACKAGE_DIR"
fi

exec "$VENDORED_SCRIPT" "$@"
