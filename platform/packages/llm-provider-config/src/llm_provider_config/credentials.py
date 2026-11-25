"""API-key resolution: OS keychain first, labelled environment-variable fallback (ADR-0034).

Keys live in the OS credential store via `keyring`, never in a repo file. Where no
keychain backend exists (headless CI, devcontainers) or the entry is absent, the
provider's conventional environment variable is used as an escape hatch. That is
plaintext, so every use is logged as a warning. Ollama and GitHub Copilot need no key.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
from collections.abc import Mapping, Sequence
from typing import cast

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


class InvalidCredentialError(MissingCredentialError):
    """Raised for a secret *reference* (``os.environ/NAME``), or a credential in call params.

    litellm resolves ``os.environ/NAME`` values passed as ``api_key`` to that environment
    variable (CVE-2026-108575, ``get_secret``). A user-supplied key must never be able to
    make the library read an arbitrary environment variable, so such values are refused on
    store and on use. Subclasses `MissingCredentialError` so existing callers that treat
    "no usable key" as not-configured handle it unchanged.
    """


_SECRET_REFERENCE_PREFIX = "os.environ/"
# Parameter names that carry a credential. Token *counts* (`max_tokens`) must not match.
_CREDENTIAL_PARAM = re.compile(
    r"api[_-]?key|authorization|secret|password|credential|access_key|(^|_)(ad|auth|session|identity)_token"
)


def _reject_secret_reference(key: str, origin: str) -> str:
    if key.strip().lower().startswith(_SECRET_REFERENCE_PREFIX):
        raise InvalidCredentialError(
            f"The API key from {origin} looks like a secret reference ({_SECRET_REFERENCE_PREFIX}...), "
            "not a literal key; refusing to use it."
        )
    return key


def check_params(params: Mapping[str, object]) -> None:
    """Refuse call parameters that carry a credential or a secret reference, at any depth.

    ``params`` is passed straight to litellm, so without this it bypasses the key guard:
    a keyless provider has no key of its own to overwrite ``params["api_key"]``.

    Args:
        params: The free-form call parameters of one configuration.

    Raises:
        InvalidCredentialError: If a name is a credential's, or a value is ``os.environ/...``.
    """
    _check_param(params)


def _check_param(value: object) -> None:
    if isinstance(value, Mapping):
        for name, item in cast("Mapping[str, object]", value).items():
            if _CREDENTIAL_PARAM.search(name.lower()):
                raise InvalidCredentialError(
                    f"params may not set {name!r}: credentials belong in the keychain or the "
                    "provider's environment variable."
                )
            _check_param(item)
    elif isinstance(value, list | tuple):
        for item in cast("Sequence[object]", value):
            _check_param(item)
    elif isinstance(value, str) and value.strip().lower().startswith(_SECRET_REFERENCE_PREFIX):
        raise InvalidCredentialError(
            f"A value in params is a secret reference ({_SECRET_REFERENCE_PREFIX}...); refusing to use it."
        )


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
        return _reject_secret_reference(key, f"keyring entry {ref!r}")
    env_var = ENV_VARS[settings.provider]
    env_key = os.environ.get(env_var)
    if env_key:
        _logger.warning(
            "Using %s from the environment (plaintext) because the OS keychain has no %r entry.",
            env_var,
            ref,
        )
        return _reject_secret_reference(env_key, env_var)
    raise MissingCredentialError(
        f"No API key for {settings.provider.value}: store one under keyring entry {ref!r} or set {env_var}."
    )


def set_api_key(ref: str, key: str) -> None:
    """Store an API key in the OS keychain.

    Args:
        ref: Keyring entry name (the provider name unless a ``credential_ref`` is set).
        key: The API key to store.

    Raises:
        InvalidCredentialError: If `key` is a secret reference such as ``os.environ/NAME``.
        keyring.errors.KeyringError: If no usable keychain backend exists.
    """
    keyring.set_password(SERVICE_NAME, ref, _reject_secret_reference(key, "the request"))


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
    with contextlib.suppress(KeyringError):  # no usable keyring backend: fall back to the environment
        if keyring.get_password(SERVICE_NAME, _ref(settings)):
            return "keychain"
    return "environment" if os.environ.get(ENV_VARS[settings.provider]) else "missing"
