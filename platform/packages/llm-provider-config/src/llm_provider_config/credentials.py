"""API-key resolution: OS keychain first, labelled environment-variable fallback (ADR-0034).

Keys live in the OS credential store via `keyring`, never in a repo file. Where no
keychain backend exists (headless CI, devcontainers) or the entry is absent, the
provider's conventional environment variable is used as an escape hatch. That is
plaintext, so every use is logged as a warning. Ollama needs no key.
"""

from __future__ import annotations

import logging
import os

import keyring
from keyring.errors import KeyringError

from llm_provider_config.settings import Provider, ProviderSettings

SERVICE_NAME = "frictionless-architect.llm-provider-config"

ENV_VARS: dict[Provider, str] = {
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.GEMINI: "GEMINI_API_KEY",
    Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
}

_logger = logging.getLogger(__name__)


class MissingCredentialError(Exception):
    """Raised when a provider needs an API key and neither source has one."""


def _ref(settings: ProviderSettings) -> str:
    return settings.credential_ref or settings.provider.value


def get_api_key(settings: ProviderSettings) -> str | None:
    """Return the API key for `settings`, or None for providers that need none."""
    if settings.provider is Provider.OLLAMA:
        return None
    ref = _ref(settings)
    try:
        key = keyring.get_password(SERVICE_NAME, ref)
    except KeyringError as exc:
        _logger.debug("No usable keyring backend (%s); trying the environment.", exc)
        key = None
    if key:
        return key
    env_var = ENV_VARS[settings.provider]
    env_key = os.environ.get(env_var)
    if env_key:
        _logger.warning(
            "Using %s from the environment (plaintext) because the OS keychain has no %r entry.",
            env_var,
            ref,
        )
        return env_key
    raise MissingCredentialError(
        f"No API key for {settings.provider.value}: store one under keyring entry {ref!r} or set {env_var}."
    )


def set_api_key(ref: str, key: str) -> None:
    keyring.set_password(SERVICE_NAME, ref, key)


def delete_api_key(ref: str) -> None:
    keyring.delete_password(SERVICE_NAME, ref)
