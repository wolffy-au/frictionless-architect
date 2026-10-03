"""Unit tests for the LLM client seam (spec 001-oscal-ai-conversion R2), over a fake litellm."""

from pathlib import Path

import pytest
from controls_compliance_catalog.llm_client import COMPONENT_ID, LlmConversionError, convert_chunk
from llm_provider_config import LlmSettings, Provider, ProviderSettings, save_settings
from support.fake_llm import FakeCompletion


def test_convert_chunk_sends_system_and_prose_and_returns_the_model_markdown(
    configured_fake_llm: FakeCompletion,
) -> None:
    result = convert_chunk("AC-2 Account Management: manages accounts.", system="convert to markdown")

    assert "## Control Statement" in result
    sent = configured_fake_llm.calls[0]
    assert sent["messages"] == [
        {"role": "system", "content": "convert to markdown"},
        {"role": "user", "content": "AC-2 Account Management: manages accounts."},
    ]


def test_convert_chunk_calls_the_configured_provider_and_model(configured_fake_llm: FakeCompletion) -> None:
    convert_chunk("x: y", system="s")

    sent = configured_fake_llm.calls[0]
    assert sent["model"] == "ollama_chat/test-model"
    assert sent["api_base"] == "http://localhost:11434"


def test_component_override_selects_a_different_model(
    configured_fake_llm: FakeCompletion, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = save_settings(
        LlmSettings(
            default=ProviderSettings(provider=Provider.OLLAMA, model="test-model"),
            components={COMPONENT_ID: ProviderSettings(provider=Provider.OLLAMA, model="override-model")},
        ),
        tmp_path / "override.toml",
    )
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(config))

    convert_chunk("x: y", system="s")

    assert configured_fake_llm.calls[0]["model"] == "ollama_chat/override-model"


def test_surrounding_markdown_fence_is_stripped(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = "```markdown\n# ac-2\n\nbody\n```"

    assert convert_chunk("x: y", system="s") == "# ac-2\n\nbody\n"


def test_unfenced_output_is_kept_with_a_trailing_newline(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.content = "  # ac-2\n\nbody  "

    assert convert_chunk("x: y", system="s") == "# ac-2\n\nbody\n"


def test_convert_chunk_rejects_empty_prompt(configured_fake_llm: FakeCompletion) -> None:
    with pytest.raises(LlmConversionError, match="Cannot convert empty prose"):
        convert_chunk("   ", system="convert to markdown")

    assert configured_fake_llm.calls == []


def test_unconfigured_provider_is_a_clear_conversion_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(tmp_path / "absent.toml"))

    with pytest.raises(LlmConversionError, match="No LLM provider is configured"):
        convert_chunk("x: y", system="s")


def test_missing_credential_is_a_clear_conversion_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_keychain: None
) -> None:
    config = save_settings(
        LlmSettings(default=ProviderSettings(provider=Provider.OPENAI, model="gpt-4o")), tmp_path / "o.toml"
    )
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(config))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LlmConversionError, match="OPENAI_API_KEY"):
        convert_chunk("x: y", system="s")


def test_provider_failure_is_wrapped_with_the_model_name(configured_fake_llm: FakeCompletion) -> None:
    configured_fake_llm.error = ConnectionError("connection refused")

    with pytest.raises(LlmConversionError, match=r"ollama_chat/test-model.*connection refused"):
        convert_chunk("x: y", system="s")


@pytest.mark.parametrize("content", ["", "   \n", None])
def test_empty_model_response_is_an_error(configured_fake_llm: FakeCompletion, content: str | None) -> None:
    configured_fake_llm.content = content or ""

    with pytest.raises(LlmConversionError, match="empty response"):
        convert_chunk("x: y", system="s")
