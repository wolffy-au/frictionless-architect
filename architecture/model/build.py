#!/usr/bin/env python3
"""Build the Frictionless Architecture Platform ArchiMate model from YAML.

    poetry run python architecture/model/build.py

``architecture/model/elements.yaml`` + ``relationships.yaml`` are the single
source of truth for first-party content; each dir under ``third_party/`` (the
IT4IT 3.0 value-stream skeleton, ADR-0029) contributes its own
``elements.yaml`` / ``relationships.yaml`` in the same schema, merged in
alongside the first-party ones before this script projects the combined model
into ``frictionless-architect.xml`` (Open Group Exchange Format) via
pyArchimate, then runs the ``model-archimate`` validator over the result.
Every diagram (``*.puml`` / ``*.svg``) is in turn a projection of that XML —
regenerate them with the ``diagram-c4`` / ``diagram-archimate`` skills after
running this.

Schema (see ``architecture/model/README.md``):

* element:  ``type`` (bare ArchiMate 3.2 concept, case-insensitive) / ``id``
  (stable) / ``name`` / ``desc`` (optional) / ``props`` (optional str->str)
* relationship: ``type`` / ``source`` / ``target`` / ``label`` (optional) /
  ``props`` (optional; ``access_type`` for Access, ``c4-label`` overrides
  ``label`` in the C4 projection only)
* view: ``id`` / ``name`` / ``members`` (element ids) and/or ``include_types``
  / ``viewpoint`` (optional standard-viewpoint slug; see the model-archimate
  skill's ``reference/archi-viewpoints.xml`` — a declared viewpoint is enforced)

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
SKILL_SCRIPTS = HERE.parents[1] / ".claude/skills/model-archimate/scripts"
VALIDATOR = SKILL_SCRIPTS / "validate.py"
# Vendored reference models (ADR-0029): each is loaded alongside the
# first-party elements.yaml/relationships.yaml and merged into the same
# det_id()/NS pass below — their own id prefix (e.g. `it4it-`) is what keeps
# the merged id space unique, not any separate reconciliation step.
THIRD_PARTY = HERE.parents[1] / "third_party"
VENDORED_MODELS = [THIRD_PARTY / "it4it"]

# The model-archimate skill owns the standard-viewpoint reference and the
# conformance check a view is held to when it declares `viewpoint:`.
sys.path.insert(0, str(SKILL_SCRIPTS))
from viewpoints import UNRESTRICTED, check_conformance, get_viewpoint, known_slugs  # noqa: E402

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


def load_path(path: Path, errors: list[str], optional: bool = False) -> list[dict[str, Any]]:
    if optional and not path.exists():
        return []
    if not path.exists():
        errors.append(f"{path} is missing")
        return []
    data = yaml.safe_load(path.read_text()) or []
    if not isinstance(data, list):
        errors.append(f"{path} must be a YAML list")
        return []
    return data


def load(name: str, errors: list[str], optional: bool = False) -> list[dict[str, Any]]:
    return load_path(HERE / name, errors, optional)


def load_vendored(filename: str, errors: list[str]) -> list[dict[str, Any]]:
    """Load `filename` from every vendored model dir (ADR-0029). A missing
    submodule checkout (never initialized) is silently skipped, same as any
    other optional input — `git submodule update --init` fixes it."""
    merged: list[dict[str, Any]] = []
    for model_dir in VENDORED_MODELS:
        merged += load_path(model_dir / filename, errors, optional=True)
    return merged


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
        assert isinstance(el, Element)  # ct is never ArchiType.View here
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


def _view_element_ids(v: dict[str, Any], elements: list[dict[str, Any]], types_by_id: dict[str, str]) -> set[str]:
    """Element ids in scope for a view — same members/include_types rule as `add_views`."""
    want = set(v.get("members") or [])
    types = {
        _CANON.get(str(t).strip().replace("_", "").replace("-", "").lower()) for t in (v.get("include_types") or [])
    }
    return {e["id"] for e in elements if e["id"] in want or (types and types_by_id.get(e["id"]) in types)}


def _check_driver_bypasses_assessment(
    elements: list[dict[str, Any]], rels: list[dict[str, Any]], types_by_id: dict[str, str], errors: list[str]
) -> None:
    """A Driver analysed into an Assessment must route every other downstream
    influence through that Assessment, not around it — otherwise the Goal (or
    a Requirement) gets two inconsistent levels of justification for the same
    Driver: one evidenced, one not."""
    for e in elements:
        if types_by_id.get(e["id"]) != "Driver":
            continue
        driver = e["id"]
        outgoing = [r for r in rels if r["source"] == driver]
        assessments = {r["target"] for r in outgoing if types_by_id.get(r["target"]) == "Assessment"}
        if not assessments:
            continue
        for r in outgoing:
            if r["target"] not in assessments:
                errors.append(
                    f"driver {driver!r} has a {r['type']} relationship straight to {r['target']!r}, "
                    f"bypassing its own Assessment ({', '.join(sorted(assessments))}) — "
                    "re-source it from the Assessment instead"
                )


def _check_derived_goal_edges(
    elements: list[dict[str, Any]],
    rels: list[dict[str, Any]],
    views: list[dict[str, Any]],
    types_by_id: dict[str, str],
) -> list[str]:
    """A direct `A -> Goal` relationship that is also reachable as
    `A -> B -> Goal` is a candidate for removal as derived — *unless* some
    view holds both A and the Goal without B in scope, in which case the
    direct edge is the only way that view can show the connection at all,
    and it stays."""
    warnings: list[str] = []
    targets_of: dict[str, set[str]] = {}
    for r in rels:
        targets_of.setdefault(r["source"], set()).add(r["target"])

    view_scopes = {v["id"]: _view_element_ids(v, elements, types_by_id) for v in views if "id" in v}
    for r in rels:
        a, t = r["source"], r["target"]
        if types_by_id.get(t) != "Goal":
            continue
        for b in targets_of.get(a, ()):
            if b in (a, t) or t not in targets_of.get(b, ()):
                continue
            load_bearing = [vid for vid, ids in view_scopes.items() if a in ids and t in ids and b not in ids]
            if load_bearing:
                warnings.append(
                    f"note: {a!r} -> {t!r} is also reachable via {b!r}, but views "
                    f"{load_bearing} show {a!r}/{t!r} without {b!r} in scope — keeping it"
                )
            else:
                warnings.append(
                    f"warning: {a!r} -> {t!r} ({r['type']}) looks derived — already reachable via "
                    f"{a!r} -> {b!r} -> {t!r}, and no view needs the direct edge; consider removing it"
                )
    return warnings


def check_motivation_conventions(
    elements: list[dict[str, Any]],
    rels: list[dict[str, Any]],
    views: list[dict[str, Any]],
    types_by_id: dict[str, str],
    errors: list[str],
) -> list[str]:
    """Project-specific motivation-layer conventions pyArchimate's metamodel gate
    doesn't (and shouldn't) know about — both learned the hard way from earlier
    modelling passes on this file. See `_check_driver_bypasses_assessment`
    (hard error) and `_check_derived_goal_edges` (soft warning; never blocks
    the build)."""
    _check_driver_bypasses_assessment(elements, rels, types_by_id, errors)
    return _check_derived_goal_edges(elements, rels, views, types_by_id)


def check_view_viewpoint(v: dict[str, Any], el_types: set[str], rel_types: set[str], errors: list[str]) -> None:
    """Hold a view that declares `viewpoint:` to that standard viewpoint's allow lists."""
    slug = v.get("viewpoint")
    if not slug or slug == UNRESTRICTED:
        return
    vp = get_viewpoint(slug)
    if vp is None:
        errors.append(f"view {v['id']}: unknown viewpoint {slug!r} (known: {', '.join(known_slugs())})")
        return
    for msg in check_conformance(vp, el_types, rel_types):
        errors.append(f"view {v['id']} ({slug} viewpoint): {msg}")


