"""Load, merge, validate and write the Frictionless Architecture Platform ArchiMate model.

Ported from `architecture/model/build.py` (ADR-0037, R2) -- this is now the one load/
merge/validate/write path, used by both this package's CLI `build` command and the
chat router's in-memory validate-before-write (R9). Root's `build.py` is now a thin
wrapper shelling into the CLI (`python -m modelling_specification.cli build`).

``architecture/model/elements.yaml`` + ``relationships.yaml`` are the single source of
truth for first-party content; each dir under ``third_party/`` (the IT4IT 3.0
value-stream skeleton, ADR-0029) contributes its own ``elements.yaml`` /
``relationships.yaml`` in the same schema, merged in alongside the first-party ones
before this module projects the combined model into ``frictionless-architect.xml``
(Open Group Exchange Format) via pyArchimate, then validates the result.

Schema (see ``architecture/model/README.md``):

* element:  ``type`` (bare ArchiMate 3.2 concept, case-insensitive) / ``id``
  (stable) / ``name`` / ``desc`` (optional) / ``props`` (optional str->str)
* relationship: ``type`` / ``source`` / ``target`` / ``label`` (optional) /
  ``props`` (optional; ``access_type`` for Access, ``c4-label`` overrides
  ``label`` in the C4 projection only)
* view: ``id`` / ``name`` / ``members`` (element ids) and/or ``include_types``
  (optionally narrowed by ``exclude_elements``) / ``viewpoint`` (optional
  standard-viewpoint slug; see the model-archimate skill's
  ``reference/archi-viewpoints.xml`` -- a declared viewpoint is enforced)

``id`` values are hashed to deterministic UUIDs so regeneration does not churn
identifiers (and therefore diagrams).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

import yaml
from pyArchimate import ArchiType, Element, Model, check_valid_relationship
from pyArchimate.view.layout import LayoutConfig, apply_format, apply_layout

# This file lives at
# platform/packages/modelling-specification/src/modelling_specification/model_io.py --
# five parents up is the repo root, anchoring every path below independently of the
# process's current working directory (the CLI may run with cwd=platform/).
REPO_ROOT = Path(__file__).resolve().parents[5]
HERE = REPO_ROOT / "architecture" / "model"
OUT = HERE / "frictionless-architect.xml"
SKILL_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "model-archimate" / "scripts"
# Vendored reference models (ADR-0029): each is loaded alongside the
# first-party elements.yaml/relationships.yaml and merged into the same
# det_id()/NS pass below -- their own id prefix (e.g. `it4it-`) is what keeps
# the merged id space unique, not any separate reconciliation step.
THIRD_PARTY = REPO_ROOT / "third_party"
# Ownership scope: every element carries a `context` (a bounded context, in DDD
# terms). First-party elements default to this one; a layer's elements default
# to the layer directory's name (`it4it`, `gh-roadmap`). An explicit `context:`
# on an element wins. Views sweep `include_types` only within their `context:`.
DEFAULT_CONTEXT = "platform"
ELEMENTS_FILENAME = "elements.yaml"
RELATIONSHIPS_FILENAME = "relationships.yaml"
VIEWS_FILENAME = "views.yaml"
VENDORED_MODELS = [THIRD_PARTY / "it4it"]
# Every optional layer merged into the same pass: the vendored models plus the
# generated GitHub roadmap (GH #95, import_gh_roadmap.py), whose ids are
# prefixed by ArchiMate type (plat-, del-, wp-) rather than by source system.
MODEL_LAYERS = [*VENDORED_MODELS, HERE / "gh-roadmap"]
LAYER_CONTEXTS = {p.name for p in MODEL_LAYERS}

# The model-archimate skill owns the standard-viewpoint reference and the
# conformance check a view is held to when it declares `viewpoint:`.
sys.path.insert(0, str(SKILL_SCRIPTS))
from viewpoints import UNRESTRICTED, check_conformance, get_viewpoint, known_slugs  # noqa: E402

# Fixed namespace -- do not change; it anchors every generated identifier.
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
    """Derive a stable identifier from the given parts, so regeneration never churns ids.

    Args:
        *parts: The strings that identify the object (hashed together).

    Returns:
        ``"id-"`` followed by a deterministic UUID5 hex digest.
    """
    return "id-" + uuid.uuid5(NS, "|".join(parts)).hex


def load_path(path: Path, errors: list[str], optional: bool = False) -> list[dict[str, Any]]:
    """Load a model YAML file that must hold a list.

    Args:
        path: The YAML file.
        errors: Collects problems found; this function reports instead of raising.
        optional: If true, a missing file yields an empty list without an error.

    Returns:
        The list of entries, or ``[]`` when the file is missing or malformed.
    """
    if optional and not path.exists():
        return []
    if not path.exists():
        errors.append(f"{path} is missing")
        return []
    data = yaml.safe_load(path.read_text()) or []
    if not isinstance(data, list):
        errors.append(f"{path} must be a YAML list")
        return []
    _check_null_keys(data, str(path), errors)
    return data


def _null_key_context(node: dict[str, Any], where: str) -> str:
    """`where: id` (or `where: src->tgt`) for an error label, if `node` carries an id
    or both relationship endpoints -- else just `where` unchanged."""
    ident = node.get("id") or (f"{node['source']}->{node['target']}" if "source" in node and "target" in node else None)
    return f"{where}: {ident}" if ident else where


def _check_null_keys(node: Any, where: str, errors: list[str]) -> None:
    """Flag any mapping key whose value is null.

    In a flow-style entry (`- {id: x, desc: a, b}`) an unquoted comma ends the
    value, so YAML silently truncates it and turns the tail into a stray key
    with a null value. No model field is legitimately null, so treat every one
    as that truncation and report it rather than build from the cut-short text.
    """
    if isinstance(node, dict):
        ctx = _null_key_context(node, where)
        for key, value in node.items():
            if value is None:
                errors.append(
                    f"{ctx}: key {key!r} has no value — likely an unquoted comma truncating a flow-style value; quote it"
                )
            else:
                _check_null_keys(value, ctx, errors)
    elif isinstance(node, list):
        for item in node:
            _check_null_keys(item, where, errors)


def load(name: str, errors: list[str], optional: bool = False) -> list[dict[str, Any]]:
    """Load a model YAML file from the model directory by name.

    Args:
        name: File name relative to the model directory (for example ``elements.yaml``).
        errors: Collects problems found.
        optional: If true, a missing file is not an error.

    Returns:
        The entries, as for ``load_path``.
    """
    return load_path(HERE / name, errors, optional)


def load_layers(filename: str, errors: list[str]) -> list[dict[str, Any]]:
    """Load `filename` from every optional model layer: the vendored models
    (ADR-0029) and the generated gh-roadmap dir. A missing dir (a submodule never
    initialized, or the importer never run) is silently skipped, same as any
    other optional input -- `git submodule update --init` fixes the former."""
    merged: list[dict[str, Any]] = []
    for model_dir in MODEL_LAYERS:
        merged += load_path(model_dir / filename, errors, optional=True)
    return merged


def tag_contexts(elements: list[dict[str, Any]], context: str) -> list[dict[str, Any]]:
    """Give every element without an explicit `context:` the default `context`."""
    for e in elements:
        e.setdefault("context", context)
    return elements


def load_layer_elements(errors: list[str]) -> list[dict[str, Any]]:
    """`elements.yaml` from every optional layer, each tagged with its layer's context."""
    merged: list[dict[str, Any]] = []
    for model_dir in MODEL_LAYERS:
        loaded = load_path(model_dir / ELEMENTS_FILENAME, errors, optional=True)
        merged += tag_contexts(loaded, model_dir.name)
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
        el.prop("context", str(e.get("context", DEFAULT_CONTEXT)))
        by_id[yid] = el
        types[yid] = ct
    return by_id, types


