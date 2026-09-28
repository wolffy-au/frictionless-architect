"""Smoke test: the package installs into the platform/ workspace and imports."""

import controls_compliance_catalog


def test_package_imports_from_workspace() -> None:
    assert controls_compliance_catalog.__all__ == []
