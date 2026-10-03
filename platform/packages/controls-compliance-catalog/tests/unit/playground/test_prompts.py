import pathlib

import pytest
from controls_compliance_catalog.playground import prompts
from controls_compliance_catalog.playground.convert import (
    PlaygroundConversionError,
    convert_control_prose_to_markdown_candidate,
)


def test_shipped_prose_prompt_loads() -> None:
    assert "Trestle Markdown" in prompts.load_system_prompt("prose_to_trestle_markdown")


def test_prompt_edits_apply_without_restart(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "prompts.yaml"
    monkeypatch.setattr(prompts, "PROMPTS_PATH", path)
    path.write_text("p:\n  system: first\n")
    assert prompts.load_system_prompt("p") == "first"
    path.write_text("p:\n  system: second\n")
    assert prompts.load_system_prompt("p") == "second"


@pytest.mark.parametrize("content", ["", "p: 1\n", "p:\n  system: '  '\n", "other:\n  system: x\n", "a: [unclosed\n"])
def test_bad_prompt_file_raises(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, content: str) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text(content)
    monkeypatch.setattr(prompts, "PROMPTS_PATH", path)
    with pytest.raises(prompts.PromptConfigError):
        prompts.load_system_prompt("p")


def test_missing_prompt_file_raises(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts, "PROMPTS_PATH", tmp_path / "nope.yaml")
    with pytest.raises(prompts.PromptConfigError):
        prompts.load_system_prompt("p")


def test_broken_prompt_file_surfaces_as_conversion_error(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompts, "PROMPTS_PATH", tmp_path / "nope.yaml")
    with pytest.raises(PlaygroundConversionError, match="Cannot read prompts"):
        convert_control_prose_to_markdown_candidate("AC-2 Account Management: text.")
