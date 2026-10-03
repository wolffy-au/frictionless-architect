"""Settings model: override-else-default resolution and validation."""

import pytest
from llm_provider_config import LlmSettings, NotConfiguredError, Provider, ProviderSettings
from pydantic import ValidationError

_DEFAULT = ProviderSettings(provider=Provider.OPENAI, model="gpt-4o")
_OVERRIDE = ProviderSettings(provider=Provider.OLLAMA, model="llama3")


def test_resolve_uses_the_component_override_when_present() -> None:
    settings = LlmSettings(default=_DEFAULT, components={"pkg.step": _OVERRIDE})

    assert settings.resolve("pkg.step") == _OVERRIDE


def test_resolve_falls_back_to_the_global_default() -> None:
    settings = LlmSettings(default=_DEFAULT, components={"pkg.step": _OVERRIDE})

    assert settings.resolve("other.step") == _DEFAULT


def test_resolve_raises_when_nothing_applies() -> None:
    with pytest.raises(NotConfiguredError, match="pkg.step"):
        LlmSettings().resolve("pkg.step")


def test_resolve_ignores_other_components_overrides_without_a_default() -> None:
    with pytest.raises(NotConfiguredError):
        LlmSettings(components={"a": _OVERRIDE}).resolve("b")


def test_empty_model_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProviderSettings(provider=Provider.OPENAI, model="")


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProviderSettings.model_validate({"provider": "bogus", "model": "x"})


def test_secret_fields_are_not_part_of_the_model() -> None:
    with pytest.raises(ValidationError):
        ProviderSettings.model_validate({"provider": "openai", "model": "x", "api_key": "sk-secret"})
