#!/usr/bin/env python3
"""Build the Frictionless Architecture Platform ArchiMate model from YAML.

    poetry run python architecture/model/build.py

``architecture/model/elements.yaml`` + ``relationships.yaml`` are the single
source of truth. This script projects them into ``frictionless-architect.xml``
(Open Group Exchange Format) via pyArchimate, then runs the ``model-archimate``
validator over the result. Every diagram (``*.puml`` / ``*.svg``) is in turn a
projection of that XML — regenerate them with the ``diagram-c4`` /
``diagram-archimate`` skills after running this.

Schema (see ``architecture/model/README.md``):

* element:  ``type`` (bare ArchiMate 3.2 concept, case-insensitive) / ``id``
  (stable) / ``name`` / ``desc`` (optional) / ``props`` (optional str->str)
* relationship: ``type`` / ``source`` / ``target`` / ``label`` (optional) /
  ``props`` (optional; ``access_type`` for Access, ``c4-label`` overrides
  ``label`` in the C4 projection only)
* view: ``id`` / ``name`` / ``members`` (element ids) and/or ``include_types``

``id`` values are hashed to deterministic UUIDs so regeneration does not churn
identifiers (and therefore diagrams).
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml
from pyArchimate import ArchiType, Element, Model
from pyArchimate.view.layout import LayoutConfig, apply_format, apply_layout

HERE = Path(__file__).parent
OUT = HERE / "frictionless-architect.xml"
VALIDATOR = HERE.parents[1] / ".agents/skills/model-archimate/scripts/validate.py"

# Fixed namespace — do not change; it anchors every generated identifier.
NS = uuid.UUID("6f4c0d2e-1a3b-5c7d-8e9f-0a1b2c3d4e5f")

_CANON = {name.lower(): name for name in ArchiType.__members__}


def canon(raw: str, errors: list[str], ctx: str) -> str | None:
    """Resolve a bare ArchiMate 3.2 concept name, case- and separator-insensitive.

    On an unknown name: append a contextual message to `errors` and return None,
    so the caller can skip the offending item and the build still reports every
    problem in one pass (rather than aborting on the first)."""
    key = str(raw).strip().replace("_", "").replace("-", "").lower()
    name = _CANON.get(key)
    if name is None:
        errors.append(f"{ctx}: {raw!r} is not an ArchiMate 3.2 concept name (pyArchimate.ArchiType)")
    return name


def det_id(*parts: str) -> str:
    return "id-" + uuid.uuid5(NS, "|".join(parts)).hex


def load(name: str, errors: list[str], optional: bool = False) -> list[dict[str, Any]]:
    path = HERE / name
    if optional and not path.exists():
        return []
    if not path.exists():
        errors.append(f"{name} is missing")
        return []
    data = yaml.safe_load(path.read_text()) or []
    if not isinstance(data, list):
        errors.append(f"{name} must be a YAML list")
        return []
    return data


def add_elements(
    m: Model, elements: list[dict[str, Any]], errors: list[str]
) -> tuple[dict[str, Element], dict[str, str]]:
    """Add every valid element and return (element-by-yaml-id, canon-type-by-yaml-id).

    The type map is returned so `add_views` can test element types without
    re-running `canon()` for every (view, element) pair."""
    by_id: dict[str, Element] = {}
    types: dict[str, str] = {}
    for e in elements:
        yid = e.get("id")
        if not yid or "type" not in e or "name" not in e:
            errors.append(f"element missing id/type/name: {e!r}")
            continue
        if yid in by_id:
            errors.append(f"duplicate element id: {yid}")
            continue
        ct = canon(e["type"], errors, f"element {yid}")
        if ct is None:
            continue
        el = m.add(
            concept_type=ct,
            name=e["name"],
            desc=e.get("desc"),
            uuid=det_id(yid),
        )
        for k, v in (e.get("props") or {}).items():
            el.prop(str(k), str(v))
        by_id[yid] = el
        types[yid] = ct
    return by_id, types


def add_relationships(m: Model, rels: list[dict[str, Any]], by_id: dict[str, Element], errors: list[str]) -> None:
    for r in rels:
        if "type" not in r or "source" not in r or "target" not in r:
            errors.append(f"relationship missing type/source/target: {r!r}")
            continue
        s, t = by_id.get(r["source"]), by_id.get(r["target"])
        if s is None or t is None:
            missing = r["source"] if s is None else r["target"]
            errors.append(f"relationship references unknown id {missing!r}: {r!r}")
            continue
        rt = canon(r["type"], errors, f"relationship {r['source']}->{r['target']}")
        if rt is None:
            continue
        props = dict(r.get("props") or {})
        access = props.pop("access_type", None)
        rel = m.add_relationship(
            rel_type=rt,
            source=s,
            target=t,
            name=r.get("label"),
            access_type=access,
            uuid=det_id(r["source"], r["type"], r["target"], r.get("label", "")),
        )
        for k, v in props.items():
            rel.prop(str(k), str(v))


def add_views(
    m: Model,
    views: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    by_id: dict[str, Element],
    types_by_id: dict[str, str],
    errors: list[str],
) -> None:
    """Minimal view scoping for the diagram-archimate skill: a view lists
    `members` (element ids) and/or `include_types` (every element of those
    ArchiMate types). `build.py` adds a node for every matching element and a
    connection for every model relationship whose *both* endpoints are on the
    view — the same in-scope rule `model_to_puml.py` applies when rendering —
    then runs pyArchimate's grid auto-layout + format so the view is usable
    when opened directly in Archi (the diagram skills re-lay-out via PlantUML
    and ignore these coordinates). The richer view schema (view kind,
    auto-membership rules) is still deferred."""
    for v in views:
        if "id" not in v or "name" not in v:
            errors.append(f"view missing id/name: {v!r}")
            continue
        want = set(v.get("members") or [])
        types = {
            c
            for t in (v.get("include_types") or [])
            if (c := canon(t, errors, f"view {v['id']} include_types")) is not None
        }
        # Deterministic view/node/connection uuids (via det_id) so the <views>
        # block of the generated XML does not churn on every build. add() below
        # bypasses get_or_create_view() only because that wrapper has no uuid arg.
        view: Any = m.add(ArchiType.View, name=v["name"], uuid=det_id(v["id"]))
        on_view: set[str] = set()  # element uuids with a node on this view
        for e in elements:
            selected = e["id"] in want or (types and types_by_id.get(e["id"]) in types)
            if selected and e["id"] in by_id:
                el = by_id[e["id"]]
                view.add(ref=el, uuid=det_id(v["id"], "node", el.uuid))
                on_view.add(el.uuid)
        for rel in m.relationships:
            if rel.source.uuid in on_view and rel.target.uuid in on_view:
                view.add_connection(ref=rel, uuid=det_id(v["id"], "conn", rel.uuid))
        missing = [mid for mid in want if mid not in by_id]
        if missing:
            errors.append(f"view {v['id']} references unknown ids: {missing}")
            continue
        # Grid layout is deterministic (layer-ordered row-major placement);
        # apply_format then applies the ArchiMate per-category node sizes.
        cfg = LayoutConfig(alignment="grid", layer_direction="vertical")
        for res in (apply_layout(view, cfg), apply_format(view, cfg)):
            if not res.success:
                errors.append(f"view {v['id']} {res.algorithm_used} failed: {res.error_message}")


def main() -> int:
    m = Model("frictionless-architect")
    errors: list[str] = []

    elements = load("elements.yaml", errors)
    by_id, types_by_id = add_elements(m, elements, errors)
    add_relationships(m, load("relationships.yaml", errors), by_id, errors)
    add_views(m, load("views.yaml", errors, optional=True), elements, by_id, types_by_id, errors)

    if errors:
        for msg in errors:
            sys.stderr.write(f"error: {msg}\n")
        return 2

    m.write(str(OUT))
    print(
        f"wrote {OUT.relative_to(HERE.parents[1])}  ({len(m.elements)} elements, {len(m.relationships)} relationships)"
    )

    result = subprocess.run([sys.executable, str(VALIDATOR), str(OUT)], capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
