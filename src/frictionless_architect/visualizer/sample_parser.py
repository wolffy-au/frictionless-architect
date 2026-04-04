"""Lightweight parser that normalizes the enriched sample model XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARCHIMATE_NS = "http://www.opengroup.org/xsd/archimate/3.0/"  # Defined namespace per ArchiMate 3 spec (must stay http)
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"  # Standard XML Schema Instance namespace uses http and is the published URI


@dataclass
class SampleParseResult:
    model: dict[str, Any]
    elements: dict[str, dict[str, Any]]
    relationships: dict[str, dict[str, Any]]
    views: list[dict[str, Any]]
    file_path: Path

    @classmethod
    def empty(cls, sample_file: Path) -> "SampleParseResult":
        return cls(model={}, elements={}, relationships={}, views=[], file_path=sample_file)


class SampleParser:
    def __init__(self, sample_file: Path) -> None:
        self.sample_file = sample_file

    def parse(self) -> SampleParseResult:
        tree = ET.parse(self.sample_file)
        root = tree.getroot()
        elements = self._parse_elements(root)
        relationships = self._parse_relationships(root)
        views = self._parse_views(root, elements)
        return SampleParseResult(
            model=self._extract_model(root),
            elements=elements,
            relationships=relationships,
            views=views,
            file_path=self.sample_file,
        )

    def _parse_elements(self, root: ET.Element) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for element in root.findall(f".//{{{ARCHIMATE_NS}}}elements/{{{ARCHIMATE_NS}}}element"):
            identifier = element.attrib.get("identifier")
            if not identifier:
                continue
            elem_type = element.attrib.get(f"{{{XSI_NS}}}type") or "Element"
            result[identifier] = {
                "identifier": identifier,
                "type": elem_type,
                "name": self._first_name(element),
            }
        return result

    def _parse_relationships(self, root: ET.Element) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for relationship in root.findall(f".//{{{ARCHIMATE_NS}}}relationships/{{{ARCHIMATE_NS}}}relationship"):
            identifier = relationship.attrib.get("identifier")
            if not identifier:
                continue
            rel_type = relationship.attrib.get(f"{{{XSI_NS}}}type") or "Relationship"
            result[identifier] = {
                "identifier": identifier,
                "type": rel_type,
                "source": relationship.attrib.get("source"),
                "target": relationship.attrib.get("target"),
                "properties": {k: v for k, v in relationship.attrib.items() if k not in {"identifier", "source", "target", f"{{{XSI_NS}}}type"}},
            }
        return result

    def _parse_views(self, root: ET.Element, elements: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        views_elem = root.find(f"./{{{ARCHIMATE_NS}}}views/{{{ARCHIMATE_NS}}}diagrams")
        if views_elem is None:
            return []
        views: list[dict[str, Any]] = []
        for view in views_elem.findall(f"{{{ARCHIMATE_NS}}}view"):
            identifier = view.attrib.get("identifier")
            if not identifier:
                continue
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
        return name_elem.text.strip() if name_elem is not None and name_elem.text else None

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
