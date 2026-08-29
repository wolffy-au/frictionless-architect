#!/bin/bash

# Exit immediately on error, treat unset variables as an error, and fail if any command in a pipeline fails.
set -euo pipefail

# Function to run a command and show logs only on error
run_command() {
    local command_to_run="$*"
    local output
    local exit_code
    
    # Capture all output (stdout and stderr)
    output=$(eval "$command_to_run" 2>&1) || exit_code=$?
    exit_code=${exit_code:-0}
    
    if [ $exit_code -ne 0 ]; then
        echo -e "\033[0;31m[ERROR] Command failed (Exit Code $exit_code): $command_to_run\033[0m" >&2
        echo -e "\033[0;31m$output\033[0m" >&2
        
        exit $exit_code
    fi
}

# Prints the tag_name of a GitHub repo's latest release, or nothing if it
# can't be resolved.
github_latest_release_tag() {
    local repo="$1"   # e.g. github/spec-kit
    curl -fsSL "https://api.github.com/repos/${repo}/releases/latest" \
        | grep -m1 '"tag_name"' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/'
}

# Installing UV (Python package manager)
echo -e "\n🐍 Installing UV - Python Package Manager..."
run_command "pip install uv"
echo "✅ Done"

# Installing Poetry (Python package manager)
echo -e "\n🐍 Installing Poetry - Python Package Manager..."
run_command "pip install poetry"
echo "✅ Done"

# Installing CLI-based AI Agents

# echo -e "\n🤖 Installing Copilot CLI..."
# run_command "npm install -g @github/copilot@latest"
# echo "✅ Done"

# echo -e "\n🤖 Installing Codex CLI..."
# run_command "npm install -g @openai/codex@latest"
# echo "✅ Done"

# echo -e "\n🤖 Installing Gemini CLI..."
# run_command "npm install -g @google/gemini-cli@latest"
# echo "✅ Done"

echo -e "\n🤖 Installing Claude CLI..."
run_command "curl -fsSL https://claude.ai/install.sh | bash"
echo "✅ Done"

echo -e "\n🤖 Installing Specify CLI (latest release)..."
SPEC_KIT_TAG=$(github_latest_release_tag "github/spec-kit") || SPEC_KIT_TAG=""
if [[ -z "$SPEC_KIT_TAG" ]]; then
    echo "⚠️  Could not resolve latest spec-kit release — falling back to main"
    run_command "uv tool install --force specify-cli --from git+https://github.com/github/spec-kit.git"
else
    run_command "uv tool install --force specify-cli --from git+https://github.com/github/spec-kit.git@${SPEC_KIT_TAG}"
fi
echo "✅ Done"

# ── Spec Kit scaffolding: regenerate to match the installed CLI ──────────────
# .specify/{templates,scripts,integrations} and .agents/skills/speckit-* are
# git-ignored and rebuilt here. .specify/speckit.lock (tracked) pins the version;
# if a rebuild changes it, the working tree goes dirty so the bump gets reviewed
# and committed. .specify/memory/ is hand-owned and never touched.
echo -e "\n🧩 Regenerating Spec Kit scaffolding..."
export PATH="$HOME/.local/bin:$PATH"
WORKSPACE_DIR="/workspaces/frictionless-architect"
SPECKIT_MANIFEST="$WORKSPACE_DIR/.specify/integrations/speckit.manifest.json"
LOCK_FILE="$WORKSPACE_DIR/.specify/speckit.lock"

LOCKED_VERSION=$(jq -r '.speckit_version // "none"' "$LOCK_FILE" 2>/dev/null || echo "none")

# Guard the hand-owned governance files against any tooling side effects.
cp -r "$WORKSPACE_DIR/.specify/memory" /tmp/speckit-memory.bak 2>/dev/null || true

if [[ -f "$SPECKIT_MANIFEST" ]]; then
    # Existing scaffolding present → diff-aware upgrade (blocks on modified managed files).
    specify integration upgrade codex --script sh \
        || echo "⚠️  'specify integration upgrade' did not complete cleanly — run 'specify integration status'."
else
    # Fresh clone (scaffolding is git-ignored and absent) → scaffold from bundled assets.
    specify init --here --force --non-interactive --ignore-agent-tools \
        --integration codex --integration-options "--skills" \
        || echo "⚠️  'specify init' did not complete cleanly."
fi

# Restore the governance files if anything changed them.
if [[ -d /tmp/speckit-memory.bak ]] && ! diff -rq /tmp/speckit-memory.bak "$WORKSPACE_DIR/.specify/memory" >/dev/null 2>&1; then
    cp -rf /tmp/speckit-memory.bak/. "$WORKSPACE_DIR/.specify/memory/"
    echo "ℹ️  Restored hand-owned .specify/memory/ (tooling had modified it)."
fi

NEW_VERSION=$(jq -r '.version // "none"' "$SPECKIT_MANIFEST" 2>/dev/null || echo "none")

