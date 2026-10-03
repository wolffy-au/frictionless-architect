"""Settings file: TOML round-trip, location rules, missing-file behaviour."""

from pathlib import Path

import pytest
from llm_provider_config import (
    LlmSettings,
    Provider,
    ProviderSettings,
    default_config_path,
    load_settings,
    save_settings,
)


def test_missing_file_means_nothing_configured(tmp_path: Path) -> None:
    assert load_settings(tmp_path / "absent.toml") == LlmSettings()


def test_round_trip_preserves_default_overrides_and_params(tmp_path: Path) -> None:
    settings = LlmSettings(
        default=ProviderSettings(provider=Provider.ANTHROPIC, model="claude-x", params={"temperature": 0.2}),
        components={
            "pkg.step": ProviderSettings(
                provider=Provider.OLLAMA, model="llama3", api_base="http://box:11434", credential_ref="custom"
            )
        },
    )
    path = tmp_path / "nested" / "llm.toml"

    save_settings(settings, path)

    assert load_settings(path) == settings


def test_saved_file_contains_no_secret_material(tmp_path: Path) -> None:
    path = save_settings(
        LlmSettings(default=ProviderSettings(provider=Provider.OPENAI, model="gpt-4o", credential_ref="work")),
        tmp_path / "llm.toml",
    )

    text = path.read_text(encoding="utf-8")

    assert "work" in text
    assert "api_key" not in text


def test_default_path_honours_the_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(tmp_path / "x.toml"))

    assert default_config_path() == tmp_path / "x.toml"


def test_default_path_lives_under_the_user_config_dir_not_the_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER_CONFIG_PATH", raising=False)

    assert default_config_path() == Path.home() / ".config" / "frictionless-architect" / "llm.toml"


def test_save_and_load_default_to_the_env_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(tmp_path / "env.toml"))
    settings = LlmSettings(default=ProviderSettings(provider=Provider.GEMINI, model="gemini-x"))

    save_settings(settings)

    assert load_settings() == settings


def test_save_survives_a_filesystem_that_refuses_chmod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(self: Path, mode: int) -> None:
        raise PermissionError("chmod not permitted")

    monkeypatch.setattr(Path, "chmod", refuse)
    target = tmp_path / "llm.toml"

    save_settings(LlmSettings(), target)

    assert target.exists()
