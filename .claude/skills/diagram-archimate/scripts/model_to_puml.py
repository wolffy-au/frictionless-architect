#!/usr/bin/env python3
"""Generate an ArchiMate PlantUML diagram from a validated ArchiMate model.

    poetry run python model_to_puml.py MODEL[.archimate|.xml] [--view NAME] [-o OUT.puml]
        [--no-direction TYPE ...]

Emits PlantUML using the bundled `<archimate/Archimate>` stdlib. With
--view, only the elements/relationships shown on that ArchiMate view are
included; without it, the whole model. Unmapped element types fall back to
a plain `rectangle` and are reported on stderr.

--no-direction TYPE (repeatable) drops the default Up/Right layout hint
(REL_DIRECTION) for that relationship type on this view, letting graphviz
pick freely instead. Use it where the default rank hint fights itself — e.g.
a relationship type with edges running both ways between the same pair of
elements (a hub-and-spoke or mesh, not a one-way sequence), which forces
graphviz to silently drop half the constraints as back-edges and produces a
tangled layout regardless of the underlying data.

Exit 0 = wrote output, 2 = load/lookup error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    from pyArchimate import Model
except ImportError:
    sys.stderr.write("pyArchimate not importable — run via: poetry run python model_to_puml.py ...\n")
    raise SystemExit(2) from None

# ArchiMate element type (pyArchimate bare name) -> <archimate/Archimate> macro.
# Verified against PlantUML 1.2026.7's bundled stdlib.
ELEMENT_MACRO = {
    # Business
    "BusinessActor": "Business_Actor",
    "BusinessRole": "Business_Role",
    "BusinessCollaboration": "Business_Collaboration",
    "BusinessInterface": "Business_Interface",
    "BusinessProcess": "Business_Process",
    "BusinessFunction": "Business_Function",
    "BusinessInteraction": "Business_Interaction",
    "BusinessEvent": "Business_Event",
    "BusinessService": "Business_Service",
    "BusinessObject": "Business_Object",
    "Contract": "Business_Contract",
    "Representation": "Business_Representation",
    "Product": "Business_Product",
    # Application
    "ApplicationComponent": "Application_Component",
    "ApplicationCollaboration": "Application_Collaboration",
    "ApplicationInterface": "Application_Interface",
    "ApplicationFunction": "Application_Function",
    "ApplicationInteraction": "Application_Interaction",
    "ApplicationProcess": "Application_Process",
    "ApplicationEvent": "Application_Event",
    "ApplicationService": "Application_Service",
    "DataObject": "Application_DataObject",
    # Technology
    "Node": "Technology_Node",
    "Device": "Technology_Device",
    "SystemSoftware": "Technology_SystemSoftware",
    "TechnologyCollaboration": "Technology_Collaboration",
    "TechnologyInterface": "Technology_Interface",
    "Path": "Technology_Path",
    "CommunicationNetwork": "Technology_CommunicationNetwork",
    "TechnologyFunction": "Technology_Function",
    "TechnologyProcess": "Technology_Process",
    "TechnologyInteraction": "Technology_Interaction",
    "TechnologyEvent": "Technology_Event",
    "TechnologyService": "Technology_Service",
    "Artifact": "Technology_Artifact",
    # Physical
    "Equipment": "Physical_Equipment",
    "Facility": "Physical_Facility",
    "DistributionNetwork": "Physical_DistributionNetwork",
    "Material": "Physical_Material",
    # Motivation
    "Stakeholder": "Motivation_Stakeholder",
    "Driver": "Motivation_Driver",
    "Assessment": "Motivation_Assessment",
    "Goal": "Motivation_Goal",
    "Outcome": "Motivation_Outcome",
    "Principle": "Motivation_Principle",
    "Requirement": "Motivation_Requirement",
    "Constraint": "Motivation_Constraint",
    "Meaning": "Motivation_Meaning",
    "Value": "Motivation_Value",
    # Strategy
    "Resource": "Strategy_Resource",
    "Capability": "Strategy_Capability",
    "CourseOfAction": "Strategy_CourseOfAction",
    "ValueStream": "Strategy_ValueStream",
    # Implementation & Migration
    "WorkPackage": "Implementation_WorkPackage",
    "Deliverable": "Implementation_Deliverable",
    "ImplementationEvent": "Implementation_Event",
    "Plateau": "Implementation_Plateau",
    "Gap": "Implementation_Gap",
    # Composite
    "Grouping": "Grouping",
}

REL_MACRO = {
    "Composition": "Rel_Composition",
    "Aggregation": "Rel_Aggregation",
    "Assignment": "Rel_Assignment",
    "Realization": "Rel_Realization",
    "Serving": "Rel_Serving",
    "Access": "Rel_Access",
    "Influence": "Rel_Influence",
    "Triggering": "Rel_Triggering",
    "Flow": "Rel_Flow",
    "Specialization": "Rel_Specialization",
    "Association": "Rel_Association",
}

# Default layout direction per relationship type, using the stdlib's directional
# macro variants (e.g. `Rel_Realization_Up`). Realization/Serving read bottom-up
# (implementation realizing/serving something above it); Triggering/Flow read
# left-to-right (process sequence). Types not listed here use the plain macro
# and let graphviz pick a direction. A view whose graph isn't actually a
# one-way sequence for one of these types (e.g. a hub-and-spoke with edges
# running both ways between the same pair) should pass that type via
# --no-direction / views.yaml's `no_direction:` key instead of fighting it —
# see render_diagrams.py.
REL_DIRECTION = {
    "Realization": "Up",
    "Specialization": "Up",
    "Serving": "Up",
    "Triggering": "Right",
    "Flow": "Right",
}

# Access relationship access_type -> stdlib macro suffix (Rel_Access_r/_w/_rw),
# giving the connector its read/write arrowhead. Undefined/other -> plain Rel_Access.
ACCESS_TYPE_SUFFIX = {
    "Read": "r",
    "Write": "w",
    "ReadWrite": "rw",
}

# Relationship types rendered as containment (child nested in parent's box) rather
# than an arrow. source = whole/container/active-structure, target = part/behaviour.
# A child is only nested if it has exactly one such parent on the diagram and the
# nesting introduces no cycle; otherwise the relationship stays a plain arrow.
NEST_RELS = {"Composition", "Aggregation", "Assignment"}


def alias(uuid: str) -> str:
    return "e_" + re.sub(r"[^0-9a-zA-Z]", "", uuid)[:16]


def esc(text: str | None) -> str:
    return (text or "").replace('"', "'").replace("\n", " ").strip()


def _view_concepts(view: Any) -> set[str]:
    """UUIDs of every concept placed on an ArchiMate view, walking nested nodes."""
    wanted: set[str] = set()
    stack = list(view.nodes)
    while stack:
        n = stack.pop()
        if getattr(n, "concept", None) is not None:
            wanted.add(n.concept.uuid)
        stack.extend(getattr(n, "nodes", []) or [])
    return wanted


def _nest_tree(elements: list[Any], relationships: list[Any]) -> tuple[dict[str, list[str]], set[str], set[int]]:
    """Fold containment relationships into nesting.

    Returns (children, roots-excluded set, ``id()``s of the folded relationships).
    A part is nested under a whole only if it has exactly one containment parent
    on the diagram and the nesting introduces no cycle.
    """
    by_uuid = {e.uuid: e for e in elements}

    # Pass 1: gather the legal containment edges and count each part's parents.
    candidates: list[tuple[str, str, Any]] = []
    parent_count: dict[str, int] = {}
    for r in relationships:
        if r.type not in NEST_RELS:
            continue
        whole, part = r.source.uuid, r.target.uuid
        if whole not in by_uuid or part not in by_uuid or whole == part:
            continue
        candidates.append((whole, part, r))
        parent_count[part] = parent_count.get(part, 0) + 1

    # Pass 2: nest a part only when it has exactly one container on the diagram
    # and the nesting introduces no cycle; every other containment stays an arrow.
    parent_of: dict[str, str] = {}
    children: dict[str, list[str]] = {}
    nested: set[int] = set()

    def is_descendant(node: str, of: str) -> bool:
        cur: str | None = of
        while cur is not None:
            if cur == node:
                return True
            cur = parent_of.get(cur)
        return False

    for whole, part, r in candidates:
        if parent_count[part] != 1 or is_descendant(part, whole):
            continue
        parent_of[part] = whole
        children.setdefault(whole, []).append(part)
        nested.add(id(r))
    return children, set(parent_of), nested


def _element_lines(
    elements: list[Any], children: dict[str, list[str]], contained: set[str], warnings: list[str]
) -> list[str]:
    by_uuid = {e.uuid: e for e in elements}
    out: list[str] = []

    def emit(e: Any, depth: int) -> None:
        pad = "  " * depth
        macro = ELEMENT_MACRO.get(e.type)
        if macro:
            head = f'{pad}{macro}({alias(e.uuid)}, "{esc(e.name) or e.type}")'
        else:
            warnings.append(f"unmapped element type {e.type!r} ({e.name!r}) -> plain rectangle")
            head = f'{pad}rectangle "{esc(e.name) or e.type}" as {alias(e.uuid)}'
        kids = children.get(e.uuid, [])
        if not kids:
            out.append(head)
            return
        out.append(head + " {")
        for k in kids:
            emit(by_uuid[k], depth + 1)
        out.append(pad + "}")

    for e in elements:
        if e.uuid not in contained:
            emit(e, 0)
    return out


def generate(
    path: str, view_name: str | None, no_direction: set[str] | None = None, max_width: int | None = None
) -> tuple[str, list[str]]:
    model = Model("diagram")
    model.read(path)
    warnings: list[str] = []

    if view_name:
        views = [v for v in model.views if v.name == view_name]
        if not views:
            raise KeyError(f"no view named {view_name!r}; have: {[v.name for v in model.views]}")
        view = views[0]
        wanted = _view_concepts(view)
        elements = [e for e in model.elements if e.uuid in wanted]
        # Render exactly the connections the view itself declares, not every
        # model relationship whose endpoints happen to both be in scope — a
        # view may deliberately omit an in-scope relationship (build.py's
        # per-view `exclude:` patterns), and that suppression must survive
        # into the diagram rather than being silently recomputed away here.
        relationships = [model.rels_dict[c.ref] for c in view.conns if c.ref in model.rels_dict]
        title = view_name
    else:
        elements = list(model.elements)
        relationships = list(model.relationships)
        title = model.name or path

    children, contained, nested = _nest_tree(elements, relationships)

    lines = ["@startuml", "!include <archimate/Archimate>", ""]
    if max_width:
        # Scales the rendered image down (never up) to fit this width in px.
        lines.append(f"scale max {max_width} width")
    lines += [f"title {esc(title)}", ""]
    lines += _element_lines(elements, children, contained, warnings)
    lines.append("")

    for r in relationships:
        if id(r) in nested:
            continue
        macro = REL_MACRO.get(r.type)
        s, t = alias(r.source.uuid), alias(r.target.uuid)
        if macro:
            if r.type == "Access":
                suffix = ACCESS_TYPE_SUFFIX.get(getattr(r, "access_type", None))
                if suffix:
                    macro = f"{macro}_{suffix}"
            direction = None if no_direction and r.type in no_direction else REL_DIRECTION.get(r.type)
            if direction:
                macro = f"{macro}_{direction}"
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
    ap.add_argument(
        "--no-direction",
        action="append",
        default=[],
        metavar="TYPE",
        help="drop the default layout-direction hint for this relationship type (repeatable)",
    )
    ap.add_argument(
        "--max-width",
        type=int,
        metavar="PX",
        help="cap the rendered width in pixels (PlantUML `scale max PX width`); smaller diagrams are untouched",
    )
    ap.add_argument("-o", "--output", help="write .puml here (default: stdout)")
    args = ap.parse_args()

    try:
        puml, warnings = generate(args.model, args.view, set(args.no_direction), args.max_width)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: {exc}\n")
        return 2

    for w in warnings:
        sys.stderr.write(f"warning: {w}\n")

    if args.output:
        # Resolve before writing: `-o` is a normal CLI output flag, not
        # untrusted network input, but an agent may construct this path from
        # other data, so a bad value should fail with a clear error here
        # rather than an ambiguous OS error, or worse, land somewhere the
        # caller didn't intend.
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(puml)
        sys.stderr.write(f"wrote {out_path}\n")
    else:
        print(puml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
