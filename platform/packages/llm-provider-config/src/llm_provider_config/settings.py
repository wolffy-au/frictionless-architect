"""Settings model: a global default plus optional per-component overrides (ADR-0034).

Resolution is "component override if present, else global default" — no deeper chain.
Settings never hold secrets, only an optional keyring reference (`credential_ref`).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Provider(StrEnum):
    """Providers supported on day 1."""

    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class NotConfiguredError(Exception):
    """Raised when no override and no global default applies to a component."""


class ProviderSettings(BaseModel):
    """Which provider and model to call, and with what parameters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Provider
    model: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict[str, Any])
    api_base: str | None = None
    # Name of the keyring entry holding the API key; defaults to the provider name.
    credential_ref: str | None = None


class LlmSettings(BaseModel):
    """Global default plus per-component overrides, keyed by component identifier."""

    model_config = ConfigDict(extra="forbid")

    default: ProviderSettings | None = None
    components: dict[str, ProviderSettings] = Field(default_factory=dict[str, ProviderSettings])

    def resolve(self, component: str) -> ProviderSettings:
        override = self.components.get(component)
        if override is not None:
            return override
        if self.default is not None:
            return self.default
        raise NotConfiguredError(f"No LLM provider is configured for {component!r} and there is no global default.")
