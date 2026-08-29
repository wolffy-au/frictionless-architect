#!/usr/bin/env python3
"""Generate an ArchiMate PlantUML diagram from a validated ArchiMate model.

    poetry run python model_to_puml.py MODEL[.archimate|.xml] [--view NAME] [-o OUT.puml]

Emits PlantUML using the bundled `<archimate/Archimate>` stdlib. With
--view, only the elements/relationships shown on that ArchiMate view are
included; without it, the whole model. Unmapped element types fall back to
a plain `rectangle` and are reported on stderr.

Exit 0 = wrote output, 2 = load/lookup error.
"""
from __future__ import annotations

import argparse
import re
import sys

try:
    from pyArchimate import Model
except ImportError:
    sys.stderr.write("pyArchimate not importable — run via: poetry run python model_to_puml.py ...\n")
    raise SystemExit(2) from None

# ArchiMate element type (pyArchimate bare name) -> <archimate/Archimate> macro.
# Verified against PlantUML 1.2026.7's bundled stdlib.
ELEMENT_MACRO = {
    # Business
    "BusinessActor": "Business_Actor", "BusinessRole": "Business_Role",
    "BusinessCollaboration": "Business_Collaboration", "BusinessInterface": "Business_Interface",
    "BusinessProcess": "Business_Process", "BusinessFunction": "Business_Function",
    "BusinessInteraction": "Business_Interaction", "BusinessEvent": "Business_Event",
    "BusinessService": "Business_Service", "BusinessObject": "Business_Object",
    "Contract": "Business_Contract", "Representation": "Business_Representation",
    "Product": "Business_Product",
    # Application
    "ApplicationComponent": "Application_Component", "ApplicationCollaboration": "Application_Collaboration",
    "ApplicationInterface": "Application_Interface", "ApplicationFunction": "Application_Function",
    "ApplicationInteraction": "Application_Interaction", "ApplicationProcess": "Application_Process",
    "ApplicationEvent": "Application_Event", "ApplicationService": "Application_Service",
    "DataObject": "Application_DataObject",
    # Technology
    "Node": "Technology_Node", "Device": "Technology_Device", "SystemSoftware": "Technology_SystemSoftware",
    "TechnologyCollaboration": "Technology_Collaboration", "TechnologyInterface": "Technology_Interface",
    "Path": "Technology_Path", "CommunicationNetwork": "Technology_CommunicationNetwork",
    "TechnologyFunction": "Technology_Function", "TechnologyProcess": "Technology_Process",
    "TechnologyInteraction": "Technology_Interaction", "TechnologyEvent": "Technology_Event",
    "TechnologyService": "Technology_Service", "Artifact": "Technology_Artifact",
    # Physical
    "Equipment": "Physical_Equipment", "Facility": "Physical_Facility",
    "DistributionNetwork": "Physical_DistributionNetwork", "Material": "Physical_Material",
    # Motivation
    "Stakeholder": "Motivation_Stakeholder", "Driver": "Motivation_Driver",
    "Assessment": "Motivation_Assessment", "Goal": "Motivation_Goal", "Outcome": "Motivation_Outcome",
    "Principle": "Motivation_Principle", "Requirement": "Motivation_Requirement",
    "Constraint": "Motivation_Constraint", "Meaning": "Motivation_Meaning", "Value": "Motivation_Value",
    # Strategy
    "Resource": "Strategy_Resource", "Capability": "Strategy_Capability",
    "CourseOfAction": "Strategy_CourseOfAction", "ValueStream": "Strategy_ValueStream",
    # Implementation & Migration
    "WorkPackage": "Implementation_WorkPackage", "Deliverable": "Implementation_Deliverable",
    "ImplementationEvent": "Implementation_Event", "Plateau": "Implementation_Plateau",
    "Gap": "Implementation_Gap",
    # Composite
    "Grouping": "Grouping",
}

REL_MACRO = {
    "Composition": "Rel_Composition", "Aggregation": "Rel_Aggregation", "Assignment": "Rel_Assignment",
    "Realization": "Rel_Realization", "Serving": "Rel_Serving", "Access": "Rel_Access",
    "Influence": "Rel_Influence", "Triggering": "Rel_Triggering", "Flow": "Rel_Flow",
    "Specialization": "Rel_Specialization", "Association": "Rel_Association",
}


def alias(uuid: str) -> str:
    return "e_" + re.sub(r"[^0-9a-zA-Z]", "", uuid)[:16]


def esc(text: str | None) -> str:
    return (text or "").replace('"', "'").replace("\n", " ").strip()


def generate(path: str, view_name: str | None) -> tuple[str, list[str]]:
    model = Model("diagram")
    model.read(path)
    warnings: list[str] = []

    if view_name:
        views = [v for v in model.views if v.name == view_name]
        if not views:
            raise KeyError(f"no view named {view_name!r}; have: {[v.name for v in model.views]}")
        wanted = set()

        def walk(nodes):
            for n in nodes:
                if getattr(n, "concept", None) is not None:
                    wanted.add(n.concept.uuid)
                walk(getattr(n, "nodes", []) or [])

        walk(views[0].nodes)
        elements = [e for e in model.elements if e.uuid in wanted]
        relationships = [
            r for r in model.relationships if r.source.uuid in wanted and r.target.uuid in wanted
        ]
        title = view_name
    else:
        elements = list(model.elements)
        relationships = list(model.relationships)
        title = model.name or path

    lines = ["@startuml", "!include <archimate/Archimate>", "", f'title {esc(title)}', ""]

    for e in elements:
        macro = ELEMENT_MACRO.get(e.type)
        if macro:
            lines.append(f'{macro}({alias(e.uuid)}, "{esc(e.name) or e.type}")')
        else:
            warnings.append(f"unmapped element type {e.type!r} ({e.name!r}) -> plain rectangle")
            lines.append(f'rectangle "{esc(e.name) or e.type}" as {alias(e.uuid)}')
    lines.append("")

    for r in relationships:
        macro = REL_MACRO.get(r.type)
        s, t = alias(r.source.uuid), alias(r.target.uuid)
        if macro:
            lines.append(f'{macro}({s}, {t}, "{esc(getattr(r, "name", ""))}")')
        else:
            warnings.append(f"unmapped relationship type {r.type!r} -> plain association")
            lines.append(f"{s} --> {t}")

    lines += ["", "@enduml", ""]
    return "\n".join(lines), warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--view", help="restrict to the contents of this ArchiMate view")
    ap.add_argument("-o", "--output", help="write .puml here (default: stdout)")
    args = ap.parse_args()

    try:
        puml, warnings = generate(args.model, args.view)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: {exc}\n")
        return 2

    for w in warnings:
        sys.stderr.write(f"warning: {w}\n")

    if args.output:
        with open(args.output, "w") as fh:
            fh.write(puml)
        sys.stderr.write(f"wrote {args.output}\n")
    else:
        print(puml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
