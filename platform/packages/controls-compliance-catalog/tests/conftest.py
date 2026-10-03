"""Run every test against a fake LLM and a fixed provider config -- never a real provider."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from llm_provider_config import LlmSettings, Provider, ProviderSettings, save_settings
from support.fake_llm import FakeCompletion


@pytest.fixture(autouse=True)
def configured_fake_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeCompletion:
    config = save_settings(
        LlmSettings(default=ProviderSettings(provider=Provider.OLLAMA, model="test-model")),
        tmp_path / "llm.toml",
    )
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(config))
    fake = FakeCompletion()
    monkeypatch.setattr("controls_compliance_catalog.llm_client.completion", fake)
    return fake


@pytest.fixture
def no_keychain() -> Iterator[None]:
    import keyring
    from keyring.backends.fail import Keyring as FailKeyring

    previous = keyring.get_keyring()
    keyring.set_keyring(FailKeyring())  # type: ignore[no-untyped-call]
    yield
    keyring.set_keyring(previous)
