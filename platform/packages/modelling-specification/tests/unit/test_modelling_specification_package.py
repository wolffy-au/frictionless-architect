"""Smoke test: the package installs into the platform/ workspace and imports."""

import modelling_specification


def test_package_imports_from_workspace() -> None:
    assert modelling_specification.__all__ == []