def add_relationships(m: Model, rels: list[dict[str, Any]], by_id: dict[str, Element], errors: list[str]) -> None:
    """Add every valid relationship to the model.

    Args:
        m: The model being built.
        rels: Relationship entries (``type`` / ``source`` / ``target`` / ``label?`` / ``props?``).
        by_id: Elements already added, keyed by YAML id.
        errors: Collects entries that are incomplete, reference unknown ids or have an
            unrecognised type; those are skipped.
    """
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


def view_element_ids(v: dict[str, Any], elements: list[dict[str, Any]], types_by_id: dict[str, str]) -> set[str]:
    """Element ids in scope for a view -- same members/include_types/exclude_elements
    rule as `add_views`. Public: `rendering.py`'s `resolve_view_request` (FR-016)
    reuses this to resolve an `object_id` named directly, rather than re-deriving
    "what's on a view" with a narrower members-only rule."""
    want = set(v.get("members") or [])
    types = {
        _CANON.get(str(t).strip().replace("_", "").replace("-", "").lower()) for t in (v.get("include_types") or [])
    }
    scope = _view_scope(v, {e.get("context", DEFAULT_CONTEXT) for e in elements}, [])
    exclude_patterns = _compile_exclude_element_patterns(v, [])
    return {
        e["id"]
        for e in elements
        if (
            e["id"] in want
            or (types and types_by_id.get(e["id"]) in types and e.get("context", DEFAULT_CONTEXT) in scope)
        )
        and not _element_excluded(e["id"], exclude_patterns, types_by_id)
    }


