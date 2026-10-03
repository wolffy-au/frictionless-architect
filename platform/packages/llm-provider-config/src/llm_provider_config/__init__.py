"""LLM provider configuration.

Resolves the provider, model and credential for an LLM call from a global default
plus optional per-component overrides, over `litellm`. Secrets come from the OS
keychain via `keyring`, with a labelled environment-variable fallback. See ADR-0034.
"""

from llm_provider_config.credentials import (
    MissingCredentialError,
    delete_api_key,
    get_api_key,
    key_source,
    set_api_key,
)
from llm_provider_config.resolve import ResolvedCall, resolve_call
from llm_provider_config.router import Component, create_settings_router
from llm_provider_config.settings import LlmSettings, NotConfiguredError, Provider, ProviderSettings
from llm_provider_config.store import default_config_path, load_settings, save_settings

__all__ = [
    "Component",
    "LlmSettings",
    "MissingCredentialError",
    "NotConfiguredError",
    "Provider",
    "ProviderSettings",
    "ResolvedCall",
    "create_settings_router",
    "default_config_path",
    "delete_api_key",
    "get_api_key",
    "key_source",
    "load_settings",
    "resolve_call",
    "save_settings",
    "set_api_key",
]
