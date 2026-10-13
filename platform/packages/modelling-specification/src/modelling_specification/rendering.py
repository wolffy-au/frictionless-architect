"""Regenerate diagrams from the model, and render a single view on demand.

Ported from `architecture/model/render_diagrams.py` (ADR-0037, R2) -- the batch
regeneration logic is unchanged; `render_single_view` is new (T006, FR-013): given a
`views.yaml` view id, render just that view to SVG in-process, without touching any
committed `.puml`/`.svg` file, for the chat router's on-demand/auto render endpoint.

Single source of truth for "which view -> which file": the ``diagram:`` key in
``views.yaml`` (path under ``diagrams/``, no extension). The two C4 diagrams are
not views -- they are projected by ``diagram-c4`` and listed in ``C4_DIAGRAMS``.
Vendored views (ADR-0029 -- ``third_party/it4it/views.yaml``, loaded alongside
``views.yaml`` the same way `model_io.py` merges the vendored elements and
relationships) render into that model's own ``diagrams/`` dir instead of
``architecture/model/diagrams/``; every view defined in this repo's own
``views.yaml``, including the cross-model capability-bridges touchpoint view,
stays under ``architecture/model/diagrams/``.

Batch regeneration reads the already-built XML (run `model_io.write_and_validate()`
first); `render_single_view` reads it too, and raises if it's missing.

Each view's ``.puml`` is generated to a string first and compared against the
committed file; a matching file is left untouched and its ``.svg`` is not
re-rendered (the PlantUML/graphviz invocation is the expensive step). Only
views whose rendered ``.puml`` actually changed -- because the model or
``views.yaml`` changed -- are written and re-rendered. Orphaned files (a view
removed from ``views.yaml``) are deleted.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml
from defusedxml import ElementTree as SafeET

from modelling_specification import model_io
from modelling_specification.model_io import OUT, REPO_ROOT

# Repo-relative string, not OUT's absolute Path: model_to_puml.py/model_to_c4.py echo
# their input path verbatim into each generated file's "GENERATED from ..." header, and
# subprocesses below run with cwd=REPO_ROOT, so this must match what render_diagrams.py
# always passed or every view would show as spuriously stale against the committed .puml.
MODEL_REL = str(OUT.relative_to(REPO_ROOT))

HERE = REPO_ROOT / "architecture" / "model"
VIEWS = HERE / "views.yaml"
# Generic one-per-standard-viewpoint views (include_types only), split out of views.yaml.
VIEWPOINT_VIEWS = HERE / "views-viewpoints.yaml"
# Generated gh-roadmap layer (ADR-0035): its per-milestone views render beside the hand-authored ones.
ROADMAP_VIEWS = HERE / "gh-roadmap" / "views.yaml"
DIAGRAMS = HERE / "diagrams"
# Vendored models (ADR-0029) each carry their own views.yaml, rendering into
# their own diagrams/ dir -- (views file, diagrams dir) pairs, same order as
# model_io.py's VENDORED_MODELS.
VENDORED_VIEW_SOURCES = [(REPO_ROOT / "third_party/it4it/views.yaml", REPO_ROOT / "third_party/it4it/diagrams")]

ARCHIMATE_PUML = REPO_ROOT / ".claude/skills/diagram-archimate/scripts/model_to_puml.py"
C4_PUML = REPO_ROOT / ".claude/skills/diagram-c4/scripts/model_to_c4.py"

SYSTEM = "Frictionless Architecture Platform"
C4_DIAGRAMS = [
    # (slug, level, layout)
    ("c4/context", "context", "WITH_LEGEND"),
    ("c4/container", "container", "LEFT_RIGHT"),
]


class ViewNotFoundError(Exception):
    """No `views.yaml` entry matches the requested view id (FR-013, FR-016)."""


def _capture(cmd: list[str]) -> str:
    # Run from the repo root so generators that echo their input path into a
    # "GENERATED from ..." header emit a stable repo-relative path.
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(2)
    if r.stderr.strip():  # unmapped-type warnings etc.
        sys.stderr.write(r.stderr)
    return r.stdout.rstrip("\n") + "\n"


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(2)
    if r.stderr.strip():
        sys.stderr.write(r.stderr)


def _jobs(diagram_root: Path) -> list[tuple[Path, list[str]]]:
    """(puml output path, generator command without `-o`) for every diagram,
    view-derived plus the fixed C4 pair. `diagram_root` is DIAGRAMS or a
    vendored model's diagrams dir."""
    jobs: list[tuple[Path, list[str]]] = []
    views_files = (
        [VIEWS, VIEWPOINT_VIEWS, ROADMAP_VIEWS]
        if diagram_root == DIAGRAMS
        else [next(vf for vf, root in VENDORED_VIEW_SOURCES if root == diagram_root)]
    )
    for views_file in views_files:
        if not views_file.exists():
            continue
        for v in yaml.safe_load(views_file.read_text()) or []:
            slug = v.get("diagram")
            if not slug:
                sys.stderr.write(f"note: view {v.get('id')} has no `diagram:` key — skipped\n")
                continue
            cmd = [sys.executable, str(ARCHIMATE_PUML), MODEL_REL, "--view", v["name"]]
            for rel_type in v.get("no_direction", []):
                cmd += ["--no-direction", rel_type]
            if v.get("max_width"):
                cmd += ["--max-width", str(v["max_width"])]
            jobs.append((diagram_root / f"{slug}.puml", cmd))

    if diagram_root == DIAGRAMS:
        for slug, level, layout in C4_DIAGRAMS:
            cmd = [
                sys.executable,
                str(C4_PUML),
                MODEL_REL,
                "--system",
                SYSTEM,
                "--level",
                level,
                "--layout",
                layout,
            ]
            jobs.append((diagram_root / f"{slug}.puml", cmd))
    return jobs