def _compile_exclude_patterns(v: dict[str, Any], errors: list[str]) -> list[dict[str, str | None]]:
    """Compile a view's `exclude:` entries (see `add_views`) into matchers."""
    patterns: list[dict[str, str | None]] = []
    for ex in v.get("exclude") or []:
        ctx = f"view {v['id']} exclude"
        patterns.append(
            {
                "type": canon(ex["type"], errors, ctx) if "type" in ex else None,
                "source_type": canon(ex["source_type"], errors, ctx) if "source_type" in ex else None,
                "target_type": canon(ex["target_type"], errors, ctx) if "target_type" in ex else None,
                "source": ex.get("source"),
                "target": ex.get("target"),
            }
        )
    return patterns


def _relationship_excluded(
    rel: Any,
    patterns: list[dict[str, str | None]],
    uuid_to_id: dict[str, str],
    types_by_id: dict[str, str],
) -> bool:
    sid = uuid_to_id.get(rel.source.uuid)
    tid = uuid_to_id.get(rel.target.uuid)
    stype = types_by_id.get(sid) if sid else None
    ttype = types_by_id.get(tid) if tid else None
    for p in patterns:
        if p["type"] and p["type"] != rel.type:
            continue
        if p["source_type"] and p["source_type"] != stype:
            continue
        if p["target_type"] and p["target_type"] != ttype:
            continue
        if p["source"] and p["source"] != sid:
            continue
        if p["target"] and p["target"] != tid:
            continue
        return True
    return False


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
    and ignore these coordinates).

    A view may also declare `viewpoint: <slug>` (see the model-archimate
    skill's `reference/archi-viewpoints.xml`). When it does — and the slug is
    not `custom` — every element type placed on the view is held to that
    standard ArchiMate viewpoint's allow-set, and a stray concept fails the
    build. The declaration is not written into the generated XML (pyArchimate
    cannot round-trip view-level properties in the pinned version);
    `views.yaml` stays the source of truth for it.

    A view may also declare `exclude:` — a list of type+pair patterns for
    relationships that would otherwise render (both endpoints in scope) but
    are incidental to this view's own narrated story rather than core to it
    (GH #20: the same capability-to-capability Serving mesh was leaking
    identically into every view that happens to include ≥2 capabilities,
    even though only the Capability Map view is actually about it). Each
    entry may give any of `type` / `source_type` / `target_type` (ArchiMate
    concept names) and/or `source` / `target` (specific element ids); a
    relationship is suppressed when every key given in an entry matches.
    Omitted keys are wildcards, so `{type: Serving, source_type: Capability,
    target_type: Capability}` drops every capability-to-capability Serving
    edge on that view regardless of which specific capabilities are
    involved.

    The richer view schema (auto-membership rules) is still deferred."""
    uuid_to_id = {el.uuid: eid for eid, el in by_id.items()}
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
        view_el_types: set[str] = set()
        for e in elements:
            selected = e["id"] in want or (types and types_by_id.get(e["id"]) in types)
            if selected and e["id"] in by_id:
                el = by_id[e["id"]]
                view.add(ref=el, uuid=det_id(v["id"], "node", el.uuid))
                on_view.add(el.uuid)
                view_el_types.add(types_by_id[e["id"]])
        exclude_patterns = _compile_exclude_patterns(v, errors)
        view_rel_types: set[str] = set()
        for rel in m.relationships:
            if (
                rel.source.uuid in on_view
                and rel.target.uuid in on_view
                and not _relationship_excluded(rel, exclude_patterns, uuid_to_id, types_by_id)
            ):
                view.add_connection(ref=rel, uuid=det_id(v["id"], "conn", rel.uuid))
                view_rel_types.add(rel.type)
        missing = [mid for mid in want if mid not in by_id]
        if missing:
            errors.append(f"view {v['id']} references unknown ids: {missing}")
            continue
        check_view_viewpoint(v, view_el_types, view_rel_types, errors)
        # Grid layout is deterministic (layer-ordered row-major placement);
        # apply_format then applies the ArchiMate per-category node sizes.
        cfg = LayoutConfig(alignment="grid", layer_direction="vertical")
        for res in (apply_layout(view, cfg), apply_format(view, cfg)):
            if not res.success:
                errors.append(f"view {v['id']} {res.algorithm_used} failed: {res.error_message}")


def main() -> int:
    m = Model("frictionless-architect")
    errors: list[str] = []

    elements = load("elements.yaml", errors) + load_vendored("elements.yaml", errors)
    by_id, types_by_id = add_elements(m, elements, errors)
    rels = load("relationships.yaml", errors) + load_vendored("relationships.yaml", errors)
    add_relationships(m, rels, by_id, errors)
    views = load("views.yaml", errors, optional=True) + load_vendored("views.yaml", errors)
    add_views(m, views, elements, by_id, types_by_id, errors)
    motivation_warnings = check_motivation_conventions(elements, rels, views, types_by_id, errors)

    if errors:
        for msg in errors:
            sys.stderr.write(f"error: {msg}\n")
        return 2

    for msg in motivation_warnings:
        print(msg)

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
