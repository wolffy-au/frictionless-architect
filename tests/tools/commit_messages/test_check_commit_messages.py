"""Unit tests for scripts/check_commit_messages.py."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_commit_messages.py"
spec = importlib.util.spec_from_file_location("check_commit_messages", SCRIPT)
assert spec
assert spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SCOPES = {"specs", "speckit", "model", "llm-provider-config"}


@pytest.mark.parametrize(
    "message",
    [
        "docs(specs): trim plan",
        "feat(model)!: reframe plateaus\n\nBREAKING CHANGE: ids renamed",
        "chore: bump lock",
        "Merge branch 'develop' into feature/x",
        "revert(model): undo reframe\n\nRefs: abc1234",
    ],
)
def test_conforming_messages_pass(message: str) -> None:
    assert mod.check_message(message, SCOPES) == []


@pytest.mark.parametrize(
    ("message", "fragment"),
    [
        ("docs(spec): trim plan", "unknown scope 'spec'"),
        ("wip(model): trim plan", "unknown type"),
        ("docs(specs): " + "x" * 70, "characters"),
        ("docs(specs): Trim plan", "lower-case"),
        ("docs(specs): trim plan.", "period"),
        ("docs(model)!: rename", "BREAKING CHANGE"),
        ("revert(model): undo", "Refs"),
        ("not a conventional commit", "subject is not"),
    ],
)
def test_breaking_messages_fail(message: str, fragment: str) -> None:
    assert any(fragment in p for p in mod.check_message(message, SCOPES))


def test_scopes_come_from_the_standard_and_packages() -> None:
    scopes = mod.area_scopes() | mod.package_scopes()
    assert {"specs", "speckit", "model", "controls-compliance-catalog"} <= scopes
    assert "spec" not in scopes


def test_message_file_mode(tmp_path: Path) -> None:
    good, bad = tmp_path / "good", tmp_path / "bad"
    good.write_text("docs(specs): trim plan\n")
    bad.write_text("docs(spec): trim plan\n")
    assert mod.main(["--message-file", str(good)]) == 0
    assert mod.main(["--message-file", str(bad)]) == 1


def test_body_wrap_flags_long_prose_lines() -> None:
    message = "docs(specs): trim plan\n\n" + "word " * 15 + "\n"
    assert any("columns" in p for p in mod.body_wrap_problems(message))


def test_body_wrap_exempts_trailers_urls_and_code() -> None:
    message = (
        "docs(specs): trim plan\n\n"
        "https://example.com/" + "a" * 80 + "\n"
        "    " + "indented " * 12 + "\n"
        "Co-Authored-By: " + "N" * 70 + " <noreply@example.com>\n"
    )
    assert mod.body_wrap_problems(message) == []


def test_body_wrap_fails_message_file_but_only_warns_for_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    long_body = "docs(specs): trim plan\n\n" + "word " * 15 + "\n"
    path = tmp_path / "msg"
    path.write_text(long_body)
    assert mod.main(["--message-file", str(path)]) == 1
    capsys.readouterr()
    monkeypatch.setattr(mod, "commits_in_range", lambda _range: [("abc1234", long_body.strip())])
    assert mod.main(["--range", "x..y"]) == 0
    assert "warning: abc1234" in capsys.readouterr().err
