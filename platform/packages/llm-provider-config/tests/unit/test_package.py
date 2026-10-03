"""Smoke test: the package installs into the platform/ workspace and imports."""

import llm_provider_config


def test_package_imports_from_workspace() -> None:
    assert llm_provider_config.__all__ == []
