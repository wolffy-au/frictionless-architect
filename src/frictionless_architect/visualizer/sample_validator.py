"""Helpers to validate sample XML content against the provided ArchiMate schema."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

XSD_NS = "http://www.w3.org/2001/XMLSchema"
ARCHIMATE_NS = "http://www.opengroup.org/xsd/archimate/3.0/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def _iter_defined_types(schema_path: Path) -> set[str]:
    root = ET.parse(schema_path).getroot()
    defined: set[str] = set()
    defined.update(
        elem.attrib["name"]
        for elem in root.findall(f".//{{{XSD_NS}}}element")
        if "name" in elem.attrib
    )
    defined.update(
        elem.attrib["name"]
        for elem in root.findall(f".//{{{XSD_NS}}}complexType")
        if "name" in elem.attrib
    )
    return defined


def _gather_sample_metadata(root: ET.Element) -> tuple[set[str], set[str], set[str], set[str]]:
    element_ids: set[str] = set()
    relationship_ids: set[str] = set()
    element_types: set[str] = set()
    relationship_types: set[str] = set()

    for element in root.findall(f".//{{{ARCHIMATE_NS}}}element"):
        identifier = element.attrib.get("identifier")
        if identifier:
            element_ids.add(identifier)
        elem_type = element.attrib.get(f"{{{XSI_NS}}}type")
        if elem_type:
            element_types.add(elem_type)

    for relationship in root.findall(f".//{{{ARCHIMATE_NS}}}relationship"):
        identifier = relationship.attrib.get("identifier")
        if identifier:
            relationship_ids.add(identifier)
        rel_type = relationship.attrib.get(f"{{{XSI_NS}}}type")
        if rel_type:
            relationship_types.add(rel_type)

    return element_ids, relationship_ids, element_types, relationship_types


def _validate_relationship_connections(root: ET.Element, element_ids: set[str]) -> Iterable[str]:
    for relationship in root.findall(f".//{{{ARCHIMATE_NS}}}relationship"):
        identifier = relationship.attrib.get("identifier", "<unknown>")
        source = relationship.attrib.get("source")
        target = relationship.attrib.get("target")
        if source and source not in element_ids:
            yield f"Relationship {identifier} source {source} is missing"
        if target and target not in element_ids:
            yield f"Relationship {identifier} target {target} is missing"


def _validate_view_refs(root: ET.Element, element_ids: set[str], relationship_ids: set[str]) -> Iterable[str]:
    for node in root.findall(f".//{{{ARCHIMATE_NS}}}node"):
        element_ref = node.attrib.get("elementRef")
        if element_ref and element_ref not in element_ids:
            yield f"View node references missing element {element_ref}"
    for connection in root.findall(f".//{{{ARCHIMATE_NS}}}connection"):
        rel_ref = connection.attrib.get("relationshipRef")
        if rel_ref and rel_ref not in relationship_ids:
            yield f"View connection references missing relationship {rel_ref}"


def validate_sample_against_schema(sample_path: Path, schema_path: Path) -> list[str]:
    """Return a list of validation issues (empty when consistent)."""
    if not sample_path.exists():
        return [f"Sample XML missing at {sample_path}"]
    if not schema_path.exists():
        return [f"Schema XSD missing at {schema_path}"]

    tree = ET.parse(sample_path)
    root = tree.getroot()
    element_ids, relationship_ids, element_types, relationship_types = _gather_sample_metadata(root)
    defined_types = _iter_defined_types(schema_path)
    errors: list[str] = []

    unknown_types = sorted((element_types | relationship_types) - defined_types)
    if unknown_types:
        errors.append(f"Types not defined in schema: {', '.join(unknown_types)}")

    errors.extend(_validate_relationship_connections(root, element_ids))
    errors.extend(_validate_view_refs(root, element_ids, relationship_ids))
    return errors
