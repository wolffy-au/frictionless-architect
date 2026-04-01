#!/bin/sh

# npm install -g @google/gemini-cli
# uv tool install --upgrade specify-cli --force --from git+https://github.com/github/spec-kit.git
uv tool install --upgrade specify-cli --force --from git+https://github.com/wolffy-au/spec-kit-aider.git@feat-speckit-aider
# uv tool install --upgrade aider-chat --force --from git+https://github.com/Aider-AI/aider.git
# uv tool install --upgrade aider-chat --force --from git+https://github.com/wolffy-au/aider-speckit.git@feat-spec-kit
# Create new project
# specify init <PROJECT_NAME>
# Or initialize in existing project
# specify init --ai gemini --script sh --here --force
# Check installed tools
specify check
specify init --ai codex --script sh --here --force



# One-off
# uvx --from git+https://github.com/github/spec-kit.git specify init . --ai gemini --script sh --here --force

# Upgrade
# uv tool install --upgrade specify-cli --force --from git+https://github.com/github/spec-kit.git
