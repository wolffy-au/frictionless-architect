#!/usr/bin/env python3
"""Regenerate diagrams from the model, skipping any view whose output is unchanged.

    poetry run python architecture/model/render_diagrams.py [--check] [--no-svg]

Single source of truth for "which view -> which file": the ``diagram:`` key in
``views.yaml`` (path under ``diagrams/``, no extension). The two C4 diagrams are
not views — they are projected by ``diagram-c4`` and listed in ``C4_DIAGRAMS``.
Vendored views (ADR-0029 — ``third_party/it4it/views.yaml``, loaded alongside
``views.yaml`` the same way ``build.py`` merges the vendored elements and
relationships) render into that model's own ``diagrams/`` dir instead of
``architecture/model/diagrams/``; every view defined in this repo's own
``views.yaml``, including the cross-model capability-bridges touchpoint view,
stays under ``architecture/model/diagrams/``.

Run ``build.py`` first (this reads the generated XML, it does not rebuild it).

Each view's ``.puml`` is generated to a string first and compared against the
committed file; a matching file is left untouched and its ``.svg`` is not
re-rendered (the PlantUML/graphviz invocation is the expensive step). Only
views whose rendered ``.puml`` actually changed — because the model or
``views.yaml`` changed — are written and re-rendered. Orphaned files (a view
removed from ``views.yaml``) are deleted.

* ``--check``  — do the same comparison but write nothing; exit 1 if anything
  is stale or orphaned. For CI / pre-commit.
* ``--no-svg`` — emit ``.puml`` only (skip the PlantUML render).

Exit 0 = up to date / written, 1 = stale (``--check``), 2 = error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REPO = HERE.parents[1]
VIEWS = HERE / "views.yaml"
DIAGRAMS = HERE / "diagrams"
# Vendored models (ADR-0029) each carry their own views.yaml, rendering into
# their own diagrams/ dir — (views file, diagrams dir) pairs, same order as
# build.py's VENDORED_MODELS.
VENDORED_VIEW_SOURCES = [(REPO / "third_party/it4it/views.yaml", REPO / "third_party/it4it/diagrams")]

# Repo-relative paths — _run() executes with cwd=REPO.
MODEL = "architecture/model/frictionless-architect.xml"
ARCHIMATE_PUML = ".claude/skills/diagram-archimate/scripts/model_to_puml.py"
C4_PUML = ".claude/skills/diagram-c4/scripts/model_to_c4.py"

SYSTEM = "Frictionless Architecture Platform"
C4_DIAGRAMS = [
    # (slug, level, layout)
    ("c4/context", "context", "WITH_LEGEND"),
    ("c4/container", "container", "LEFT_RIGHT"),
]


def _capture(cmd: list[str]) -> str:
    # Run from the repo root so generators that echo their input path into a
    # "GENERATED from ..." header emit a stable repo-relative path.
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(2)
    if r.stderr.strip():  # unmapped-type warnings etc.
        sys.stderr.write(r.stderr)
    return r.stdout.rstrip("\n") + "\n"


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
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
    views_file = (
        VIEWS if diagram_root == DIAGRAMS else next(vf for vf, root in VENDORED_VIEW_SOURCES if root == diagram_root)
    )
    if views_file.exists():
        for v in yaml.safe_load(views_file.read_text()) or []:
            slug = v.get("diagram")
            if not slug:
                sys.stderr.write(f"note: view {v.get('id')} has no `diagram:` key — skipped\n")
                continue
            cmd = [sys.executable, str(ARCHIMATE_PUML), str(MODEL), "--view", v["name"]]
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
                str(MODEL),
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
        found.append(str(f.relative_to(REPO)))
        if write:
            f.unlink()
    return found


def render(diagram_roots: list[Path], svg: bool, *, write: bool) -> tuple[list[str], list[str]]:
    """Generate each view's `.puml` and compare it against the committed file.

    Returns (stale, orphan) as repo-relative path strings. `stale` is every
    `.puml` whose freshly generated content differs from what's on disk (or
    is missing); when `write` is true those files are (re)written and their
    `.svg` re-rendered — content-identical views are left untouched. `orphan`
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
            stale.append(str(puml.relative_to(REPO)))
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if committed diagrams are stale")
    ap.add_argument("--no-svg", action="store_true", help="write .puml only")
    args = ap.parse_args()

    if not (REPO / MODEL).exists():
        sys.stderr.write(f"{MODEL} missing — run build.py first\n")
        return 2

    diagram_roots = [DIAGRAMS] + [d for _, d in VENDORED_VIEW_SOURCES]
    stale, orphan = render(diagram_roots, svg=not args.no_svg, write=not args.check)

    if args.check:
        for f in stale:
            print(f"STALE   {f}")
        for f in orphan:
            print(f"ORPHAN  {f}")
        if stale or orphan:
            print("\nrun: poetry run python architecture/model/render_diagrams.py")
            return 1
        print("diagrams up to date")
        return 0

    for f in stale:
        print(f"regenerated {f}")
    for f in orphan:
        print(f"removed {f}")
    if not (stale or orphan):
        print("diagrams already up to date, nothing regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
