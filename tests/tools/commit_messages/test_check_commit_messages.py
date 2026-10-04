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
