#!/bin/bash

# Refreshes every dependency source in the repo: the root Poetry lock, the
# platform/ Poetry lock, the pre-commit hook versions, and the third_party/
# submodules. Doesn't commit anything — review `git status`/`git diff` and
# commit what you want to keep. Run scripts/pre_merge_checks.sh afterwards to
# verify the bumped versions still pass the full gate.

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

root="$(git rev-parse --show-toplevel)"
cd "$root"

echo "Updating root poetry.lock..."
poetry update
poetry install

echo "Updating platform/poetry.lock..."
(cd platform && poetry update && poetry install)

echo "Updating pre-commit hook versions..."
poetry run pre-commit autoupdate

echo "Updating third_party/ submodules..."
# Submodule clone/checkout steps chmod .git/modules/.../config.lock, which
# fails EPERM unprivileged on this workspace's drvfs mount (see AGENTS.md's
# "Known environment quirks"); sudo sidesteps the UID-mapping check that
# causes it.
sudo git submodule update --remote --merge --recursive

echo "✅ Update pass complete. Review changes with 'git status' / 'git diff', then run:"
echo "   bash scripts/pre_merge_checks.sh"