def _check_derived_goal_edges(
    elements: list[dict[str, Any]],
    rels: list[dict[str, Any]],
    views: list[dict[str, Any]],
    types_by_id: dict[str, str],
) -> list[str]:
    """A direct `A -> Goal` relationship that is also reachable as
    `A -> B -> Goal` is a candidate for removal as derived -- *unless* some
    view holds both A and the Goal without B in scope, in which case the
    direct edge is the only way that view can show the connection at all,
    and it stays.

    Overlaps on purpose with the skill's `check_derived.py` (which also
    flags `A -> Goal` as a duplicate of `A -> B -> Goal`, via
    `pyArchimate.derivation`'s formal DR2/DR3/DR5/DR7/DR8 rules across all
    seven "certain" relationship types, not just Goal-targeted ones): that
    script is a whole-model, run-by-hand/CI audit with a static exception
    table (`SERVING_EXCEPTIONS`), while this is in the hot build/validate
    path and already knows the one exemption `check_derived.py` has to
    hand-list per case -- a direct edge a *view* still needs is load-bearing,
    so it is kept automatically here instead of requiring a new
    `SERVING_EXCEPTIONS` entry there. Neither replaces the other: this one
    only covers Goal-targeted edges and only the two kinds (Realization,
    Influence) this layer uses; `check_derived.py` is the generic sweep
    across every relationship type and both Application/Strategy and
    Motivation layers."""
    warnings: list[str] = []
    targets_of: dict[str, set[str]] = {}
    for r in rels:
        targets_of.setdefault(r["source"], set()).add(r["target"])

    view_scopes = {v["id"]: view_element_ids(v, elements, types_by_id) for v in views if "id" in v}
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
    rules: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Apply configured whole-model relationship conventions, the derived-edge note,
    and the GH #129 tag-coverage warning -- despite the name, not motivation-only."""
    from modelling_specification.validation import conventions

    if rules is None:
        try:
            rules = conventions.load_rules()
        except conventions.ConventionRuleError as exc:
            errors.append(str(exc))
            rules = []
    errors.extend(conventions.check_relationships(elements, rels, types_by_id, rules))
    return _check_derived_goal_edges(elements, rels, views, types_by_id) + check_context_coverage()


# GH #129 tag-coverage check, scope. Motivation/Strategy layers (Driver,
# Stakeholder, Goal, Outcome, Requirement, Capability's shared cases, etc.),
# BusinessRole and ValueStream are cross-cutting by design and excluded from
# this check entirely -- only the layers #129 calls out (Application,
# Technology, BusinessObject) are checked, since those are where an element
# usually belongs to exactly one package.
_CONTEXT_COVERAGE_TYPES = {
    "ApplicationComponent",
    "ApplicationFunction",
    "ApplicationInterface",
    "DataObject",
    "BusinessObject",
    "Grouping",
    "Node",
    "SystemSoftware",
    "TechnologyProcess",
    "TechnologyFunction",
    "Artifact",
}
# Elements of the types above that are genuinely shared across every package
# (a shared kernel, host/portal, or something entirely outside the platform
# Grouping) rather than owned by one -- reviewed and accepted here, the same
# "never silently" posture as `check_derived.py`'s SERVING_EXCEPTIONS: an
# addition to this set is a conscious decision, not a default.
_SHARED_CONTEXT_EXEMPTIONS = {
    "sys-platform",  # the platform Grouping itself
    "sub-portal",  # host package, not one of the six subsystems (ADR-0020)
    "if-portal-ui",  # the portal's own shared entry point
    "art-flat-src",  # legacy pre-migration flat src/, not one package
    "art-pkg-portal",  # host package Artifact, not one of the six subsystems
    # Shared stores -- the "shared kernel" DataObjects multiple subsystems read/write.
    "store-oscal",
    "store-patterns",
    "store-akg",
    "store-frameworks",
    "store-ledger",
    # External systems -- outside the platform Grouping entirely.
    "ext-scm",
    "ext-cicd",
    "ext-cloud",
    "ext-itsm",
    "ext-trestle",
    "ext-llm",
    "ext-rfp",
    "ext-collab",
    "fn-scm-versioning",
    "fn-scm-change-review",
    "fn-cicd-build",
    "fn-cicd-deploy",
    "fn-itsm-backlog",
    "fn-itsm-change",
    # Cross-cutting pipeline artefacts with no single owning subsystem.
    "do-target-architecture",
    "do-release-candidate",
    "do-gate-decision",
    "bo-release-gate-decision",
    "bo-target-state-architecture",
    "bo-transition-state-architecture",
    # Shared infra -- the common deployment target/runtime/CI, not one package's.
    "node-ci-runner",
    "node-app-server",
    "node-hosted-cluster",
    "sw-pytest",
    "sw-uvicorn-fastapi",
    # Cross-subsystem composition, owned by no single subsystem (ADR-0020).
    "techfn-role-journey-composition",
}


