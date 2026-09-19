#!/bin/bash

# Mirror the repo-tracked skills and agents into .claude/ as relative symlinks.
#
# .agents/skills/* and .agents/agents are the tracked source of truth; Claude
# Code only discovers skills/agents under .claude/ (which is git-ignored), so
# they have to be linked in on every fresh checkout. The devcontainer's
# post-create.sh calls this, but a new `git worktree` gets its own git-ignored
# .claude/, so run this by hand there too:
#
#     ./scripts/link-claude-skills.sh
#
# Externally-sourced skills (caveman, session-handoff) are real directories
# installed elsewhere and are left untouched.

set -euo pipefail

# Operate on the checkout this script lives in (works from any subdirectory and
# from a linked worktree).
REPO_ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$REPO_ROOT"

echo -e "\n🔗 Linking .agents skills and agents into .claude/..."
mkdir -p .claude/skills
for skill_dir in .agents/skills/*/; do
    [ -f "${skill_dir}SKILL.md" ] || continue
    name=$(basename "$skill_dir")
    ln -sfn "../../.agents/skills/${name}" ".claude/skills/${name}"
done
ln -sfn "../.agents/agents" ".claude/agents"
echo "✅ Done"
