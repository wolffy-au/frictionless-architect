"""Unit tests for the shared ArchiMate namespace constants and root check."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast

import pytest
from defusedxml.ElementTree import iterparse

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


SCHEMA_FILES = sorted(Path("sample-data/schema").glob("archimate3_*.xsd"))


def _schema_namespaces(schema_path: Path) -> tuple[str | None, dict[str, str]]:
    declared: dict[str, str] = {}
    for event, item in iterparse(schema_path, events=("start-ns", "start")):
        if event == "start-ns":
            # The stubs type every item as an Element; start-ns yields (prefix, uri).
            prefix, uri = cast("tuple[str, str]", item)
            declared[prefix] = uri
        else:
            return item.attrib.get("targetNamespace"), declared
    return None, declared


def test_bundled_schemas_are_present() -> None:
    assert [path.name for path in SCHEMA_FILES] == [
        "archimate3_Diagram.xsd",
        "archimate3_Model.xsd",
        "archimate3_View.xsd",
    ]


@pytest.mark.parametrize("schema_path", SCHEMA_FILES, ids=lambda path: path.name)
def test_bundled_schema_namespaces_match_archimate_ns(schema_path: Path) -> None:
    # ADR-0032: the bundled XSDs stay identical to The Open Group's files,
    # whose target namespace is the 3.0 URI even for schema version 3.1.
    target_namespace, declared = _schema_namespaces(schema_path)
    assert target_namespace == ARCHIMATE_NS
    assert declared.get("") == ARCHIMATE_NS
    assert declared.get("archimate") == ARCHIMATE_NS
