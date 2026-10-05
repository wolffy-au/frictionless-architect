"""Lightweight parser that normalizes the enriched sample model XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import parse as _safe_parse

from frictionless_architect.visualizer.namespaces import ARCHIMATE_NS, XSI_NS, require_archimate_namespace

_DUPLICATE_LAST_WINS = "Duplicate {kind} identifier {identifier} in the sample; the last definition is used"


@dataclass
class SampleParseResult:
    """Normalised content of a parsed sample model file.

    Attributes:
        model: Model-level metadata (identifier, name, ...).
        elements: Elements keyed by identifier.
        relationships: Relationships keyed by identifier.
        views: View definitions with their nodes and connections.
        file_path: The XML file the data came from.
        warnings: Problems found while parsing, such as repeated identifiers.
    """

    model: dict[str, Any]
    elements: dict[str, dict[str, Any]]
    relationships: dict[str, dict[str, Any]]
    views: list[dict[str, Any]]
    file_path: Path
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def empty(cls, sample_file: Path) -> "SampleParseResult":
        """Build a result with no content, for when the sample cannot be used.

        Args:
            sample_file: The file that was attempted.

        Returns:
            An empty result pointing at ``sample_file``.
        """
        return cls(model={}, elements={}, relationships={}, views=[], file_path=sample_file)


class SampleParser:
    """Parses an ArchiMate 3 exchange-format file into a ``SampleParseResult``."""

    def __init__(self, sample_file: Path) -> None:
        """Create a parser.

        Args:
            sample_file: Path of the ArchiMate exchange XML to parse.
        """
        self.sample_file = sample_file

    def parse(self) -> SampleParseResult:
        """Parse the sample file.

        Repeated element or relationship identifiers keep the last definition; repeated
        view identifiers are kept as-is. Each repeat adds an entry to ``warnings``.

        Returns:
            The normalised model, elements, relationships and views, plus ``warnings``.

        Raises:
            FileNotFoundError: If the file does not exist.
            xml.etree.ElementTree.ParseError: If the XML is malformed.
            ValueError: If the document has no root element.
            ArchimateNamespaceError: If the root is not in the ArchiMate 3 namespace.
        """
        tree = _safe_parse(self.sample_file)
        root = tree.getroot()
        if root is None:
            raise ValueError(f"Sample XML {self.sample_file} has no root element")
        require_archimate_namespace(root, self.sample_file)
        warnings: list[str] = []
        elements = self._parse_elements(root, warnings)
        relationships = self._parse_relationships(root, warnings)
        views = self._parse_views(root, elements, warnings)
        return SampleParseResult(
            model=self._extract_model(root),
            elements=elements,
            relationships=relationships,
            views=views,
            file_path=self.sample_file,
            warnings=warnings,
        )

    def _parse_elements(self, root: ET.Element, warnings: list[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for element in root.findall(f".//{{{ARCHIMATE_NS}}}elements/{{{ARCHIMATE_NS}}}element"):
            identifier = element.attrib.get("identifier")
            if not identifier:
                continue
            if identifier in result:
                warnings.append(_DUPLICATE_LAST_WINS.format(kind="element", identifier=identifier))
            elem_type = element.attrib.get(f"{{{XSI_NS}}}type") or "Element"
            result[identifier] = {
                "identifier": identifier,
                "type": elem_type,
                "name": self._first_name(element),
            }
        return result

    def _parse_relationships(self, root: ET.Element, warnings: list[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for relationship in root.findall(f".//{{{ARCHIMATE_NS}}}relationships/{{{ARCHIMATE_NS}}}relationship"):
            identifier = relationship.attrib.get("identifier")
            if not identifier:
                continue
            if identifier in result:
                warnings.append(_DUPLICATE_LAST_WINS.format(kind="relationship", identifier=identifier))
            rel_type = relationship.attrib.get(f"{{{XSI_NS}}}type") or "Relationship"
            result[identifier] = {
                "identifier": identifier,
                "type": rel_type,
                "source": relationship.attrib.get("source"),
                "target": relationship.attrib.get("target"),
                "properties": {
                    k: v
                    for k, v in relationship.attrib.items()
                    if k not in {"identifier", "source", "target", f"{{{XSI_NS}}}type"}
                },
            }
        return result

    def _parse_views(
        self, root: ET.Element, elements: dict[str, dict[str, Any]], warnings: list[str]
    ) -> list[dict[str, Any]]:
        views_elem = root.find(f"./{{{ARCHIMATE_NS}}}views/{{{ARCHIMATE_NS}}}diagrams")
        if views_elem is None:
            return []
        views: list[dict[str, Any]] = []
        seen: set[str] = set()
        for view in views_elem.findall(f"{{{ARCHIMATE_NS}}}view"):
            identifier = view.attrib.get("identifier")
            if not identifier:
                continue
            if identifier in seen:
                warnings.append(f"Duplicate view identifier {identifier} in the sample")
            seen.add(identifier)
            view_dict: dict[str, Any] = {
                "identifier": identifier,
                "name": self._first_name(view),
                "type": view.attrib.get(f"{{{XSI_NS}}}type", "Diagram"),
                "nodes": [],
                "connections": [],
            }
            for node in view.findall(f"{{{ARCHIMATE_NS}}}node"):
                bounds = self._extract_bounds(node)
                label = self._lookup_label(node.attrib.get("elementRef"), elements)
                view_dict["nodes"].append(
                    {
                        "identifier": node.attrib.get("identifier"),
                        "elementRef": node.attrib.get("elementRef"),
                        "bounds": bounds,
                        "label": label,
                    }
                )
            for connection in view.findall(f"{{{ARCHIMATE_NS}}}connection"):
                connection_dict = {
                    "identifier": connection.attrib.get("identifier"),
                    "relationshipRef": connection.attrib.get("relationshipRef"),
                    "source": connection.attrib.get("source"),
                    "target": connection.attrib.get("target"),
                }
                view_dict["connections"].append(connection_dict)
            views.append(view_dict)
        return views

    def _extract_model(self, root: ET.Element) -> dict[str, Any]:
        return {
            "identifier": root.attrib.get("identifier"),
            "name": self._first_name(root),
        }

    def _first_name(self, element: ET.Element) -> str | None:
        name_elem = element.find(f"{{{ARCHIMATE_NS}}}name")
        if name_elem is None:
            return None
        return (name_elem.text or "").strip() or None

    def _lookup_label(self, element_ref: str | None, elements: dict[str, dict[str, Any]]) -> str | None:
        if element_ref and element_ref in elements:
            return elements[element_ref].get("name")
        return None

    def _extract_bounds(self, node: ET.Element) -> dict[str, int]:
        bounds: dict[str, int] = {}
        for key in ("x", "y", "w", "h"):
            raw = node.attrib.get(key)
            if raw is not None:
                try:
                    bounds[key] = int(float(raw))
                except ValueError:
                    continue
        return bounds
