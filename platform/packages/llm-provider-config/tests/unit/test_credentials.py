"""Credential resolution: keychain first, labelled env fallback, Ollama keyless."""

import logging

import pytest
from conftest import InMemoryKeyring
from llm_provider_config import (
    MissingCredentialError,
    Provider,
    ProviderSettings,
    delete_api_key,
    get_api_key,
    set_api_key,
)

_OPENAI = ProviderSettings(provider=Provider.OPENAI, model="gpt-4o")


def test_keychain_entry_is_returned(fake_keyring: InMemoryKeyring) -> None:
    set_api_key("openai", "sk-keychain")

    assert get_api_key(_OPENAI) == "sk-keychain"


def test_credential_ref_selects_a_different_keychain_entry(fake_keyring: InMemoryKeyring) -> None:
    set_api_key("work", "sk-work")
    settings = ProviderSettings(provider=Provider.OPENAI, model="gpt-4o", credential_ref="work")

    assert get_api_key(settings) == "sk-work"


def test_keychain_wins_over_the_environment(fake_keyring: InMemoryKeyring, monkeypatch: pytest.MonkeyPatch) -> None:
    set_api_key("openai", "sk-keychain")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

    assert get_api_key(_OPENAI) == "sk-keychain"


def test_environment_fallback_is_used_and_warned_about_when_the_entry_is_absent(
    fake_keyring: InMemoryKeyring, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

    with caplog.at_level(logging.WARNING):
        key = get_api_key(_OPENAI)

    assert key == "sk-env"
    assert "OPENAI_API_KEY" in caplog.text
    assert "sk-env" not in caplog.text


@pytest.mark.usefixtures("no_keyring")
def test_environment_fallback_works_when_no_keychain_backend_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")

    assert get_api_key(ProviderSettings(provider=Provider.ANTHROPIC, model="claude-x")) == "sk-ant"


@pytest.mark.usefixtures("no_keyring")
def test_missing_everywhere_raises_with_both_remedies_named() -> None:
    with pytest.raises(MissingCredentialError, match=r"keyring entry 'openai'.*OPENAI_API_KEY"):
        get_api_key(_OPENAI)


def test_gemini_uses_its_own_environment_variable(
    fake_keyring: InMemoryKeyring, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")

    assert get_api_key(ProviderSettings(provider=Provider.GEMINI, model="gemini-x")) == "g-key"


def test_ollama_needs_no_key_and_never_touches_the_keychain() -> None:
    assert get_api_key(ProviderSettings(provider=Provider.OLLAMA, model="llama3")) is None


def test_delete_removes_the_keychain_entry(fake_keyring: InMemoryKeyring) -> None:
    set_api_key("openai", "sk-keychain")

    delete_api_key("openai")

    with pytest.raises(MissingCredentialError):
        get_api_key(_OPENAI)
