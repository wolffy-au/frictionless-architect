"""Non-secret settings storage: a local TOML file outside the repo tree (ADR-0034).

The path is `$LLM_PROVIDER_CONFIG_PATH` if set, else
`~/.config/frictionless-architect/llm.toml`. A missing file means "nothing configured".
"""

from __future__ import annotations

import contextlib
import os
import tomllib
from pathlib import Path

import tomli_w

from llm_provider_config.settings import LlmSettings

PATH_ENV_VAR = "LLM_PROVIDER_CONFIG_PATH"


def default_config_path() -> Path:
    override = os.environ.get(PATH_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / ".config" / "frictionless-architect" / "llm.toml"


def load_settings(path: Path | None = None) -> LlmSettings:
    target = path or default_config_path()
    if not target.exists():
        return LlmSettings()
    with target.open("rb") as handle:
        return LlmSettings.model_validate(tomllib.load(handle))


def save_settings(settings: LlmSettings, path: Path | None = None) -> Path:
    target = path or default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = settings.model_dump(mode="json", exclude_none=True)
    target.write_text(tomli_w.dumps(payload), encoding="utf-8")
    with contextlib.suppress(OSError):  # e.g. drvfs/9p mounts; the file holds no secrets either way
        target.chmod(0o600)
    return target
