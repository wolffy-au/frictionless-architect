"""Detector-category/failure-mode config: a local TOML file outside the repo tree
(research.md R4), mirroring `llm-provider-config`'s `store.py` pattern.

The path is `$PII_GATEWAY_CONFIG_PATH` if set, else
`~/.config/frictionless-architect/pii-gateway.toml`. A missing file seeds the
ADR-0014 defaults below rather than meaning "nothing configured".
"""

from __future__ import annotations

import contextlib
import os
import tomllib
from pathlib import Path

import tomli_w

from pii_gateway.detectors import ALL_ENTITIES
from pii_gateway.models import DetectorCategoryConfiguration, ScrubAction

PATH_ENV_VAR = "PII_GATEWAY_CONFIG_PATH"

#: The context whose default differs from every other context (ADR-0014 amendment).
CONVERSATIONAL_AUTHORING_CONTEXT = "conversational-authoring"

#: Known contexts registered at this feature's scope (plan.md Scale/Scope).
KNOWN_CONTEXTS = ["spec-generator", "governance-eval", CONVERSATIONAL_AUTHORING_CONTEXT]


def default_config_path() -> Path:
    """Return where the config file lives.

    Returns:
        ``$PII_GATEWAY_CONFIG_PATH`` if set, else
        ``~/.config/frictionless-architect/pii-gateway.toml``.
    """
    override = os.environ.get(PATH_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / ".config" / "frictionless-architect" / "pii-gateway.toml"


def _seed_default(context: str) -> DetectorCategoryConfiguration:
    failure_mode = (
        ScrubAction.FLAGGED_FOR_REVIEW
        if context == CONVERSATIONAL_AUTHORING_CONTEXT
        else ScrubAction.REDACTED_AND_PROCEEDED
    )
    return DetectorCategoryConfiguration(
        context=context, active_categories=set(ALL_ENTITIES), failure_mode=failure_mode
    )


def default_configurations() -> dict[str, DetectorCategoryConfiguration]:
    """Return the ADR-0014-seeded default for every known context."""
    return {context: _seed_default(context) for context in KNOWN_CONTEXTS}


def load_config(path: Path | None = None) -> dict[str, DetectorCategoryConfiguration]:
    """Read the config file, keyed by context.

    Args:
        path: File to read; defaults to ``default_config_path()``.

    Returns:
        One `DetectorCategoryConfiguration` per context; the ADR-0014 defaults for
        every known context not present in the file.
    """
    target = path or default_config_path()
    configs = default_configurations()
    if not target.exists():
        return configs
    with target.open("rb") as handle:
        raw = tomllib.load(handle)
    for context, entry in raw.get("contexts", {}).items():
        configs[context] = DetectorCategoryConfiguration.model_validate({"context": context, **entry})
    return configs


def resolve_context(context: str, configs: dict[str, DetectorCategoryConfiguration]) -> DetectorCategoryConfiguration:
    """Pick the config for `context`, falling back to the global default.

    An unrecognized context falls back to the global (`redacted_and_proceeded`)
    default rather than `conversational-authoring`'s differentiated one (spec Edge
    Cases).
    """
    if context in configs:
        return configs[context]
    return _seed_default(context)


def save_config(configs: dict[str, DetectorCategoryConfiguration], path: Path | None = None) -> Path:
    """Write the config file, creating parent directories.

    Args:
        configs: One `DetectorCategoryConfiguration` per context.
        path: File to write; defaults to ``default_config_path()``.

    Returns:
        The path written.
    """
    target = path or default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contexts": {
            context: config.model_dump(mode="json", exclude={"context"}) for context, config in configs.items()
        }
    }
    target.write_text(tomli_w.dumps(payload), encoding="utf-8")
    with contextlib.suppress(OSError):  # e.g. drvfs/9p mounts; the file holds no secrets either way
        target.chmod(0o600)
    return target
