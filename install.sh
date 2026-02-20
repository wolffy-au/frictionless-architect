#!/bin/sh

npm install -g @google/gemini-cli
uv tool install --upgrade specify-cli --force --from git+https://github.com/github/spec-kit.git
# Create new project
# specify init <PROJECT_NAME>
# Or initialize in existing project
# specify init --ai gemini --script sh --here --force
# Check installed tools
specify check
specify init --ai gemini --script sh --here --force



# One-off
# uvx --from git+https://github.com/github/spec-kit.git specify init . --ai gemini --script sh --here --force

# Upgrade
# uv tool install --upgrade specify-cli --force --from git+https://github.com/github/spec-kit.git
