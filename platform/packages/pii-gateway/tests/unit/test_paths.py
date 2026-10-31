"""`resolve_override` confines env-var-sourced paths (Snyk Code CWE-22 fix)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pii_gateway._paths import resolve_override


def test_path_under_home_is_accepted() -> None:
    target = Path.home() / ".config" / "frictionless-architect" / "x.toml"

    assert resolve_override(str(target), env_var="X") == target


def test_path_under_system_temp_is_accepted(tmp_path: Path) -> None:
    target = tmp_path / "x.toml"

    assert resolve_override(str(target), env_var="X") == target


def test_traversal_segments_that_escape_to_a_system_path_are_rejected() -> None:
    escaping = str(Path.home() / ".config" / ".." / ".." / ".." / "etc" / "passwd")

    with pytest.raises(ValueError, match="outside both the user's home directory"):
        resolve_override(escaping, env_var="PII_GATEWAY_CONFIG_PATH")


def test_a_bare_system_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="PII_GATEWAY_AUDIT_PATH"):
        resolve_override("/etc/passwd", env_var="PII_GATEWAY_AUDIT_PATH")
