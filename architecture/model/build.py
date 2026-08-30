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
from pyArchimate import ArchiType, Model

HERE = Path(__file__).parent
OUT = HERE / "frictionless-architect.xml"
VALIDATOR = HERE.parents[1] / ".agents/skills/model-archimate/scripts/validate.py"

# Fixed namespace — do not change; it anchors every generated identifier.
NS = uuid.UUID("6f4c0d2e-1a3b-5c7d-8e9f-0a1b2c3d4e5f")

_CANON = {name.lower(): name for name in ArchiType.__members__}


def canon(raw: str) -> str:
    key = str(raw).strip().replace("_", "").replace("-", "").lower()
    try:
        return _CANON[key]
    except KeyError:
        raise SystemExit(f"error: {raw!r} is not an ArchiMate 3.2 concept name (pyArchimate.ArchiType)") from None


def det_id(*parts: str) -> str:
    return "id-" + uuid.uuid5(NS, "|".join(parts)).hex


def load(name: str, optional: bool = False) -> list[dict]:
    path = HERE / name
    if optional and not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or []
    if not isinstance(data, list):
        raise SystemExit(f"error: {name} must be a YAML list")
    return data


def add_elements(m: Model, elements: list[dict], errors: list[str]) -> dict[str, object]:
    by_id: dict[str, object] = {}
    for e in elements:
        yid = e.get("id")
        if not yid or "type" not in e or "name" not in e:
            errors.append(f"element missing id/type/name: {e!r}")
            continue
        if yid in by_id:
            errors.append(f"duplicate element id: {yid}")
            continue
        el = m.add(
            concept_type=canon(e["type"]),
            name=e["name"],
            desc=e.get("desc"),
            uuid=det_id(yid),
        )
        for k, v in (e.get("props") or {}).items():
            el.prop(str(k), str(v))
        by_id[yid] = el
    return by_id


def add_relationships(m: Model, rels: list[dict], by_id: dict[str, object], errors: list[str]) -> None:
    for r in rels:
        if "type" not in r or "source" not in r or "target" not in r:
            errors.append(f"relationship missing type/source/target: {r!r}")
            continue
        s, t = by_id.get(r["source"]), by_id.get(r["target"])
        if s is None or t is None:
            missing = r["source"] if s is None else r["target"]
            errors.append(f"relationship references unknown id {missing!r}: {r!r}")
            continue
        props = dict(r.get("props") or {})
        access = props.pop("access_type", None)
        rel = m.add_relationship(
            rel_type=canon(r["type"]),
            source=s,
            target=t,
            name=r.get("label"),
            access_type=access,
            uuid=det_id(r["source"], r["type"], r["target"], r.get("label", "")),
        )
        for k, v in props.items():
            rel.prop(str(k), str(v))


def add_views(m: Model, views: list[dict], elements: list[dict], by_id: dict[str, object], errors: list[str]) -> None:
    """Minimal view scoping for the diagram-archimate skill: a view lists
    `members` (element ids) and/or `include_types` (every element of those
    ArchiMate types). The richer view schema is still deferred."""
    for v in views:
        if "id" not in v or "name" not in v:
            errors.append(f"view missing id/name: {v!r}")
            continue
        want = set(v.get("members") or [])
        types = {canon(t) for t in (v.get("include_types") or [])}
        view: Any = m.get_or_create_view(v["name"], create_view=True)
        for e in elements:
            if e["id"] in want or (types and canon(e["type"]) in types):
                view.add(ref=by_id[e["id"]])
        missing = [mid for mid in want if mid not in by_id]
        if missing:
            errors.append(f"view {v['id']} references unknown ids: {missing}")


def main() -> int:
    m = Model("frictionless-architect")
    errors: list[str] = []

    elements = load("elements.yaml")
    by_id = add_elements(m, elements, errors)
    add_relationships(m, load("relationships.yaml"), by_id, errors)
    add_views(m, load("views.yaml", optional=True), elements, by_id, errors)

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
