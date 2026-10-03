"""Load the playground's LLM prompts from ``prompts.yaml`` (GH #76).

The prompts live in YAML, not Python, so they can be tuned without touching code.
The file is re-read on every call, so edits take effect without a server restart.
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml

PROMPTS_PATH = pathlib.Path(__file__).with_name("prompts.yaml")


class PromptConfigError(Exception):
    """Raised when ``prompts.yaml`` is missing, malformed, or lacks a requested prompt."""


def load_system_prompt(name: str) -> str:
    """Return the ``system`` prompt text for the prompt called ``name``."""
    try:
        data: Any = yaml.safe_load(PROMPTS_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PromptConfigError(f"Cannot read prompts from {PROMPTS_PATH}: {exc}") from exc

    entry = data.get(name) if isinstance(data, dict) else None
    system = entry.get("system") if isinstance(entry, dict) else None
    if not isinstance(system, str) or not system.strip():
        raise PromptConfigError(f"{PROMPTS_PATH} has no non-empty '{name}.system' prompt.")
    return system.strip()
