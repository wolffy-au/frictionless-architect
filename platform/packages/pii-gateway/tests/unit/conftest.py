"""Isolates each test's config/audit files to a fresh tmp_path."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_GATEWAY_CONFIG_PATH", str(tmp_path / "pii-gateway.toml"))
    monkeypatch.setenv("PII_GATEWAY_AUDIT_PATH", str(tmp_path / "pii-gateway-audit.jsonl"))
