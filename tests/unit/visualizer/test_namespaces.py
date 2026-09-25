"""Unit tests for the shared ArchiMate namespace constants and root check."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from frictionless_architect.visualizer.namespaces import (
    ARCHIMATE_NS,
    ArchimateNamespaceError,
    require_archimate_namespace,
)

ARCHIMATE_31_NS = "http://www.opengroup.org/xsd/archimate/3.1/"


def test_accepts_archimate_30_root() -> None:
    root = ET.fromstring(f'<model xmlns="{ARCHIMATE_NS}"/>')
    require_archimate_namespace(root, "sample.xml")


def test_rejects_other_namespace_with_actionable_message() -> None:
    root = ET.fromstring(f'<model xmlns="{ARCHIMATE_31_NS}"/>')
    with pytest.raises(ArchimateNamespaceError) as excinfo:
        require_archimate_namespace(root, "sample.xml")
    message = str(excinfo.value)
    assert "sample.xml" in message
    assert ARCHIMATE_31_NS in message
    assert ARCHIMATE_NS in message


def test_rejects_unnamespaced_root() -> None:
    root = ET.fromstring("<model/>")
    with pytest.raises(ArchimateNamespaceError, match="no namespace"):
        require_archimate_namespace(root, "sample.xml")


def test_rejects_wrong_root_element() -> None:
    root = ET.fromstring(f'<elements xmlns="{ARCHIMATE_NS}"/>')
    with pytest.raises(ArchimateNamespaceError, match="<model>"):
        require_archimate_namespace(root, "sample.xml")