def check_context_coverage() -> list[str]:
    """Warn about a first-party Application/Technology/BusinessObject element with
    no explicit `context:` and no recorded exemption (GH #129 tag-coverage check).

    Re-reads `elements.yaml` directly rather than taking `load_all_elements()`'s
    result: that result has already run through `tag_contexts()`, whose
    `setdefault` fills in `context` for every element in place -- by then an
    originally-untagged element is indistinguishable from one explicitly tagged
    `platform`. Only first-party `elements.yaml` is in scope; a vendored layer
    (`it4it-*`, `gh-roadmap`) already carries its own layer-name context from its
    own `tag_contexts()` pass, not a first-party package decision."""
    warnings: list[str] = []
    for element in load(ELEMENTS_FILENAME, []):
        element_id = str(element.get("id", ""))
        if element.get("type") not in _CONTEXT_COVERAGE_TYPES:
            continue
        if "context" in element or element_id in _SHARED_CONTEXT_EXEMPTIONS:
            continue
        warnings.append(
            f"warning: {element['type']} {element_id!r} has no explicit context and no "
            f"recorded shared-context exemption — defaults to {DEFAULT_CONTEXT!r}"
        )
    return warnings


def _context_display_name(context: str, elements: list[dict[str, Any]]) -> str:
    """The context's subsystem `ApplicationComponent`'s own `name` (every current
    context has exactly one `sub-*` element carrying it) -- falls back to a
    title-cased slug for a context with no such component."""
    for element in elements:
        if element.get("context") == context and str(element.get("id", "")).startswith("sub-"):
            name = element.get("name")
            if name:
                return str(name)
    return context.replace("-", " ").title()


