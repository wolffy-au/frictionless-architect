"""Every `scrub()` call records exactly one metadata-only audit entry (FR-011)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pii_gateway import scrub
from pii_gateway.audit import default_audit_path


def _audit_lines() -> list[dict[str, object]]:
    path = Path(os.environ["PII_GATEWAY_AUDIT_PATH"])
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_records_one_entry_per_call() -> None:
    scrub("Contact Jane Doe at jane@example.com", context="spec-generator")

    entries = _audit_lines()
    assert len(entries) == 1
    categories = entries[0]["categories"]
    assert entries[0]["context"] == "spec-generator"
    assert entries[0]["action"] == "redacted_and_proceeded"
    assert isinstance(categories, list)
    assert "PERSON" in categories or "EMAIL_ADDRESS" in categories


def test_entry_never_contains_matched_text_or_surrounding_content() -> None:
    scrub("Contact Jane Doe at jane@example.com", context="spec-generator")

    raw = Path(os.environ["PII_GATEWAY_AUDIT_PATH"]).read_text(encoding="utf-8")
    assert "Jane Doe" not in raw
    assert "jane@example.com" not in raw
    assert "Contact" not in raw


def test_passthrough_call_still_records_an_entry_with_no_categories() -> None:
    scrub("Ordinary prose with no PII.", context="spec-generator")

    entries = _audit_lines()
    assert len(entries) == 1
    assert entries[0]["categories"] == []
    assert entries[0]["action"] == "passed_through_unchanged"


def test_default_audit_path_lives_under_the_user_state_dir_not_the_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PII_GATEWAY_AUDIT_PATH", raising=False)

    assert (
        default_audit_path() == Path.home() / ".local" / "state" / "frictionless-architect" / "pii-gateway-audit.jsonl"
    )
