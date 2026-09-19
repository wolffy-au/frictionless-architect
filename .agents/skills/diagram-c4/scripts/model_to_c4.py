#!/usr/bin/env python3
"""Project a validated ArchiMate model into a C4-PlantUML diagram.

    poetry run python model_to_c4.py MODEL --system "Name" \
        [--level context|container] [--layout WITH_LEGEND|TOP_DOWN|LEFT_RIGHT] [-o OUT.puml]

Applies the mapping in references/archimate-to-c4-mapping.md. Exit 0 = wrote
output, 2 = load/lookup error.
"""

from __future__ import annotations

import argparse
import re
import sys

try:
    from pyArchimate import Model
except ImportError:
    sys.stderr.write("pyArchimate not importable — run via: poetry run python model_to_c4.py ...\n")
    raise SystemExit(2) from None

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
DEPLOY_TYPES = {"Node", "Device", "SystemSoftware", "CommunicationNetwork", "Path", "Equipment", "Facility"}
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
DIRECTIONS = {"U", "D", "L", "R"}


def alias(uuid: str) -> str:
    return "n_" + re.sub(r"[^0-9a-zA-Z]", "", uuid)[:16]


def esc(text: str | None) -> str:
    return (text or "").replace('"', "'").replace("\n", " ").strip()


def prop(obj, key: str) -> str | None:
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


