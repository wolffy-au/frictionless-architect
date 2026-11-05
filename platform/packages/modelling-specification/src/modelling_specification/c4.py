#!/usr/bin/env python3
"""Project a validated ArchiMate model into a C4-PlantUML diagram.

    python -m modelling_specification.c4 MODEL --system "Name" \
        [--level context|container] [--layout WITH_LEGEND|TOP_DOWN|LEFT_RIGHT]

Applies the mapping in references/archimate-to-c4-mapping.md and prints the
diagram to stdout. Exit 0 = generated, 2 = load/lookup error.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Any

from pyArchimate import Model

PERSON_TYPES = {"BusinessActor", "BusinessRole"}
STORE_TYPES = {"DataObject", "Artifact"}
# BusinessObject is business-layer, not application/technology-layer like the
# STORE_TYPES above — appropriate to surface as an external datastore at
# Context level (where implementation detail is out of scope), but treated
# the same as STORE_TYPES when inside the system (folded/ContainerDb).
BUSINESS_STORE_TYPES = {"BusinessObject"}
# Likewise BusinessService is business-layer — level-appropriate as the
# externally-visible "system" at Context level. No auto-suppression of an
# ApplicationComponent/ApplicationService that Realizes it: that risks
# silently dropping relationships unique to the app-layer element. Mark such
# an element c4=ignore explicitly if you want only the BusinessService shown.
BUSINESS_SERVICE_TYPES = {"BusinessService"}
STRUCTURAL_RELS = {"Realization", "Assignment", "Composition", "Aggregation", "Specialization"}
ACCESS_LABEL = {
    "Read": "reads from",
    "Write": "writes to",
    "ReadWrite": "reads from and writes to",
    "Access": "accesses",
}
# c4 classification -> C4-PlantUML macro, for non-system, non-inside elements.
ELEMENT_MACROS = {
    "person": "Person",
    "personExt": "Person_Ext",
    "external": "System_Ext",
    "externalDb": "SystemDb_Ext",
    "externalQueue": "SystemQueue_Ext",
}
SYSTEM_MACROS = {"db": "SystemDb", "queue": "SystemQueue"}
# c4 classification -> C4-PlantUML macro, for elements inside the system boundary.
CONTAINER_MACROS = {
    "container": "Container",
    "containerDb": "ContainerDb",
    "containerQueue": "ContainerQueue",
}
# Relationship type -> label when the relationship names none. Access is absent:
# its default depends on the access type.
DEFAULT_LABELS = {
    "Serving": "uses",
    "Flow": "sends data to",
    "Triggering": "triggers",
    "Association": "related to",
}
DIRECTIONS = {"U", "D", "L", "R"}


def alias(uuid: str) -> str:
    """Return a PlantUML-safe alias (`n_` plus up to 16 alphanumerics of the UUID).

    Args:
        uuid: Model element or relationship identifier.

    Returns:
        The alias string.
    """
    return "n_" + re.sub(r"[^0-9a-zA-Z]", "", uuid)[:16]


def esc(text: str | None) -> str:
    """Make text safe inside a double-quoted PlantUML string.

    Args:
        text: Raw label, or None.

    Returns:
        Text with double quotes swapped for single quotes and newlines flattened.
    """
    return (text or "").replace('"', "'").replace("\n", " ").strip()


def prop(obj: Any, key: str) -> str | None:
    """Read a property value from a model object, tolerating missing props.

    Args:
        obj: Object exposing a `props` mapping.
        key: Property name.

    Returns:
        The value, or None when absent or `props` is unavailable.
    """
    try:
        props = obj.props
    except Exception:  # noqa: BLE001
        return None
    if isinstance(props, dict):
        return props.get(key)
    return None


def contained_by_system(model: Model, system_uuid: str) -> set[str]:
    """UUIDs composed/aggregated (transitively) by the system in focus.

    Only *structural containers* (the system, application components,
    collaborations, groupings) expand further — a contained ``DataObject`` /
    ``Artifact`` that in turn aggregates other data objects does not drag them
    into the boundary (that is a data-model relationship, not containment).
    """
    by_uuid = {e.uuid: e for e in model.elements}
    expandable = {"ApplicationComponent", "ApplicationCollaboration", "Grouping"}
    inside: set[str] = set()
    frontier = [system_uuid]
    while frontier:
        cur = frontier.pop()
        if cur != system_uuid and getattr(by_uuid.get(cur), "type", None) not in expandable:
            continue
        for r in model.relationships:
            if r.type in {"Composition", "Aggregation"} and r.source.uuid == cur and r.target.uuid not in inside:
                inside.add(r.target.uuid)
                frontier.append(r.target.uuid)
    return inside


@dataclass
class _Diagram:
    """What one generation is drawing: the system in focus, the elements inside
    it, and the C4 kind of each element emitted so far."""

    system: Any
    inside: set[str]
    level: str
    kind: dict[str, str] = field(default_factory=dict[str, str])


# (source, target, label, technology, macro)
_RawRel = tuple[str, str, str, str, str]


def _find_system(model: Model, system_name: str) -> Any:
    systems = [e for e in model.elements if e.name == system_name or prop(e, "c4") == "system"]
    systems = [e for e in systems if e.name == system_name] or systems
    if not systems:
        raise KeyError(f"no element named {system_name!r} and none with c4=system")
    return systems[0]


def _header(path: str, system: Any, level: str, layout: str) -> list[str]:
    include = "C4_Container" if level == "container" else "C4_Context"
    return [
        "@startuml",
        f"' GENERATED from {path} by diagram-c4 (model_to_c4.py) — do not edit; fix the ArchiMate model.",
        f"!include <C4/{include}>",
        "",
        f"title {esc(system.name)} — C4 {level.capitalize()}",
        f"LAYOUT_{layout}()",
        "",
    ]


def _classify_inside(e: Any) -> str:
    if e.type in STORE_TYPES or e.type in BUSINESS_STORE_TYPES:
        return "containerDb"
    return "container" if e.type == "ApplicationComponent" else "ignore"


def _classify_outside(e: Any, level: str) -> str:
    if e.type in ("ApplicationComponent", "ApplicationService"):
        return "external"
    if level == "context" and e.type in BUSINESS_STORE_TYPES:
        return "externalDb"
    if level == "context" and e.type in BUSINESS_SERVICE_TYPES:
        return "external"
    return "ignore"


def _classify(e: Any, diagram: _Diagram) -> str:
    override = prop(e, "c4")
    if override:
        return override
    if e.type in PERSON_TYPES:
        return "person"
    return _classify_inside(e) if e.uuid in diagram.inside else _classify_outside(e, diagram.level)


def _system_lines(model: Model, diagram: _Diagram) -> list[str]:
    """The system box: a boundary of containers, or one box at Context level."""
    system = diagram.system
    if diagram.level != "container":
        sys_macro = SYSTEM_MACROS.get(prop(system, "c4-kind") or "", "System")
        diagram.kind[system.uuid] = "system"
        return [f'{sys_macro}({alias(system.uuid)}, "{esc(system.name)}", "{esc(system.desc)}")']
    lines = [f'System_Boundary({alias(system.uuid)}, "{esc(system.name)}") {{']
    for e in model.elements:
        if e.uuid not in diagram.inside:
            continue
        c = _classify(e, diagram)
        macro = CONTAINER_MACROS.get(c)
        if macro:
            lines.append(f'  {macro}({alias(e.uuid)}, "{esc(e.name)}", "", "{esc(e.desc)}")')
            diagram.kind[e.uuid] = c
    lines.append("}")
    return lines


def _external_lines(model: Model, diagram: _Diagram) -> list[str]:
    """People and external systems."""
    lines: list[str] = []
    for e in model.elements:
        if e.uuid in diagram.kind or e.uuid == diagram.system.uuid:
            continue
        c = _classify(e, diagram)
        macro = ELEMENT_MACROS.get(c)
        if macro:
            lines.append(f'{macro}({alias(e.uuid)}, "{esc(e.name)}", "{esc(e.desc)}")')
            diagram.kind[e.uuid] = c
    return lines


def _endpoint(uuid: str, diagram: _Diagram) -> str | None:
    """A relationship end's alias. At Context level, inside-elements fold onto the system box."""
    if uuid in diagram.kind:
        return alias(uuid)
    if diagram.level == "context" and uuid in diagram.inside:
        return alias(diagram.system.uuid)
    return None


