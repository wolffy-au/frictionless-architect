"""Run every test against a fake LLM and a fixed provider config -- never a real provider.

Mirrors `controls-compliance-catalog`'s own `tests/conftest.py` fixture (same
pattern, R4): this `conftest.py` sits at the `tests/` root so the autouse fixture
reaches `tests/unit/` and `tests/api/` alike.
"""

from __future__ import annotations

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
    monkeypatch.setattr("modelling_specification.authoring.delta.completion", fake)
    return fake
