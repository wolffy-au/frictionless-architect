"""Opt-in live check of the AI conversion path against a local Ollama (GH #76, criterion 3).

Skipped unless ``RUN_OLLAMA_TESTS=1``: it is slow (model load) and its output is not
deterministic, so it asserts only that a real model returned non-empty Markdown mentioning
the control's title. Override the model with ``OLLAMA_TEST_MODEL`` (default ``gemma4:12b``)
and the endpoint with ``OLLAMA_API_BASE``.
"""

import os
from pathlib import Path

import litellm
import pytest
from controls_compliance_catalog import llm_client
from controls_compliance_catalog.playground.convert import convert_control_prose_to_markdown_candidate
from llm_provider_config import LlmSettings, Provider, ProviderSettings, save_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_OLLAMA_TESTS") != "1", reason="set RUN_OLLAMA_TESTS=1 to run"
)  # pragma: no cover


def test_real_ollama_converts_prose_to_non_empty_markdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:  # pragma: no cover
    config = save_settings(
        LlmSettings(
            default=ProviderSettings(
                provider=Provider.OLLAMA,
                model=os.environ.get("OLLAMA_TEST_MODEL", "gemma4:12b"),
                api_base=os.environ.get("OLLAMA_API_BASE"),
                params={"temperature": 0},
            )
        ),
        tmp_path / "llm.toml",
    )
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(config))
    monkeypatch.setattr(llm_client, "completion", litellm.completion)  # undo the autouse fake

    markdown = convert_control_prose_to_markdown_candidate(
        "AC-2 Account Management: The organization manages information system accounts."
    )

    assert "Account Management" in markdown
