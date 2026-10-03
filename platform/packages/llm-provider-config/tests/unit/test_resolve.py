"""resolve_call: settings + credentials -> litellm.completion arguments."""

from pathlib import Path

import pytest
from conftest import InMemoryKeyring
from llm_provider_config import (
    LlmSettings,
    MissingCredentialError,
    NotConfiguredError,
    Provider,
    ProviderSettings,
    resolve_call,
    save_settings,
    set_api_key,
)


def test_openai_call_carries_prefixed_model_key_and_params(fake_keyring: InMemoryKeyring) -> None:
    set_api_key("openai", "sk-k")
    settings = LlmSettings(
        default=ProviderSettings(provider=Provider.OPENAI, model="gpt-4o", params={"temperature": 0})
    )

    call = resolve_call("pkg.step", settings)

    assert call.completion_kwargs() == {"model": "openai/gpt-4o", "temperature": 0, "api_key": "sk-k"}


@pytest.mark.parametrize(
    ("provider", "expected_prefix"),
    [
        (Provider.GEMINI, "gemini/m"),
        (Provider.ANTHROPIC, "anthropic/m"),
        (Provider.OLLAMA, "ollama_chat/m"),
    ],
)
def test_each_provider_gets_its_litellm_prefix(
    provider: Provider, expected_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    call = resolve_call("c", LlmSettings(default=ProviderSettings(provider=provider, model="m")))

    assert call.model == expected_prefix


def test_ollama_defaults_to_the_local_endpoint_and_sends_no_key() -> None:
    call = resolve_call("c", LlmSettings(default=ProviderSettings(provider=Provider.OLLAMA, model="llama3")))

    assert call.completion_kwargs() == {"model": "ollama_chat/llama3", "api_base": "http://localhost:11434"}


def test_explicit_api_base_overrides_the_ollama_default() -> None:
    settings = LlmSettings(
        default=ProviderSettings(provider=Provider.OLLAMA, model="llama3", api_base="http://box:11434")
    )

    assert resolve_call("c", settings).api_base == "http://box:11434"


def test_component_override_beats_the_default(fake_keyring: InMemoryKeyring) -> None:
    settings = LlmSettings(
        default=ProviderSettings(provider=Provider.OPENAI, model="gpt-4o"),
        components={"c": ProviderSettings(provider=Provider.OLLAMA, model="llama3")},
    )

    assert resolve_call("c", settings).model == "ollama_chat/llama3"


def test_unconfigured_component_raises() -> None:
    with pytest.raises(NotConfiguredError):
        resolve_call("c", LlmSettings())


@pytest.mark.usefixtures("no_keyring")
def test_missing_credential_surfaces() -> None:
    with pytest.raises(MissingCredentialError):
        resolve_call("c", LlmSettings(default=ProviderSettings(provider=Provider.OPENAI, model="gpt-4o")))


def test_settings_are_loaded_from_the_config_file_when_not_passed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = save_settings(
        LlmSettings(default=ProviderSettings(provider=Provider.OLLAMA, model="llama3")), tmp_path / "llm.toml"
    )
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(path))

    assert resolve_call("c").model == "ollama_chat/llama3"
