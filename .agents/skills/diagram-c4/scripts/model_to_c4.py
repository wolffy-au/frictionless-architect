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
DEPLOY_TYPES = {"Node", "Device", "SystemSoftware", "CommunicationNetwork", "Path", "Equipment", "Facility"}
STRUCTURAL_RELS = {"Realization", "Assignment", "Composition", "Aggregation", "Specialization"}
ACCESS_LABEL = {
    "Read": "reads from",
    "Write": "writes to",
    "ReadWrite": "reads from and writes to",
    "Access": "accesses",
}


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
    """UUIDs composed/aggregated (transitively) by the system in focus."""
    inside: set[str] = set()
    frontier = [system_uuid]
    while frontier:
        cur = frontier.pop()
        for r in model.relationships:
            if r.type in {"Composition", "Aggregation"} and r.source.uuid == cur and r.target.uuid not in inside:
                inside.add(r.target.uuid)
                frontier.append(r.target.uuid)
    return inside


def generate(path: str, system_name: str, level: str, layout: str) -> tuple[str, list[str]]:  # noqa: C901 - linear codegen
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
    lines = [
        "@startuml",
        f"!include <C4/{include}>",
        "",
        f"title {esc(system.name)} — C4 {level.capitalize()}",
        f"LAYOUT_{layout}()",
        "",
    ]

    kind: dict[str, str] = {}  # uuid -> emitted C4 macro alias-kind

    def classify(e) -> str:
        override = prop(e, "c4")
        if override:
            return override
        if e.type in PERSON_TYPES:
            return "person"
        if e.uuid in inside:
            if e.type in STORE_TYPES:
                return "containerDb"
            if e.type == "ApplicationComponent":
                return "container"
            return "ignore"
        if e.type in ("ApplicationComponent", "ApplicationService"):
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
        lines.append(f'System({alias(system.uuid)}, "{esc(system.name)}", "{esc(system.desc)}")')
        kind[system.uuid] = "system"

    # People + external systems
    for e in model.elements:
        if e.uuid in kind or e.uuid == system.uuid:
            continue
        c = classify(e)
        if c == "person":
            lines.append(f'Person({alias(e.uuid)}, "{esc(e.name)}", "{esc(e.desc)}")')
            kind[e.uuid] = "person"
        elif c == "external":
            lines.append(f'System_Ext({alias(e.uuid)}, "{esc(e.name)}", "{esc(e.desc)}")')
            kind[e.uuid] = "external"

    # For context level, fold inside-elements onto the system box.
    def endpoint(uuid: str) -> str | None:
        if uuid in kind:
            return alias(uuid)
        if level == "context" and uuid in inside:
            return alias(system.uuid)
        return None

    lines.append("")
    seen_edges: set[tuple[str, str, str]] = set()
    for r in model.relationships:
        if r.type in STRUCTURAL_RELS:
            continue
        s, t = endpoint(r.source.uuid), endpoint(r.target.uuid)
        if not s or not t or s == t:
            continue
        label = prop(r, "c4-label")
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
        edge = (s, t, label or "")
        if edge in seen_edges:
            continue
        seen_edges.add(edge)
        args = f'{s}, {t}, "{esc(label)}"'
        if tech:
            args += f', "{tech}"'
        lines.append(f"Rel({args})")

    lines += ["", "@enduml", ""]
    return "\n".join(lines), warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--system", required=True, help="name of the system in focus")
    ap.add_argument("--level", choices=("context", "container"), default="container")
    ap.add_argument("--layout", choices=("WITH_LEGEND", "TOP_DOWN", "LEFT_RIGHT"), default="WITH_LEGEND")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    try:
        puml, warns = generate(args.model, args.system, args.level, args.layout)
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
