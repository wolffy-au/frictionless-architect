"""LLM provider configuration.

Resolves the provider, model and credential for an LLM call from a global default
plus optional per-component overrides, over `litellm`. Secrets come from the OS
keychain via `keyring`. See ADR-0034.
"""

__all__: list[str] = []