if [[ "$NEW_VERSION" != "none" && "$NEW_VERSION" != "$LOCKED_VERSION" ]]; then
    jq --arg v "$NEW_VERSION" '.speckit_version = $v' "$LOCK_FILE" > "$LOCK_FILE.tmp" \
        && mv "$LOCK_FILE.tmp" "$LOCK_FILE"
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    echo " ⚠️  Spec Kit version changed: ${LOCKED_VERSION} → ${NEW_VERSION}"
    echo "     .specify/speckit.lock has been bumped. Review the regenerated"
    echo "     scaffolding and skills, then commit the lock change."
    echo "════════════════════════════════════════════════════════════════════════"
    if [[ -n "${CI:-}" ]]; then
        echo "CI: exiting non-zero so the version bump is reviewed deliberately."
        exit 1
    fi
fi
echo "✅ Done"

# Installing PlantUML
echo -e "\n🌱 Installing PlantUML..."
run_command "sudo apt-get update"
run_command "sudo apt-get install -y plantuml"
run_command "sudo curl -L https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar -o /usr/share/plantuml/plantuml.jar"
echo "✅ Done"

# Installing GitHub CLI
echo -e "\n🐙 Installing GitHub CLI..."
run_command "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
run_command "sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg"
run_command "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
run_command "sudo apt-get update && sudo apt install -y gh"
echo "✅ Done"

if [ -f /workspaces/frictionless-architect/frontend/package.json ]; then
    echo -e "\n🌐 Installing frontend dependencies and Playwright browser..."
    run_command "cd /workspaces/frictionless-architect/frontend && npm config set bin-links false && npm install && node ./node_modules/playwright/cli.js install --with-deps chromium"
    echo "✅ Done"
fi

# Installing Snyk CLI
echo -e "\n🔒 Installing Snyk CLI..."
run_command "npm install -g snyk@latest"
echo "✅ Done"

# Installing Claude Code Skills
# Skills are pulled from each project's latest GitHub *release* tag (not a
# branch, since raw.githubusercontent.com 404s on paths that only exist on
# main/master) and the whole skill directory is copied so any supporting
# files (references/, README, etc.) come along with SKILL.md.
echo -e "\n🧠 Installing Claude Code Skills..."

install_skill_from_release() {
    local repo="$1"          # e.g. JuliusBrussee/caveman
    local skill_path="$2"    # path of the skill dir inside the repo
    local dest_dir="$3"      # e.g. .claude/skills/caveman
    local label="$4"

    local tag
    tag=$(github_latest_release_tag "$repo") || tag=""

    if [[ -z "$tag" ]]; then
        echo "⚠️  ${label}: could not resolve latest release — using repo version"
        return 0
    fi

    local tmp
    tmp=$(mktemp -d)
    local extracted_root=""
    if curl -fsSL "https://github.com/${repo}/archive/refs/tags/${tag}.tar.gz" -o "${tmp}/skill.tar.gz" \
        && tar -xzf "${tmp}/skill.tar.gz" -C "${tmp}"; then
        extracted_root=$(find "${tmp}" -mindepth 1 -maxdepth 1 -type d | head -1)
    fi

    if [[ -n "$extracted_root" && -d "${extracted_root}/${skill_path}" ]]; then
        mkdir -p "$(dirname "$dest_dir")"
        rm -rf "$dest_dir"
        cp -r "${extracted_root}/${skill_path}" "$dest_dir"
        echo "✅ ${label}@${tag} installed"
    else
        echo "⚠️  ${label}@${tag} download failed — using repo version"
    fi
    rm -rf "$tmp"
}

install_skill_from_release "JuliusBrussee/caveman" "skills/caveman" ".claude/skills/caveman" "caveman"
install_skill_from_release "REMvisual/claude-handoff" "skills/handoff" ".claude/skills/session-handoff" "session-handoff"
echo "✅ Done"

# Linking repo-tracked skills & agents into .claude/
# .agents/skills/* and .agents/agents are the tracked source of truth; Claude
# Code only discovers skills/agents under .claude/ (which is git-ignored), so
# mirror them there as relative symlinks on every create. Externally-sourced
# skills above (caveman, session-handoff) are real dirs and are left alone.
echo -e "\n🔗 Linking .agents skills and agents into .claude/..."
mkdir -p .claude/skills
for skill_dir in .agents/skills/*/; do
    [ -f "${skill_dir}SKILL.md" ] || continue
    name=$(basename "$skill_dir")
    ln -sfn "../../.agents/skills/${name}" ".claude/skills/${name}"
done
ln -sfn "../.agents/agents" ".claude/agents"
echo "✅ Done"

# Installing Git Hooks
echo -e "\n🪝 Installing Git Hooks..."
run_command "pip install pre-commit"
run_command "pre-commit install --hook-type pre-commit --hook-type pre-push"
echo "✅ Done"

echo -e "\n🧹 Cleaning cache..."
run_command "sudo apt-get autoclean"
run_command "sudo apt-get clean"

echo "✅ Setup completed. Happy coding! 🚀"
