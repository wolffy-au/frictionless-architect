"""Config path resolution: env override vs. the user-config-dir default."""

from __future__ import annotations

from pathlib import Path

import pytest
from pii_gateway.config import default_config_path, resolve_context


def test_default_path_honours_the_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PII_GATEWAY_CONFIG_PATH", str(tmp_path / "x.toml"))

    assert default_config_path() == tmp_path / "x.toml"


def test_default_path_lives_under_the_user_config_dir_not_the_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PII_GATEWAY_CONFIG_PATH", raising=False)

    assert default_config_path() == Path.home() / ".config" / "frictionless-architect" / "pii-gateway.toml"


def test_unrecognized_context_falls_back_to_the_global_default_not_conversational() -> None:
    # An unknown context must not inherit conversational-authoring's
    # flagged_for_review default (spec Edge Cases).
    config = resolve_context("some-unregistered-context", {})

    assert config.failure_mode.value == "redacted_and_proceeded"