def _orphans(root: Path, wanted: set[Path], *, write: bool) -> list[str]:
    """Existing `.puml`/`.svg` under `root` with no matching view; deletes them when `write`."""
    if not root.exists():
        return []
    found: list[str] = []
    for f in root.rglob("*"):
        if not f.is_file() or f.suffix not in (".puml", ".svg"):
            continue
        if f.with_suffix(".puml") in wanted:
            continue
        found.append(str(f.relative_to(REPO_ROOT)))
        if write:
            f.unlink()
    return found


def render(diagram_roots: list[Path], svg: bool, *, write: bool) -> tuple[list[str], list[str]]:
    """Generate each view's `.puml` and compare it against the committed file.

    Returns (stale, orphan) as repo-relative path strings. `stale` is every
    `.puml` whose freshly generated content differs from what's on disk (or
    is missing); when `write` is true those files are (re)written and their
    `.svg` re-rendered -- content-identical views are left untouched. `orphan`
    is every existing `.puml`/`.svg` with no matching view; when `write` is
    true they're deleted.
    """
    stale: list[str] = []
    orphan: list[str] = []
    changed_pumls: list[Path] = []
    wanted: set[Path] = set()

    for root in diagram_roots:
        for puml, cmd in _jobs(root):
            wanted.add(puml)
            new_text = _capture(cmd)
            current = puml.read_text() if puml.exists() else None
            if current == new_text:
                continue
            stale.append(str(puml.relative_to(REPO_ROOT)))
            changed_pumls.append(puml)
            if write:
                puml.parent.mkdir(parents=True, exist_ok=True)
                puml.write_text(new_text)

        orphan += _orphans(root, wanted, write=write)

    if write and svg and changed_pumls:
        _run(["plantuml", "-tsvg", *(str(p) for p in changed_pumls)])
        # PlantUML's SVG output has no trailing newline; normalise to one so
        # re-renders don't churn on it.
        for p in changed_pumls:
            svg_path = p.with_suffix(".svg")
            if svg_path.exists():
                svg_path.write_text(svg_path.read_text().rstrip("\n") + "\n")

    return stale, orphan


def render_diagrams(*, check: bool, svg: bool) -> tuple[int, list[str], list[str]]:
    """Batch-regenerate (or `--check`) every diagram. Returns (exit_code, stale, orphan).

    0 = up to date / written, 1 = stale (`check`), 2 = `architecture/model/
    frictionless-architect.xml` is missing (run `model_io.write_and_validate()` first)."""
    if not OUT.exists():
        return 2, [], []

    diagram_roots = [DIAGRAMS] + [d for _, d in VENDORED_VIEW_SOURCES]
    stale, orphan = render(diagram_roots, svg=svg, write=not check)
    exit_code = 1 if check and (stale or orphan) else 0
    return exit_code, stale, orphan


def _find_view(view_id: str) -> dict[str, Any]:
    """Look up a `views.yaml` entry by `id` across every views file (first-party,
    gh-roadmap, vendored). Raises `ViewNotFoundError` if none match."""
    for views_file in (VIEWS, VIEWPOINT_VIEWS, ROADMAP_VIEWS, *(vf for vf, _ in VENDORED_VIEW_SOURCES)):
        if not views_file.exists():
            continue
        for v in yaml.safe_load(views_file.read_text()) or []:
            view: dict[str, Any] = v
            if view.get("id") == view_id:
                return view
    raise ViewNotFoundError(f"no view with id {view_id!r} in views.yaml")


def _all_views() -> list[dict[str, Any]]:
    """Every view across the first-party, gh-roadmap and vendored sources, same
    precedence order `_find_view` uses."""
    views: list[dict[str, Any]] = []
    for views_file in (VIEWS, VIEWPOINT_VIEWS, ROADMAP_VIEWS, *(vf for vf, _ in VENDORED_VIEW_SOURCES)):
        if views_file.exists():
            views += yaml.safe_load(views_file.read_text()) or []
    return views


def list_views() -> list[dict[str, str]]:
    """`{id, name}` for every renderable view, in file order (the UI's view picker)."""
    return [{"id": v["id"], "name": str(v.get("name", v["id"]))} for v in _all_views() if "id" in v]


