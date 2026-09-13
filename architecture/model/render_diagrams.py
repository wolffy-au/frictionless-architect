#!/usr/bin/env python3
"""Regenerate every diagram from the model.

    poetry run python architecture/model/render_diagrams.py [--check] [--no-svg]

Single source of truth for "which view -> which file": the ``diagram:`` key in
``views.yaml`` (path under ``diagrams/``, no extension). The two C4 diagrams are
not views — they are projected by ``diagram-c4`` and listed in ``C4_DIAGRAMS``.
Pure-IT4IT views (ADR-0029 — a ``diagram:`` slug of ``it4it/...`` or
``frictionless-architect-it4it-alignment``) render into the vendored
``third_party/it4it/diagrams/`` instead of ``architecture/model/diagrams/``;
every other view, including the cross-model capability-bridges touchpoint
view, stays under ``architecture/model/diagrams/``.

Run ``build.py`` first (this reads the generated XML, it does not rebuild it).

* ``--check``  — regenerate into a temp dir and diff; exit 1 if anything is
  stale. For CI / pre-commit.
* ``--no-svg`` — emit ``.puml`` only (skip the PlantUML render).

Exit 0 = up to date / written, 1 = stale (``--check``), 2 = error.
"""

from __future__ import annotations

import argparse
import filecmp
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REPO = HERE.parents[1]
VIEWS = HERE / "views.yaml"
DIAGRAMS = HERE / "diagrams"
# Views that are pure IT4IT reference content (ADR-0029) render into the
# vendored third_party/it4it repo instead — everything else (including the
# cross-model "capability bridges" touchpoint view) stays under DIAGRAMS.
IT4IT_DIAGRAMS = REPO / "third_party/it4it/diagrams"


def is_it4it_slug(slug: str) -> bool:
    return slug.startswith("it4it/") or slug == "frictionless-architect-it4it-alignment"


def out_root(slug: str) -> Path:
    return IT4IT_DIAGRAMS if is_it4it_slug(slug) else DIAGRAMS


def rel_path(slug: str) -> str:
    """Path (no extension) under `out_root(slug)`. The `it4it/` slug prefix
    only disambiguates within views.yaml — third_party/it4it is already
    IT4IT-scoped, so drop it rather than nest an `it4it/` dir inside it."""
    return slug.removeprefix("it4it/") if is_it4it_slug(slug) else slug


# Repo-relative paths — _run() executes with cwd=REPO.
MODEL = "architecture/model/frictionless-architect.xml"
ARCHIMATE_PUML = ".agents/skills/diagram-archimate/scripts/model_to_puml.py"
C4_PUML = ".agents/skills/diagram-c4/scripts/model_to_c4.py"

SYSTEM = "Frictionless Architecture Platform"
C4_DIAGRAMS = [
    # (slug, level, layout)
    ("frictionless-architect-c4-context", "context", "WITH_LEGEND"),
    ("frictionless-architect-c4-container", "container", "LEFT_RIGHT"),
]


def _run(cmd: list[str]) -> None:
    # Run from the repo root so generators that echo their input path into a
    # "GENERATED from ..." header emit a stable repo-relative path.
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(2)
    if r.stderr.strip():  # unmapped-type warnings etc.
        sys.stderr.write(r.stderr)


def render(roots: dict[Path, Path], svg: bool) -> None:
    """`roots` maps each logical output root (DIAGRAMS / IT4IT_DIAGRAMS) to the
    actual directory to write into — themselves for a real run, or matching
    temp dirs for `--check`."""
    views = yaml.safe_load(VIEWS.read_text()) or []
    jobs: list[tuple[str, list[str]]] = []

    for v in views:
        slug = v.get("diagram")
        if not slug:
            sys.stderr.write(f"note: view {v.get('id')} has no `diagram:` key — skipped\n")
            continue
        puml = roots[out_root(slug)] / f"{rel_path(slug)}.puml"
        cmd = [sys.executable, str(ARCHIMATE_PUML), str(MODEL), "--view", v["name"], "-o", str(puml)]
        for rel_type in v.get("no_direction", []):
            cmd += ["--no-direction", rel_type]
        jobs.append((slug, cmd))

    for slug, level, layout in C4_DIAGRAMS:
        puml = roots[DIAGRAMS] / f"{slug}.puml"
        jobs.append(
            (
                slug,
                [
                    sys.executable,
                    str(C4_PUML),
                    str(MODEL),
                    "--system",
                    SYSTEM,
                    "--level",
                    level,
                    "--layout",
                    layout,
                    "-o",
                    str(puml),
                ],
            )
        )

    for _, cmd in jobs:
        Path(cmd[cmd.index("-o") + 1]).parent.mkdir(parents=True, exist_ok=True)
        _run(cmd)

    if svg:
        pumls = sorted(str(p) for out_dir in roots.values() for p in out_dir.rglob("*.puml"))
        _run(["plantuml", "-tsvg", *pumls])

    # PlantUML's SVG output has no trailing newline; the .puml generators do.
    # Normalise every file to exactly one so re-renders don't churn on it.
    for out_dir in roots.values():
        for f in out_dir.rglob("*"):
            if f.suffix in (".puml", ".svg"):
                text = f.read_text().rstrip("\n") + "\n"
                f.write_text(text)


def _all_files(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if committed diagrams are stale")
    ap.add_argument("--no-svg", action="store_true", help="write .puml only")
    args = ap.parse_args()

    if not (REPO / MODEL).exists():
        sys.stderr.write(f"{MODEL} missing — run build.py first\n")
        return 2

    if not args.check:
        render({DIAGRAMS: DIAGRAMS, IT4IT_DIAGRAMS: IT4IT_DIAGRAMS}, svg=not args.no_svg)
        print(f"rendered diagrams into {DIAGRAMS.relative_to(REPO)} and {IT4IT_DIAGRAMS.relative_to(REPO)}")
        return 0

    with tempfile.TemporaryDirectory() as td:
        tmp_main, tmp_it4it = Path(td) / "main", Path(td) / "it4it"
        render({DIAGRAMS: tmp_main, IT4IT_DIAGRAMS: tmp_it4it}, svg=not args.no_svg)
        stale: list[str] = []
        orphan: list[str] = []
        for real, tmp in ((DIAGRAMS, tmp_main), (IT4IT_DIAGRAMS, tmp_it4it)):
            want, have = _all_files(tmp), _all_files(real)
            stale += sorted(want - have) + sorted(
                f for f in want & have if not filecmp.cmp(tmp / f, real / f, shallow=False)
            )
            orphan += sorted(have - want)
        if stale or orphan:
            for f in stale:
                print(f"STALE   {f}")
            for f in orphan:
                print(f"ORPHAN  {f}")
            print("\nrun: poetry run python architecture/model/render_diagrams.py")
            return 1
    print("diagrams up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
