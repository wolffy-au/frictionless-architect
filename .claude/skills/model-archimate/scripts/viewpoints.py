#!/usr/bin/env python3
"""Standard ArchiMate viewpoints — lookup + view conformance checking.

The authority is ``../reference/archi-viewpoints.xml`` — a verbatim copy of
Archi's viewpoint definitions (see ``../reference/README.md``). This module
parses it the way Archi's ``ViewpointManager`` / ``Viewpoint`` do:

* ``<concept>`` entries are element classes, relationship classes, or
  collection tokens (``$BusinessElements$`` …) expanded via ``COLLECTIONS``.
* A viewpoint has an element allow-set and a relationship allow-set; **an
  empty set means that half is unrestricted**. Every current viewpoint has an
  empty relationship set, so relationships are effectively never filtered.
* ``Junction`` and ``Grouping`` are always allowed.

``../reference/viewpoints-guidance.yaml`` adds advisory purpose / abstraction
/ concerns / stakeholders — annotation only, no effect on conformance.

CLI::

    python viewpoints.py list
    python viewpoints.py show value_stream
    python viewpoints.py check MODEL[.xml|.archimate] --view "Name" --viewpoint value_stream

Exit 0 = conformant / info printed, 1 = non-conformant, 2 = bad input.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "reference"
ARCHI_XML = REFERENCE_DIR / "archi-viewpoints.xml"
GUIDANCE_YAML = REFERENCE_DIR / "viewpoints-guidance.yaml"

# Our own escape-hatch slug for a deliberate cross-layer view. Not an Archi
# viewpoint; never conformance-checked.
UNRESTRICTED = "custom"

# Always allowed in every viewpoint (Archi: Viewpoint.defaultList).
ALWAYS_ALLOWED_ELEMENTS = {"Junction", "Grouping"}

# Collection-token expansions, transcribed verbatim from
# com.archimatetool.model/src/com/archimatetool/model/util/ArchimateModelUtils.java
# (getStrategyClasses(), getBusinessClasses(), … and the relationship
# supertypes in archimate.ecore). Keep in sync when re-syncing the XML.
COLLECTIONS: dict[str, list[str]] = {
    "$StrategyElements$": ["Resource", "Capability", "ValueStream", "CourseOfAction"],
    "$BusinessElements$": [
        "BusinessActor",
        "BusinessRole",
        "BusinessCollaboration",
        "BusinessInterface",
        "BusinessProcess",
        "BusinessFunction",
        "BusinessInteraction",
        "BusinessEvent",
        "BusinessService",
        "BusinessObject",
        "Contract",
        "Representation",
        "Product",
    ],
    "$ApplicationElements$": [
        "ApplicationComponent",
        "ApplicationCollaboration",
        "ApplicationInterface",
        "ApplicationFunction",
        "ApplicationInteraction",
        "ApplicationProcess",
        "ApplicationEvent",
        "ApplicationService",
        "DataObject",
    ],
    "$TechnologyElements$": [
        "Node",
        "Device",
        "SystemSoftware",
        "TechnologyCollaboration",
        "TechnologyInterface",
        "Path",
        "CommunicationNetwork",
        "TechnologyFunction",
        "TechnologyProcess",
        "TechnologyInteraction",
        "TechnologyEvent",
        "TechnologyService",
        "Artifact",
    ],
    "$PhysicalElements$": ["Equipment", "Facility", "DistributionNetwork", "Material"],
    "$MotivationElements$": [
        "Stakeholder",
        "Driver",
        "Assessment",
        "Goal",
        "Outcome",
        "Principle",
        "Requirement",
        "Constraint",
        "Meaning",
        "Value",
    ],
    "$ImplementationMigrationElements$": [
        "WorkPackage",
        "Deliverable",
        "ImplementationEvent",
        "Plateau",
        "Gap",
    ],
    # Relationship collections — defined by Archi but currently unused by any
    # viewpoint. Kept so a re-sync that starts using them still resolves.
    "$StructuralRelationships$": ["Composition", "Aggregation", "Assignment", "Realization"],
    "$DependencyRelationships$": ["Serving", "Access", "Influence", "Association"],
    "$DynamicRelationships$": ["Triggering", "Flow"],
    "$OtherRelationships$": ["Specialization"],
}

_RELATIONSHIP_NAMES = {
    "Composition",
    "Aggregation",
    "Assignment",
    "Realization",
    "Serving",
    "Access",
    "Influence",
    "Triggering",
    "Flow",
    "Specialization",
    "Association",
}


def _expand(concept: str) -> list[str]:
    if concept in COLLECTIONS:
        return COLLECTIONS[concept]
    if concept.startswith("$") and concept.endswith("$"):
        raise ValueError(f"unknown collection token {concept!r} in archi-viewpoints.xml")
    return [concept]


@lru_cache(maxsize=1)
def _load_guidance() -> dict[str, dict[str, Any]]:
    if not GUIDANCE_YAML.exists():
        return {}
    import yaml  # local import: pyyaml is a dev dependency

    data = yaml.safe_load(GUIDANCE_YAML.read_text()) or {}
    return data.get("guidance", {})


@lru_cache(maxsize=1)
def load_viewpoints(xml_path: str | None = None) -> dict[str, dict[str, Any]]:
    """Return {slug: viewpoint-dict} parsed from archi-viewpoints.xml.

    Each dict has: slug, name, elements (set), relationships (set),
    elements_unrestricted (bool), relationships_unrestricted (bool), plus any
    keys from the guidance overlay.
    """
    root = ET.parse(Path(xml_path) if xml_path else ARCHI_XML).getroot()
    guidance = _load_guidance()
    out: dict[str, dict[str, Any]] = {}

    for vp in root.findall("viewpoint"):
        slug = vp.get("id")
        if not slug:
            continue
        name_el = vp.find("name")
        name = (name_el.text or "").strip() if name_el is not None else slug

        elements: set[str] = set()
        relationships: set[str] = set()
        for c in vp.findall("concept"):
            for resolved in _expand((c.text or "").strip()):
                (relationships if resolved in _RELATIONSHIP_NAMES else elements).add(resolved)

        entry: dict[str, Any] = {
            "slug": slug,
            "name": name,
            "elements": elements,
            "relationships": relationships,
            "elements_unrestricted": not elements,
            "relationships_unrestricted": not relationships,
        }
        entry.update(guidance.get(slug, {}))
        out[slug] = entry

    return out


def get_viewpoint(slug: str, xml_path: str | None = None) -> dict[str, Any] | None:
    return load_viewpoints(xml_path).get(slug)


def known_slugs(xml_path: str | None = None) -> list[str]:
    return sorted(load_viewpoints(xml_path))


def check_conformance(
    vp: dict[str, Any],
    element_types: Iterable[str],
    relationship_types: Iterable[str],
) -> list[str]:
    """Return a list of human-readable violations; empty == conformant.

    Mirrors Archi's ``Viewpoint.isAllowedConcept``: an empty allow-set means
    that half is unrestricted; Junction and Grouping are always allowed.
    """
    findings: list[str] = []
    slug = vp.get("slug", "?")

    if not vp.get("elements_unrestricted", not vp["elements"]):
        allow = set(vp["elements"]) | ALWAYS_ALLOWED_ELEMENTS
        for t in sorted(set(element_types)):
            if t not in allow:
                findings.append(f"element type {t!r} is not part of the {slug!r} viewpoint")

    if not vp.get("relationships_unrestricted", not vp["relationships"]):
        allow = set(vp["relationships"])
        for t in sorted(set(relationship_types)):
            if t not in allow:
                findings.append(f"relationship type {t!r} is not part of the {slug!r} viewpoint")

    return findings


# ─── CLI ────────────────────────────────────────────────────────────────────


def _fmt_set(s: set[str], unrestricted: bool) -> str:
    return "(unrestricted)" if unrestricted else ", ".join(sorted(s))


def _cmd_list() -> int:
    for slug in known_slugs():
        print(f"{slug:28}  {get_viewpoint(slug)['name']}")
    return 0


def _cmd_show(slug: str) -> int:
    vp = get_viewpoint(slug)
    if vp is None:
        sys.stderr.write(f"unknown viewpoint {slug!r}; known: {', '.join(known_slugs())}\n")
        return 2
    print(f"slug          : {vp['slug']}")
    print(f"name          : {vp['name']}")
    for k in ("purpose", "abstraction", "concerns", "stakeholders", "adm_phase", "since"):
        if k in vp:
            print(f"{k:14}: {vp[k]}")
    print(f"elements      : {_fmt_set(vp['elements'], vp['elements_unrestricted'])}")
    print(f"relationships : {_fmt_set(vp['relationships'], vp['relationships_unrestricted'])}")
    if not vp["elements_unrestricted"]:
        print(f"{'':14}  (+ Junction, Grouping — always allowed)")
    return 0


def _cmd_check(model_path: str, view_name: str, slug: str) -> int:
    vp = get_viewpoint(slug)
    if vp is None:
        sys.stderr.write(f"unknown viewpoint {slug!r}; known: {', '.join(known_slugs())}\n")
        return 2
    try:
        from pyArchimate import Model
    except ImportError:
        sys.stderr.write("pyArchimate not importable — run via: poetry run python viewpoints.py ...\n")
        return 2

    model = Model("viewpoints")
    model.read(model_path)
    views = [v for v in model.views if v.name == view_name]
    if not views:
        sys.stderr.write(f"no view named {view_name!r}; have: {[v.name for v in model.views]}\n")
        return 2
    view = views[0]

    on_view: set[str] = set()
    el_types: list[str] = []
    stack = list(view.nodes)
    while stack:
        n = stack.pop()
        c = getattr(n, "concept", None)
        if c is not None and getattr(c, "type", None):
            on_view.add(c.uuid)
            el_types.append(c.type)
        stack.extend(getattr(n, "nodes", []) or [])
    rel_types = [r.type for r in model.relationships if r.source.uuid in on_view and r.target.uuid in on_view]

    findings = check_conformance(vp, el_types, rel_types)
    if not findings:
        print(f"{view_name!r} conforms to the {slug!r} viewpoint")
        return 0
    print(f"{view_name!r} does NOT conform to the {slug!r} viewpoint:")
    for f in findings:
        print(f"  - {f}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list every known viewpoint slug")
    p_show = sub.add_parser("show", help="print one viewpoint definition")
    p_show.add_argument("slug")
    p_check = sub.add_parser("check", help="check a view in a model against a viewpoint")
    p_check.add_argument("model")
    p_check.add_argument("--view", required=True)
    p_check.add_argument("--viewpoint", required=True)
    args = ap.parse_args()

    if args.cmd == "list":
        return _cmd_list()
    if args.cmd == "show":
        return _cmd_show(args.slug)
    return _cmd_check(args.model, args.view, args.viewpoint)


if __name__ == "__main__":
    raise SystemExit(main())
