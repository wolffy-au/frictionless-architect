"""Validate sample XML against the bundled ArchiMate exchange-format XSDs (ADR-0022).

The sample is parsed with `defusedxml` and checked for the ArchiMate namespace
(ADR-0032), then validated against the XSDs with `xmlschema` (which re-reads the
file, equally hardened, so it keeps the document's own prefix map). The hand-written
relationship/view reference checks run as well: they name the dangling
identifier, which the XSD's key/keyref errors do not.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator
from xml.etree import ElementTree as ET

from defusedxml.ElementTree import parse as _safe_parse
from xmlschema import XMLResource, XMLSchema
from xmlschema.exceptions import XMLSchemaException

from frictionless_architect.visualizer.namespaces import (
    ARCHIMATE_NS,
    XSI_NS,
    ArchimateNamespaceError,
    require_archimate_namespace,
)

MAX_XSD_ISSUES = 50
"""XSD errors reported per sample; a badly broken file must not flood the warnings."""


@lru_cache(maxsize=4)
def _load_schema(schema_path: Path) -> XMLSchema:
    """Build (once per path) the XSD, hardened and restricted to local files.

    `allow="local"` means the remote `xml.xsd` import in `archimate3_Model.xsd`
    resolves from xmlschema's bundled copy, never the network.
    """
    return XMLSchema(str(schema_path), defuse="always", allow="local")


def _qualified_type(xsi_type: str) -> str:
    """ArchiMate `xsi:type` values are unprefixed or `prefix:Name`; both mean the ArchiMate namespace."""
    return f"{{{ARCHIMATE_NS}}}{xsi_type.rpartition(':')[2]}"


def _gather_sample_metadata(root: ET.Element) -> tuple[set[str], set[str], set[str]]:
    element_ids: set[str] = set()
    relationship_ids: set[str] = set()
    xsi_types: set[str] = set()

    for tag, ids in (("element", element_ids), ("relationship", relationship_ids)):
        for node in root.findall(f".//{{{ARCHIMATE_NS}}}{tag}"):
            identifier = node.attrib.get("identifier")
            if identifier:
                ids.add(identifier)
            node_type = node.attrib.get(f"{{{XSI_NS}}}type")
            if node_type:
                xsi_types.add(node_type)

    return element_ids, relationship_ids, xsi_types


def _undeclared_types(xsi_types: set[str], schema: XMLSchema) -> list[str]:
    """Types the XSD does not declare. xmlschema raises (not reports) on these, so check first."""
    return sorted(t for t in xsi_types if _qualified_type(t) not in schema.maps.types)


def _validate_against_xsd(sample_path: Path, schema: XMLSchema) -> Iterator[str]:
    try:
        resource = XMLResource(str(sample_path), defuse="always", allow="local")
        for count, error in enumerate(schema.iter_errors(resource)):
            if count == MAX_XSD_ISSUES:
                yield f"XSD: further XSD issues suppressed after the first {MAX_XSD_ISSUES}"
                return
            yield f"XSD: {error.reason} (at {error.path})"
    except XMLSchemaException as exc:
        yield f"XSD validation aborted: {exc}"


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


def _validate_root(sample_path: Path, root: ET.Element, schema: XMLSchema) -> list[str]:
    element_ids, relationship_ids, xsi_types = _gather_sample_metadata(root)
    errors: list[str] = []
    unknown_types = _undeclared_types(xsi_types, schema)
    if unknown_types:
        errors.append(f"Types not defined in schema: {', '.join(unknown_types)}")
    else:
        errors.extend(_validate_against_xsd(sample_path, schema))
    errors.extend(_validate_relationship_connections(root, element_ids))
    errors.extend(_validate_view_refs(root, element_ids, relationship_ids))
    return errors


def validate_sample_against_schema(sample_path: Path, schema_path: Path) -> list[str]:
    """Return a list of validation issues (empty when the sample is valid).

    `schema_path` is the entry XSD; for a model with diagrams that is
    `archimate3_Diagram.xsd`, which includes the View and Model schemas.
    """
    if not sample_path.exists():
        return [f"Sample XML missing at {sample_path}"]
    if not schema_path.exists():
        return [f"Schema XSD missing at {schema_path}"]

    root = _safe_parse(sample_path).getroot()
    if root is None:
        return [f"Sample XML {sample_path} has no root element"]
    try:
        require_archimate_namespace(root, sample_path)
    except ArchimateNamespaceError as exc:
        return [str(exc)]
    try:
        schema = _load_schema(schema_path)
    except (XMLSchemaException, OSError) as exc:
        return [f"Schema XSD at {schema_path} could not be loaded: {exc}"]
    return _validate_root(sample_path, root, schema)