def _refresh_model_if_sources_changed() -> None:
    """Rebuild the generated model when any YAML source is newer than its XML."""
    if not OUT.exists():
        return

    model_mtime = OUT.stat().st_mtime_ns
    inputs = [
        directory / filename
        for directory in (model_io.HERE, *model_io.MODEL_LAYERS)
        for filename in ("elements.yaml", "relationships.yaml", "views.yaml")
    ]
    if not any(path.is_file() and path.stat().st_mtime_ns > model_mtime for path in inputs):
        return

    code, errors, warnings, result = model_io.write_and_validate()
    for warning in warnings:
        sys.stderr.write(f"warning: {warning}\n")
    if code == 0 and not errors and result is not None:
        return

    details = list(errors)
    if result is not None:
        details.extend(f"{finding['check']}: {finding['detail']}" for finding in result["findings"])
    if not details:
        details.append(f"model build exited with code {code}")
    raise RuntimeError(f"could not rebuild the model from changed YAML sources: {'; '.join(details)}")


def _resolution(ids: list[str]) -> dict[str, Any]:
    if len(ids) == 1:
        return {"resolved_view_id": ids[0], "ambiguous_candidates": []}
    if len(ids) > 1:
        return {"resolved_view_id": None, "ambiguous_candidates": ids}
    return {"resolved_view_id": None, "ambiguous_candidates": []}


def resolve_view_request(object_id: str | None, description: str | None) -> dict[str, Any]:
    """Resolve a View Request (FR-016, data-model.md) to zero, one, or several
    plausible `views.yaml` ids -- never guessing among several and never silently
    picking none. `object_id` is tried first as an exact view id, then as an element
    id -- every view it's actually in scope for, via `model_io.view_element_ids`'s
    `members`/`include_types`/`exclude_elements` rule (the same rule `add_views` uses
    to build the view for real, not a `members`-only subset of it); `description`
    matches case-insensitively against each view's `name` as a substring."""
    views = _all_views()
    if object_id:
        exact = [v["id"] for v in views if v.get("id") == object_id]
        if exact:
            return _resolution(exact)
        elements, types_by_id = model_io.existing_elements_and_types()
        containing = [
            v["id"] for v in views if "id" in v and object_id in model_io.view_element_ids(v, elements, types_by_id)
        ]
        return _resolution(containing)
    if description:
        needle = description.strip().lower()
        matching = [v["id"] for v in views if "id" in v and needle in str(v.get("name", "")).lower()]
        return _resolution(matching)
    return {"resolved_view_id": None, "ambiguous_candidates": []}


_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_ACTIVE_ELEMENTS = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video"}


def sanitize_svg(svg: str) -> str:
    """Strip anything active from a rendered SVG before it is served or inlined into
    the page: script-like elements, `on*` event attributes and `javascript:` links.
    Element names in a preview come from the LLM, so the SVG is not trusted markup."""
    ET.register_namespace("", _SVG_NS)
    ET.register_namespace("xlink", _XLINK_NS)
    root = SafeET.fromstring(svg)

    def local(name: str) -> str:
        return name.rsplit("}", 1)[-1].lower()

    for parent in root.iter():
        for child in list(parent):
            if local(child.tag) in _ACTIVE_ELEMENTS:
                parent.remove(child)
    for element in root.iter():
        for attr in list(element.attrib):
            value = element.attrib[attr].strip().lower()
            if local(attr).startswith("on") or (local(attr) == "href" and value.startswith(("javascript:", "data:"))):
                del element.attrib[attr]
    return ET.tostring(root, encoding="unicode")


def _render_svg(v: dict[str, Any], model_path: str) -> str:
    cmd = [sys.executable, str(ARCHIMATE_PUML), model_path, "--view", v["name"]]
    for rel_type in v.get("no_direction", []):
        cmd += ["--no-direction", rel_type]
    if v.get("max_width"):
        cmd += ["--max-width", str(v["max_width"])]
    puml_text = _capture(cmd)
    result = subprocess.run(["plantuml", "-tsvg", "-pipe"], input=puml_text, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"plantuml failed rendering view {v['id']!r}: {result.stderr}")
    return sanitize_svg(result.stdout)


def render_single_view(view_id: str) -> str:
    """Render one view's current SVG in-process, without touching any committed
    `.puml`/`.svg` file (FR-013) -- used by `GET /authoring/render`'s unambiguous-resolve
    path. Reads the already-built `frictionless-architect.xml`; raises `ViewNotFoundError`
    if `view_id` matches nothing in `views.yaml` (the fuzzy/ambiguous-candidates resolution
    FR-016 adds sits in front of this, in the router)."""
    if not OUT.exists():
        raise ViewNotFoundError("architecture/model/frictionless-architect.xml is missing — build the model first")
    _refresh_model_if_sources_changed()
    return _render_svg(_find_view(view_id), MODEL_REL)


class PreviewError(Exception):
    """The candidate delta cannot be assembled into a model to preview."""


def render_candidate_view(view_id: str, elements: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> str:
    """Render `view_id` as it would look with the delta applied -- built in memory and
    written only to a throwaway temp file, never to `architecture/model/`."""
    v = _find_view(view_id)
    model, errors = model_io.preview_model(elements, relationships, v)
    if model is None:
        raise PreviewError("; ".join(errors))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "preview.xml"
        model.write(str(path))
        return _render_svg(v, str(path))