def _rel_macro(r: Any) -> str:
    if str(prop(r, "c4-birel") or "").lower() in {"true", "yes", "1"}:
        return "BiRel"
    direction = str(prop(r, "c4-direction") or "").upper()
    return f"Rel_{direction}" if direction in DIRECTIONS else "Rel"


def _rel_label(r: Any, warns: list[str]) -> str:
    label = prop(r, "c4-label") or (getattr(r, "name", "") or None)
    if r.type in DEFAULT_LABELS:
        return label or DEFAULT_LABELS[r.type]
    if r.type == "Access":
        return label or ACCESS_LABEL.get(str(getattr(r, "access_type", "Access")), "accesses")
    warns.append(f"relationship type {r.type!r} not in C4 mapping — drawn as generic Rel")
    return label or r.type.lower()


def _raw_rels(model: Model, diagram: _Diagram, warns: list[str]) -> list[_RawRel]:
    raw: list[_RawRel] = []
    for r in model.relationships:
        if r.type in STRUCTURAL_RELS:
            continue
        s, t = _endpoint(r.source.uuid, diagram), _endpoint(r.target.uuid, diagram)
        if not s or not t or s == t:
            continue
        if r.type == "Serving":
            s, t = t, s  # served party depends on the server
        tech = esc(prop(r, "c4-technology") or "")
        raw.append((s, t, _rel_label(r, warns), tech, _rel_macro(r)))
    return raw


