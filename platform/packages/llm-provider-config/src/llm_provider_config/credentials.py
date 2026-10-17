"""API-key resolution: OS keychain first, labelled environment-variable fallback (ADR-0034).

Keys live in the OS credential store via `keyring`, never in a repo file. Where no
keychain backend exists (headless CI, devcontainers) or the entry is absent, the
provider's conventional environment variable is used as an escape hatch. That is
plaintext, so every use is logged as a warning. Ollama and GitHub Copilot need no key.
"""

from __future__ import annotations

import logging
import os

import keyring
from keyring.errors import KeyringError

from llm_provider_config.settings import KEYLESS_PROVIDERS, Provider, ProviderSettings

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
    """Return the API key for `settings`, or None for providers that need none.

    The OS keychain is tried first, then the provider's environment variable (logged as
    a plaintext warning).

    Args:
        settings: The provider settings naming the provider and optional keyring entry.

    Returns:
        The API key, or ``None`` for providers in ``KEYLESS_PROVIDERS``.

    Raises:
        MissingCredentialError: If the provider needs a key and neither the keychain
            nor the environment has one.
    """
    if settings.provider in KEYLESS_PROVIDERS:
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
    """Store an API key in the OS keychain.

    Args:
        ref: Keyring entry name (the provider name unless a ``credential_ref`` is set).
        key: The API key to store.

    Raises:
        keyring.errors.KeyringError: If no usable keychain backend exists.
    """
    keyring.set_password(SERVICE_NAME, ref, key)


def delete_api_key(ref: str) -> None:
    """Remove an API key from the OS keychain.

    Args:
        ref: Keyring entry name to delete.

    Raises:
        keyring.errors.KeyringError: If there is no such entry or no usable backend.
    """
    keyring.delete_password(SERVICE_NAME, ref)


def key_source(settings: ProviderSettings) -> str:
    """Where `get_api_key` would find the key, without returning it.

    Args:
        settings: The provider settings to look up.

    Returns:
        One of ``"not-needed"`` (Ollama, Copilot), ``"keychain"``, ``"environment"`` or ``"missing"``.
    """
    if settings.provider in KEYLESS_PROVIDERS:
        return "not-needed"
    try:
        if keyring.get_password(SERVICE_NAME, _ref(settings)):
            return "keychain"
    except KeyringError:
        pass
    return "environment" if os.environ.get(ENV_VARS[settings.provider]) else "missing"