def generate_context_groupings(
    elements: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive one ArchiMate `Grouping` per bounded context (`grp-ctx-<context>`,
    GH #129 step 2) plus an Aggregation relationship from it to each of its members.
    Not hand-authored: `context:` tags (already on disk, GH #129 step 1) are the only
    input. `elements` must not already carry generated Groupings -- call this once on
    the raw, pre-generation element list, never on its own output.

    `DEFAULT_CONTEXT` ("platform", the shared-kernel fallback) and `LAYER_CONTEXTS`
    (vendored layers, keyed by directory not by package) get no Grouping, matching
    `_view_scope`'s existing treatment of `platform` as the whole-model default scope
    rather than a real bounded context. A generated Grouping itself carries no
    `context` -- it is a cross-cutting device describing a boundary, not a member
    inside one, and leaving it unset also keeps this function idempotent-safe: were
    its output ever fed back in, an untagged element defaults to `platform` and is
    skipped rather than re-aggregating the Grouping under itself."""
    members_by_context: dict[str, list[str]] = {}
    for element in elements:
        element_id = element.get("id")
        context = element.get("context", DEFAULT_CONTEXT)
        if not element_id or context == DEFAULT_CONTEXT or context in LAYER_CONTEXTS:
            continue
        members_by_context.setdefault(context, []).append(element_id)

    groupings: list[dict[str, Any]] = []
    aggregations: list[dict[str, Any]] = []
    for context, member_ids in sorted(members_by_context.items()):
        grouping_id = f"grp-ctx-{context}"
        groupings.append(
            {
                "type": "Grouping",
                "id": grouping_id,
                "name": _context_display_name(context, elements),
                "desc": (
                    f"Generated bounded-context boundary for every element tagged "
                    f"`context: {context}` (GH #129) -- not hand-authored."
                ),
                "props": {"generated": "true"},
            }
        )
        for member_id in member_ids:
            aggregations.append({"type": "Aggregation", "source": grouping_id, "target": member_id})
    return groupings, aggregations


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


def _pattern_matches_relationship(
    p: dict[str, str | None], rel_type: str, stype: str | None, ttype: str | None, sid: str | None, tid: str | None
) -> bool:
    """Whether every key an exclude_elements pattern gives (others are wildcards)
    matches this relationship's type, endpoint types and endpoint ids."""
    return (
        (not p["type"] or p["type"] == rel_type)
        and (not p["source_type"] or p["source_type"] == stype)
        and (not p["target_type"] or p["target_type"] == ttype)
        and (not p["source"] or p["source"] == sid)
        and (not p["target"] or p["target"] == tid)
    )


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
    return any(_pattern_matches_relationship(p, rel.type, stype, ttype, sid, tid) for p in patterns)


def _view_scope(v: dict[str, Any], known_contexts: set[str], errors: list[str]) -> set[str]:
    """The contexts a view's `include_types` sweep draws from (default `platform`).

    `platform` stands for the whole first-party family — `platform` itself (the
    shared kernel) plus every package context — i.e. every context that is not
    a layer's."""
    raw = v.get("context") or [DEFAULT_CONTEXT]
    scope = {raw} if isinstance(raw, str) else set(raw)
    if unknown := scope - known_contexts:
        errors.append(f"view {v['id']} context names unknown context(s): {sorted(unknown)}")
    if DEFAULT_CONTEXT in scope:
        scope |= known_contexts - LAYER_CONTEXTS
    return scope


def _compile_exclude_element_patterns(v: dict[str, Any], errors: list[str]) -> list[dict[str, str | None]]:
    """Compile a view's `exclude_elements:` entries (see `add_views`) into matchers."""
    patterns: list[dict[str, str | None]] = []
    for ex in v.get("exclude_elements") or []:
        ctx = f"view {v['id']} exclude_elements"
        patterns.append(
            {
                "type": canon(ex["type"], errors, ctx) if "type" in ex else None,
                "id": ex.get("id"),
                "id_prefix": ex.get("id_prefix"),
            }
        )
    return patterns


def _element_excluded(eid: str, patterns: list[dict[str, str | None]], types_by_id: dict[str, str]) -> bool:
    for p in patterns:
        if p["type"] and p["type"] != types_by_id.get(eid):
            continue
        if p["id"] and p["id"] != eid:
            continue
        if p["id_prefix"] and not eid.startswith(p["id_prefix"]):
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
    ArchiMate types). This adds a node for every matching element and a
    connection for every model relationship whose *both* endpoints are on the
    view -- the same in-scope rule `model_to_puml.py` applies when rendering --
    then runs pyArchimate's grid auto-layout + format so the view is usable
    when opened directly in Archi (the diagram skills re-lay-out via PlantUML
    and ignore these coordinates).

    A view may also declare `viewpoint: <slug>` (see the model-archimate
    skill's `reference/archi-viewpoints.xml`). When it does -- and the slug is
    not `custom` -- every element type placed on the view is held to that
    standard ArchiMate viewpoint's allow-set, and a stray concept fails the
    build. The declaration is not written into the generated XML (pyArchimate
    cannot round-trip view-level properties in the pinned version);
    `views.yaml` stays the source of truth for it.

    A view may also declare `exclude:` -- a list of type+pair patterns for
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

    A view's `include_types` sweep only picks up elements whose `context` is in
    the view's `context:` (a name or list; default `[platform]`, which covers every
    first-party context). Explicit `members` are
    always honoured regardless of context, so a view that names elements from
    another context needs no scope entry for them.

    A view may also declare `exclude_elements:` -- a list of patterns that
    drop otherwise-selected elements (via `members` or `include_types`)
    before nodes/connections are built. Each entry may give `type`
    (ArchiMate concept name), `id` (a specific element id) and/or
    `id_prefix`; an element is excluded when every key given in an entry
    matches (omitted keys are wildcards). This lets a view use
    `include_types` for a type that is otherwise polluted by a vendored
    layer sharing the same ArchiMate type -- e.g. `third_party/it4it`
    contributes 42 Capability / 35 Outcome / 28 ValueStream elements, all
    `it4it-`-prefixed, so `{id_prefix: "it4it-"}` keeps those out of a
    first-party view without reverting to an explicit `members` allow-list
    that silently drops any new first-party element of that type until
    someone remembers to add it.

    The richer view schema (auto-membership rules) is still deferred."""
    uuid_to_id = {el.uuid: eid for eid, el in by_id.items()}
    known_contexts = {e.get("context", DEFAULT_CONTEXT) for e in elements}
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
        scope = _view_scope(v, known_contexts, errors)
        exclude_element_patterns = _compile_exclude_element_patterns(v, errors)
        on_view, view_el_types = _select_view_elements(
            view, elements, by_id, types_by_id, want, types, scope, exclude_element_patterns, v["id"]
        )
        exclude_patterns = _compile_exclude_patterns(v, errors)
        view_rel_types = _connect_view_relationships(
            view, m, on_view, exclude_patterns, uuid_to_id, types_by_id, v["id"]
        )
        missing = [mid for mid in want if mid not in by_id]
        if missing:
            errors.append(f"view {v['id']} references unknown ids: {missing}")
            continue
        check_view_viewpoint(v, view_el_types, view_rel_types, errors)
        _apply_view_layout(view, v, errors)


def _select_view_elements(
    view: Any,
    elements: list[dict[str, Any]],
    by_id: dict[str, Element],
    types_by_id: dict[str, str],
    want: set[str],
    types: set[str],
    scope: set[str],
    exclude_element_patterns: list[dict[str, Any]],
    view_id: str,
) -> tuple[set[str], set[str]]:
    """Add a node to `view` for every element in scope (via `want`/`types`, less
    `exclude_element_patterns`); returns the node uuids and ArchiMate types placed,
    for `add_views`'s relationship/viewpoint passes."""
    on_view: set[str] = set()  # element uuids with a node on this view
    view_el_types: set[str] = set()
    for e in elements:
        swept = bool(types) and types_by_id.get(e["id"]) in types and e.get("context", DEFAULT_CONTEXT) in scope
        selected = (e["id"] in want or swept) and not _element_excluded(e["id"], exclude_element_patterns, types_by_id)
        if selected and e["id"] in by_id:
            el = by_id[e["id"]]
            view.add(ref=el, uuid=det_id(view_id, "node", el.uuid))
            on_view.add(el.uuid)
            view_el_types.add(types_by_id[e["id"]])
    return on_view, view_el_types


def _connect_view_relationships(
    view: Any,
    m: Model,
    on_view: set[str],
    exclude_patterns: list[dict[str, Any]],
    uuid_to_id: dict[str, str],
    types_by_id: dict[str, str],
    view_id: str,
) -> set[str]:
    """Add a connection to `view` for every model relationship whose endpoints are
    both on it (less `exclude_patterns`); returns the ArchiMate relationship types
    connected, for `add_views`'s viewpoint check."""
    view_rel_types: set[str] = set()
    for rel in m.relationships:
        if (
            rel.source.uuid in on_view
            and rel.target.uuid in on_view
            and not _relationship_excluded(rel, exclude_patterns, uuid_to_id, types_by_id)
        ):
            view.add_connection(ref=rel, uuid=det_id(view_id, "conn", rel.uuid))
            view_rel_types.add(rel.type)
    return view_rel_types


def _apply_view_layout(view: Any, v: dict[str, Any], errors: list[str]) -> None:
    """Grid layout is deterministic (layer-ordered row-major placement);
    apply_format then applies the ArchiMate per-category node sizes."""
    cfg = LayoutConfig(alignment="grid", layer_direction="vertical")
    for res in (apply_layout(view, cfg), apply_format(view, cfg)):
        if not res.success:
            errors.append(f"view {v['id']} {res.algorithm_used} failed: {res.error_message}")


def load_all_elements(errors: list[str]) -> list[dict[str, Any]]:
    """First-party `elements.yaml` plus every layer's, each tagged with its context."""
    return tag_contexts(load(ELEMENTS_FILENAME, errors), DEFAULT_CONTEXT) + load_layer_elements(errors)


def load_all_views(errors: list[str]) -> list[dict[str, Any]]:
    """`views.yaml`, the generic `views-viewpoints.yaml`, and every layer's views."""
    return (
        load(VIEWS_FILENAME, errors, optional=True)
        + load("views-viewpoints.yaml", errors, optional=True)
        + load_layers(VIEWS_FILENAME, errors)
    )


def _assemble(
    name: str,
    elements: list[dict[str, Any]],
    rels: list[dict[str, Any]],
    views: list[dict[str, Any]],
    errors: list[str],
) -> tuple[Model | None, list[str], list[str]]:
    """Add `elements`/`rels`/`views` to a fresh `Model` named `name`, running the same
    checks `build_model()` always has. `errors` already carries any YAML-load errors
    the caller collected; this appends to it rather than starting fresh, so a load
    error and a structural one are both reported in one pass.

    Also generates and adds the GH #129 step 2 context Groupings + Aggregations
    (`generate_context_groupings`) -- `elements`/`rels` as passed in must not already
    carry them, since that would double-add. The generated pair is added only to the
    `Model`, not to what `check_motivation_conventions` below sees: those conventions
    are about first-party content, and a generated Grouping/Aggregation has no `desc`
    worth altitude-checking and no motivation-chain role."""
    groupings, aggregations = generate_context_groupings(elements)
    m = Model(name)
    by_id, types_by_id = add_elements(m, elements + groupings, errors)
    add_relationships(m, rels + aggregations, by_id, errors)
    seen_views: set[str] = set()
    for v in views:
        if (vid := v.get("id")) is None:
            continue  # add_views reports the missing id
        if vid in seen_views:
            errors.append(f"duplicate view id: {vid}")
        seen_views.add(vid)
    add_views(m, views, elements, by_id, types_by_id, errors)
    motivation_warnings = check_motivation_conventions(elements, rels, views, types_by_id, errors)
    if errors:
        return None, errors, motivation_warnings
    return m, errors, motivation_warnings


def build_model() -> tuple[Model | None, list[str], list[str]]:
    """Load every YAML layer and assemble the in-memory pyArchimate `Model`.

    Returns `(model, errors, motivation_warnings)`. `model` is `None` when
    `errors` is non-empty -- the caller never writes/validates a model built
    from invalid YAML."""
    errors: list[str] = []
    elements = load_all_elements(errors)
    rels = load(RELATIONSHIPS_FILENAME, errors) + load_layers(RELATIONSHIPS_FILENAME, errors)
    views = load_all_views(errors)
    return _assemble("frictionless-architect", elements, rels, views, errors)


def existing_element_ids() -> set[str]:
    """Every first-party + layer element id currently on disk -- used to de-duplicate
    an id the router synthesizes for a delta element the LLM left blank (data-model.md:
    "id absent until the LLM proposes one or validation assigns one")."""
    errors: list[str] = []
    elements = load_all_elements(errors)
    return {e["id"] for e in elements if e.get("id")}


def existing_elements_and_types() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """`(elements, types_by_id)` loaded once -- `rendering.py`'s `resolve_view_request`
    uses this with `view_element_ids` to resolve an `object_id` against every view in
    one pass, rather than reloading `elements.yaml` per view."""
    errors: list[str] = []
    elements = load_all_elements(errors)
    types_by_id: dict[str, str] = {}
    for e in elements:
        eid = e.get("id")
        canon_type = canon(str(e.get("type", "")), [], "existing element") if eid else None
        if eid and canon_type:
            types_by_id[eid] = canon_type
    return elements, types_by_id


def existing_element_types() -> dict[str, str]:
    """Every first-party + layer element id mapped to its canonical ArchiMate type --
    used by `patterns.py` to type-check a proposed relationship's endpoints without
    re-loading/parsing the YAML itself."""
    return existing_elements_and_types()[1]


_ELEMENT_FIELD_ORDER = ["type", "id", "name", "desc", "props"]
_RELATIONSHIP_FIELD_ORDER = ["type", "source", "target", "label", "props"]


def _append_yaml_flow_entries(path: Path, entries: list[dict[str, Any]], field_order: list[str]) -> None:
    """Append `entries` to `path` as single-line flow-style YAML, under a banner
    comment -- never a full `yaml.safe_dump` rewrite of the file, so none of its
    existing hand-authored comments/grouping/formatting are disturbed (plan.md: an
    applied delta is additive only, FR-001)."""
    lines = ["\n# --- Conversational authoring: applied via POST /authoring/.../decide (GH #108) ---\n"]
    for entry in entries:
        ordered = {k: entry[k] for k in field_order if entry.get(k) not in (None, {})}
        lines.append(f"- {yaml.safe_dump(ordered, default_flow_style=True, sort_keys=False, width=10**9).strip()}\n")
    with path.open("a") as f:
        f.writelines(lines)


def append_delta(elements: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> None:
    """Append an applied Candidate Delta's elements/relationships to `elements.yaml`/
    `relationships.yaml` (FR-001's apply step, R9) -- additive only; no existing entry
    is edited, retired or reordered (plan.md Model impact)."""
    if elements:
        _append_yaml_flow_entries(HERE / ELEMENTS_FILENAME, elements, _ELEMENT_FIELD_ORDER)
    if relationships:
        _append_yaml_flow_entries(HERE / RELATIONSHIPS_FILENAME, relationships, _RELATIONSHIP_FIELD_ORDER)


def merge_candidate(
    delta_elements: list[dict[str, Any]], delta_relationships: list[dict[str, Any]]
) -> tuple[Model | None, list[str], list[str]]:
    """Load the current YAML model from disk, merge a Candidate Delta's elements/
    relationships on top, and assemble+check the whole resulting in-memory model
    (FR-002, R9) -- never the delta in isolation, so a change that is valid on its
    own but breaks referential integrity elsewhere is also caught. Nothing is written
    to disk; the delta is additive only, same as `build_model()` otherwise."""
    errors: list[str] = []
    elements = load_all_elements(errors) + list(delta_elements)
    rels = (
        load(RELATIONSHIPS_FILENAME, errors) + load_layers(RELATIONSHIPS_FILENAME, errors) + list(delta_relationships)
    )
    views = load_all_views(errors)
    return _assemble("candidate-delta", elements, rels, views, errors)


def preview_model(
    delta_elements: list[dict[str, Any]], delta_relationships: list[dict[str, Any]], view: dict[str, Any]
) -> tuple[Model | None, list[str]]:
    """The model with a Candidate Delta merged in, for rendering `view` as it *would*
    look -- nothing is written. The delta's elements (marked "+") and both endpoints of
    its relationships are added to the view's members so a members-listed view shows
    them; `merge_candidate`'s own checks still apply."""
    errors: list[str] = []
    elements = load_all_elements(errors)
    marked = [{**e, "name": f"+ {e.get('name', e.get('id', ''))}"} for e in delta_elements]
    rels = (
        load(RELATIONSHIPS_FILENAME, errors) + load_layers(RELATIONSHIPS_FILENAME, errors) + list(delta_relationships)
    )
    shown = [e["id"] for e in delta_elements if e.get("id")]
    shown += [end for r in delta_relationships for end in (r.get("source"), r.get("target")) if end]
    views = load_all_views(errors)
    views = [
        {**v, "members": [*(v.get("members") or []), *shown]} if v.get("id") == view.get("id") else v for v in views
    ]
    model, errors, _warnings = _assemble("candidate-preview", elements + marked, rels, views, errors)
    return model, errors


def _load_model_for_validation(path_or_model: str | Path | Model) -> tuple[Model, str]:
    """The `Model` to validate plus its display label -- as-is if already loaded,
    else read from disk (see `validate_model`'s docstring for the two contracts)."""
    if isinstance(path_or_model, Model):
        return path_or_model, "<in-memory>"
    model = Model("validate")
    try:
        # pyArchimate's Model.read() calls sys.exit(1) on an unreadable file
        # instead of raising -- normalise that to a real exception so the
        # CLI's `except Exception` handler can report it cleanly instead of
        # the process crashing with an uncaught SystemExit.
        model.read(str(path_or_model))
    except SystemExit as exc:  # NOSONAR python:S5754 -- converting it IS the point, see above
        raise OSError(f"could not read {path_or_model!s} as an ArchiMate model") from exc
    return model, str(path_or_model)


def _relationship_matrix_findings(model: Model) -> list[dict[str, Any]]:
    """Check #1: relationship-matrix legality, endpoint by endpoint."""
    findings: list[dict[str, Any]] = []
    for rel in model.relationships:
        src = getattr(rel.source, "type", None)
        tgt = getattr(rel.target, "type", None)
        if src is None or tgt is None:
            findings.append(
                {
                    "check": "dangling_relationship",
                    "id": rel.uuid,
                    "detail": f"{rel.type} has a missing endpoint",
                }
            )
        elif not check_valid_relationship(rel.type, src, tgt):
            findings.append(
                {
                    "check": "illegal_relationship",
                    "id": rel.uuid,
                    "detail": f"{rel.type}: {src} -> {tgt} is not permitted by the ArchiMate 3.2 matrix",
                    # Structured fields alongside `detail` -- fixes.py (R14) reads
                    # these to compute the nearest legal relationship type without
                    # parsing the human-readable message back apart.
                    "rel_type": rel.type,
                    "source_type": src,
                    "target_type": tgt,
                }
            )
    return findings


def validate_model(path_or_model: str | Path | Model) -> dict[str, Any]:
    """Run pyArchimate's metamodel + referential-integrity checks.

    Ported from `.claude/skills/model-archimate/scripts/validate.py` -- accepts
    either a path to an Open Group Exchange Format XML file (the skill script's
    original contract, still used by the CLI `validate` subcommand) or an
    already-loaded `Model` (used by the in-memory validate-before-write path,
    R9), so the same checks run identically from a live Model as from disk."""
    model, path_label = _load_model_for_validation(path_or_model)
    findings = _relationship_matrix_findings(model)

    # 2. Model-wide re-validation (catches anything the per-rel loop missed).
    for rel_uuid in model.check_invalid_relationships() or []:
        if not any(f["id"] == rel_uuid for f in findings):
            findings.append(
                {"check": "invalid_relationship", "id": rel_uuid, "detail": "fails check_invalid_relationships()"}
            )

    # 3. Referential integrity.
    for cid in model.check_invalid_conn() or []:
        findings.append({"check": "broken_connection", "id": cid, "detail": "connection with a broken reference"})
    for nid in model.check_invalid_nodes() or []:
        findings.append({"check": "orphan_view_node", "id": nid, "detail": "view node references an unknown element"})

    return {
        "path": path_label,
        "elements": len(model.elements),
        "relationships": len(model.relationships),
        "views": len(model.views),
        "findings": findings,
        "clean": not findings,
    }


def write_and_validate() -> tuple[int, list[str], list[str], dict[str, Any] | None]:
    """Build the model from YAML, write `OUT`, then validate it.

    Returns `(exit_code, build_errors, motivation_warnings, validation_result)`.
    `exit_code` is 2 on a build error (nothing written), else the validator's
    own exit convention (0 clean, 1 invalid). Mirrors `build.py`'s previous
    `main()` exactly, just returning data instead of printing/exiting, so the
    CLI `build` subcommand owns all user-facing output."""
    model, errors, warnings = build_model()
    if model is None:
        return 2, errors, warnings, None

    model.write(str(OUT))
    result = validate_model(OUT)
    return (0 if result["clean"] else 1), errors, warnings, result
