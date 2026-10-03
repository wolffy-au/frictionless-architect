"""Turn "component X wants an LLM" into the arguments for a `litellm.completion` call."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llm_provider_config.credentials import get_api_key
from llm_provider_config.settings import LlmSettings, Provider
from llm_provider_config.store import load_settings

# litellm model-string prefixes; ollama_chat targets Ollama's chat endpoint.
_PREFIX: dict[Provider, str] = {
    Provider.OPENAI: "openai",
    Provider.GEMINI: "gemini",
    Provider.ANTHROPIC: "anthropic",
    Provider.OLLAMA: "ollama_chat",
}
DEFAULT_OLLAMA_API_BASE = "http://localhost:11434"


@dataclass(frozen=True)
class ResolvedCall:
    """Everything `litellm.completion` needs besides the messages."""

    model: str
    api_key: str | None = None
    api_base: str | None = None
    params: dict[str, Any] = field(default_factory=dict[str, Any])

    def completion_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": self.model, **self.params}
        if self.api_key is not None:
            kwargs["api_key"] = self.api_key
        if self.api_base is not None:
            kwargs["api_base"] = self.api_base
        return kwargs


def resolve_call(component: str, settings: LlmSettings | None = None) -> ResolvedCall:
    """Resolve provider, model, params and credential for `component`.

    Raises `NotConfiguredError` or `MissingCredentialError` when it cannot.
    """
    chosen = (settings or load_settings()).resolve(component)
    api_base = chosen.api_base
    if api_base is None and chosen.provider is Provider.OLLAMA:
        api_base = DEFAULT_OLLAMA_API_BASE
    return ResolvedCall(
        model=f"{_PREFIX[chosen.provider]}/{chosen.model}",
        api_key=get_api_key(chosen),
        api_base=api_base,
        params=dict(chosen.params),
    )