def generate(  # noqa: C901 - linear codegen
    path: str, system_name: str, level: str, layout: str, enterprise: str | None = None
) -> tuple[str, list[str]]:
    model = Model("c4")
    model.read(path)
    warns: list[str] = []

    systems = [e for e in model.elements if e.name == system_name or prop(e, "c4") == "system"]
    systems = [e for e in systems if e.name == system_name] or systems
    if not systems:
        raise KeyError(f"no element named {system_name!r} and none with c4=system")
    system = systems[0]
    inside = contained_by_system(model, system.uuid)

    include = "C4_Container" if level == "container" else "C4_Context"
    header = [
        "@startuml",
        f"' GENERATED from {path} by diagram-c4 (model_to_c4.py) — do not edit; fix the ArchiMate model.",
        f"!include <C4/{include}>",
        "",
        f"title {esc(system.name)} — C4 {level.capitalize()}",
        f"LAYOUT_{layout}()",
        "",
    ]
    lines: list[str] = []

    kind: dict[str, str] = {}  # uuid -> emitted C4 macro alias-kind

    def classify(e) -> str:
        override = prop(e, "c4")
        if override:
            return override
        if e.type in PERSON_TYPES:
            return "person"
        if e.uuid in inside:
            if e.type in STORE_TYPES or e.type in BUSINESS_STORE_TYPES:
                return "containerDb"
            if e.type == "ApplicationComponent":
                return "container"
            return "ignore"
        if e.type in ("ApplicationComponent", "ApplicationService"):
            return "external"
        if level == "context" and e.type in BUSINESS_STORE_TYPES:
            return "externalDb"
        if level == "context" and e.type in BUSINESS_SERVICE_TYPES:
            return "external"
        if e.type in DEPLOY_TYPES:
            return "ignore"
        return "ignore"

    # System box
    if level == "container":
        lines.append(f'System_Boundary({alias(system.uuid)}, "{esc(system.name)}") {{')
        for e in model.elements:
            if e.uuid not in inside:
                continue
            c = classify(e)
            if c == "container":
                lines.append(f'  Container({alias(e.uuid)}, "{esc(e.name)}", "", "{esc(e.desc)}")')
                kind[e.uuid] = "container"
            elif c == "containerDb":
                lines.append(f'  ContainerDb({alias(e.uuid)}, "{esc(e.name)}", "", "{esc(e.desc)}")')
                kind[e.uuid] = "containerDb"
            elif c == "containerQueue":
                lines.append(f'  ContainerQueue({alias(e.uuid)}, "{esc(e.name)}", "", "{esc(e.desc)}")')
                kind[e.uuid] = "containerQueue"
        lines.append("}")
    else:
        sys_macro = SYSTEM_MACROS.get(prop(system, "c4-kind"), "System")
        lines.append(f'{sys_macro}({alias(system.uuid)}, "{esc(system.name)}", "{esc(system.desc)}")')
        kind[system.uuid] = "system"

    # People + external systems
    for e in model.elements:
        if e.uuid in kind or e.uuid == system.uuid:
            continue
        c = classify(e)
        macro = ELEMENT_MACROS.get(c)
        if macro:
            lines.append(f'{macro}({alias(e.uuid)}, "{esc(e.name)}", "{esc(e.desc)}")')
            kind[e.uuid] = c

    # For context level, fold inside-elements onto the system box.
    def endpoint(uuid: str) -> str | None:
        if uuid in kind:
            return alias(uuid)
        if level == "context" and uuid in inside:
            return alias(system.uuid)
        return None

    def rel_macro(r) -> str:
        if str(prop(r, "c4-birel") or "").lower() in {"true", "yes", "1"}:
            return "BiRel"
        direction = str(prop(r, "c4-direction") or "").upper()
        if direction in DIRECTIONS:
            return f"Rel_{direction}"
        return "Rel"

    lines.append("")
    raw: list[tuple[str, str, str, str, str]] = []  # (source, target, label, technology, macro)
    for r in model.relationships:
        if r.type in STRUCTURAL_RELS:
            continue
        s, t = endpoint(r.source.uuid), endpoint(r.target.uuid)
        if not s or not t or s == t:
            continue
        macro = rel_macro(r)
        label = prop(r, "c4-label") or (getattr(r, "name", "") or None)
        tech = esc(prop(r, "c4-technology") or "")
        if r.type == "Serving":
            s, t = t, s  # served party depends on the server
            label = label or "uses"
        elif r.type == "Flow":
            label = label or "sends data to"
        elif r.type == "Triggering":
            label = label or "triggers"
        elif r.type == "Access":
            label = label or ACCESS_LABEL.get(str(getattr(r, "access_type", "Access")), "accesses")
        elif r.type == "Association":
            label = label or "related to"
        else:
            warns.append(f"relationship type {r.type!r} not in C4 mapping — drawn as generic Rel")
            label = label or r.type.lower()
        raw.append((s, t, label or "", tech, macro))

    def merge_macro(current: str, incoming: str) -> str:
        # BiRel wins outright; otherwise first non-default (directional) macro sticks.
        if "BiRel" in (current, incoming):
            return "BiRel"
        return incoming if current == "Rel" and incoming != "Rel" else current

    if level == "context":
        # Every interaction with an inside-element folds onto the one system
        # box, so many container-level relationships collapse onto the same
        # (source, target) pair. Merge each pair into a single Rel (or
        # BiRel/Rel_<dir> if any contributing relationship asked for one)
        # that lists its distinct labels one per line, rather than drawing a
        # fan of near-duplicate arrows.
        merged: dict[tuple[str, str], tuple[list[str], str, str]] = {}
        order: list[tuple[str, str]] = []
        for s, t, label, tech, macro in raw:
            key = (s, t)
            if key not in merged:
                merged[key] = ([], tech, "Rel")
                order.append(key)
            labels, kept_tech, kept_macro = merged[key]
            if label and label not in labels:
                labels.append(label)
            if tech and not kept_tech:
                kept_tech = tech
            merged[key] = (labels, kept_tech, merge_macro(kept_macro, macro))
        for s, t in order:
            labels, tech, macro = merged[(s, t)]
            joined = "\\n".join(esc(x) for x in labels)
            args = f'{s}, {t}, "{joined}"'
            if tech:
                args += f', "{tech}"'
            lines.append(f"{macro}({args})")
    else:
        # Container level: keep distinct labels as separate arrows; drop only
        # exact duplicates.
        seen: set[tuple[str, str, str]] = set()
        for s, t, label, tech, macro in raw:
            if (s, t, label) in seen:
                continue
            seen.add((s, t, label))
            args = f'{s}, {t}, "{esc(label)}"'
            if tech:
                args += f', "{tech}"'
            lines.append(f"{macro}({args})")

    if enterprise:
        boundary_alias = "enterprise_" + re.sub(r"[^0-9a-zA-Z]", "", enterprise)[:16]
        lines = [f'Enterprise_Boundary({boundary_alias}, "{esc(enterprise)}") {{', *lines, "}"]

    lines = header + lines + ["", "@enduml", ""]
    return "\n".join(lines), warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--system", required=True, help="name of the system in focus")
    ap.add_argument("--level", choices=("context", "container"), default="container")
    ap.add_argument("--layout", choices=("WITH_LEGEND", "TOP_DOWN", "LEFT_RIGHT"), default="WITH_LEGEND")
    ap.add_argument("--enterprise", help="wrap the diagram in an Enterprise_Boundary with this label")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    try:
        puml, warns = generate(args.model, args.system, args.level, args.layout, args.enterprise)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: {exc}\n")
        return 2

    for w in warns:
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