def _merge_macro(current: str, incoming: str) -> str:
    # BiRel wins outright; otherwise first non-default (directional) macro sticks.
    if "BiRel" in (current, incoming):
        return "BiRel"
    return incoming if current == "Rel" and incoming != "Rel" else current


def _rel_line(macro: str, s: str, t: str, label: str, tech: str) -> str:
    args = f'{s}, {t}, "{label}"'
    if tech:
        args += f', "{tech}"'
    return f"{macro}({args})"


def _merged_rel_lines(raw: list[_RawRel]) -> list[str]:
    """Context level. Every interaction with an inside-element folds onto the one
    system box, so many container-level relationships collapse onto the same
    (source, target) pair. Merge each pair into a single Rel (or BiRel/Rel_<dir>
    if any contributing relationship asked for one) that lists its distinct labels
    one per line, rather than drawing a fan of near-duplicate arrows."""
    merged: dict[tuple[str, str], tuple[list[str], str, str]] = {}
    for s, t, label, tech, macro in raw:
        labels, kept_tech, kept_macro = merged.setdefault((s, t), ([], tech, "Rel"))
        if label and label not in labels:
            labels.append(label)
        merged[(s, t)] = (labels, kept_tech or tech, _merge_macro(kept_macro, macro))
    return [
        _rel_line(macro, s, t, "\\n".join(esc(x) for x in labels), tech)
        for (s, t), (labels, tech, macro) in merged.items()
    ]


def _distinct_rel_lines(raw: list[_RawRel]) -> list[str]:
    """Container level: keep distinct labels as separate arrows; drop only exact duplicates."""
    lines: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for s, t, label, tech, macro in raw:
        if (s, t, label) not in seen:
            seen.add((s, t, label))
            lines.append(_rel_line(macro, s, t, esc(label), tech))
    return lines


def generate(
    path: str, system_name: str, level: str, layout: str, enterprise: str | None = None
) -> tuple[str, list[str]]:
    """Generate C4-PlantUML for one system from a model file.

    Args:
        path: Path to the ArchiMate model XML.
        system_name: Name of the system in focus.
        level: `context` or `container`.
        layout: C4-PlantUML layout option.
        enterprise: Optional Enterprise_Boundary label.

    Returns:
        The PlantUML source and a list of warnings.

    Raises:
        KeyError: If the system cannot be found.
    """
    model = Model("c4")
    model.read(path)
    warns: list[str] = []

    system = _find_system(model, system_name)
    diagram = _Diagram(system, contained_by_system(model, system.uuid), level)

    lines = _system_lines(model, diagram)
    lines += _external_lines(model, diagram)
    lines.append("")
    raw = _raw_rels(model, diagram, warns)
    lines += _merged_rel_lines(raw) if level == "context" else _distinct_rel_lines(raw)

    if enterprise:
        boundary_alias = "enterprise_" + re.sub(r"[^0-9a-zA-Z]", "", enterprise)[:16]
        lines = [f'Enterprise_Boundary({boundary_alias}, "{esc(enterprise)}") {{', *lines, "}"]

    return "\n".join([*_header(path, system, level, layout), *lines, "", "@enduml", ""]), warns


def main() -> int:
    """Run the command-line entry point.

    Returns:
        Process exit code: 0 on success, 2 on error.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--system", required=True, help="name of the system in focus")
    ap.add_argument("--level", choices=("context", "container"), default="container")
    ap.add_argument("--layout", choices=("WITH_LEGEND", "TOP_DOWN", "LEFT_RIGHT"), default="WITH_LEGEND")
    ap.add_argument("--enterprise", help="wrap the diagram in an Enterprise_Boundary with this label")
    args = ap.parse_args()

    try:
        puml, warns = generate(args.model, args.system, args.level, args.layout, args.enterprise)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: {exc}\n")
        return 2

    for w in warns:
        sys.stderr.write(f"warning: {w}\n")
    print(puml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
